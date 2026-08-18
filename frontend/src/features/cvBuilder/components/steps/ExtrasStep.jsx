import { useEffect, useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';

import { Button, ConfirmDialog, FormField, Modal, SelectField } from '@/components/ui';

import {
  useCertifications,
  useCreateCertification,
  useCreateLanguage,
  useDeleteCertification,
  useDeleteLanguage,
  useLanguages,
  useReorderCertifications,
  useReorderLanguages,
  useUpdateCertification,
  useUpdateLanguage,
} from '../../api/cvQueries';
import { LANGUAGE_PROFICIENCY, monthLabel, MONTHS } from '../../constants';
import { useReorder } from '../../hooks/useReorder';
import { certificationSchema, languageSchema } from '../../schemas/cvSchemas';
import { toAbsoluteUrl, toNullableInt } from '../../utils/payload';
import { EntryCard } from '../EntryCard';
import { EmptyState, SectionShell } from '../SectionShell';

// --- Certifications ----------------------------------------------------------

const EMPTY_CERT = {
  name: '',
  issuing_organization: '',
  issue_month: '',
  issue_year: '',
  expiry_year: '',
  credential_url: '',
};

function toCertValues(cert) {
  if (!cert) return EMPTY_CERT;

  return {
    name: cert.name ?? '',
    issuing_organization: cert.issuing_organization ?? '',
    issue_month: cert.issue_month != null ? String(cert.issue_month) : '',
    issue_year: cert.issue_year != null ? String(cert.issue_year) : '',
    expiry_year: cert.expiry_year != null ? String(cert.expiry_year) : '',
    credential_url: cert.credential_url ?? '',
  };
}

function CertificationFormModal({ open, onClose, cert, onSubmit, loading }) {
  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm({
    resolver: zodResolver(certificationSchema),
    defaultValues: toCertValues(cert),
  });

  useEffect(() => {
    if (open) {
      reset(toCertValues(cert));
    }
  }, [open, cert, reset]);

  const submit = handleSubmit((values) => {
    onSubmit({
      name: values.name.trim(),
      issuing_organization: values.issuing_organization || '',
      issue_month: toNullableInt(values.issue_month),
      issue_year: toNullableInt(values.issue_year),
      expiry_year: toNullableInt(values.expiry_year),
      credential_url: toAbsoluteUrl(values.credential_url),
    });
  });

  return (
    <Modal
      open={open}
      onClose={onClose}
      title={cert ? 'Edit certification' : 'Add certification'}
      footer={
        <>
          <Button variant="ghost" size="sm" onClick={onClose} disabled={loading}>
            Cancel
          </Button>
          <Button size="sm" onClick={submit} loading={loading}>
            {cert ? 'Save changes' : 'Add certification'}
          </Button>
        </>
      }
    >
      <form onSubmit={submit} noValidate className="space-y-4">
        <FormField
          id="cert_name"
          label="Certification"
          placeholder="AWS Solutions Architect — Associate"
          error={errors.name}
          registration={register('name')}
        />
        <FormField
          id="issuing_organization"
          label="Issuing organisation"
          placeholder="Amazon Web Services"
          error={errors.issuing_organization}
          registration={register('issuing_organization')}
        />
        <div className="grid gap-4 sm:grid-cols-3">
          <SelectField
            id="issue_month"
            label="Issued month"
            placeholder="Month"
            options={MONTHS}
            error={errors.issue_month}
            registration={register('issue_month')}
          />
          <FormField
            id="issue_year"
            label="Issued year"
            type="number"
            placeholder="2025"
            error={errors.issue_year}
            registration={register('issue_year')}
          />
          <FormField
            id="expiry_year"
            label="Expires"
            type="number"
            placeholder="Never"
            hint="Leave blank if it does not expire."
            error={errors.expiry_year}
            registration={register('expiry_year')}
          />
        </div>
        <FormField
          id="credential_url"
          label="Credential URL"
          placeholder="credly.com/badges/…"
          error={errors.credential_url}
          registration={register('credential_url')}
        />
      </form>
    </Modal>
  );
}

function CertificationsSection() {
  const [formOpen, setFormOpen] = useState(false);
  const [editing, setEditing] = useState(null);
  const [pendingDelete, setPendingDelete] = useState(null);

  const { data: items = [], isLoading } = useCertifications();
  const createMutation = useCreateCertification();
  const updateMutation = useUpdateCertification();
  const deleteMutation = useDeleteCertification();
  const reorderMutation = useReorderCertifications();

  const { moveUp, moveDown, isReordering } = useReorder(items, reorderMutation);

  const handleSubmit = async (payload) => {
    try {
      if (editing) {
        await updateMutation.mutateAsync({ id: editing.id, payload });
      } else {
        await createMutation.mutateAsync(payload);
      }
      setFormOpen(false);
      setEditing(null);
    } catch {
      // toast handled by the mutation
    }
  };

  const handleDelete = async () => {
    try {
      await deleteMutation.mutateAsync(pendingDelete.id);
    } catch {
      // toast handled by the mutation
    } finally {
      setPendingDelete(null);
    }
  };

  return (
    <SectionShell
      title="Certifications"
      description="Does not affect your completion score, but strengthens the CV."
      isLoading={isLoading}
      action={
        <Button
          size="sm"
          onClick={() => {
            setEditing(null);
            setFormOpen(true);
          }}
        >
          + Add certification
        </Button>
      }
    >
      {items.length === 0 ? (
        <EmptyState message="No certifications yet" />
      ) : (
        <div className="space-y-3">
          {items.map((cert, index) => (
            <EntryCard
              key={cert.id}
              title={cert.name}
              subtitle={cert.issuing_organization}
              meta={[
                [monthLabel(cert.issue_month), cert.issue_year].filter(Boolean).join(' '),
                cert.expiry_year ? `Expires ${cert.expiry_year}` : 'No expiry',
              ]
                .filter(Boolean)
                .join('  •  ')}
              onEdit={() => {
                setEditing(cert);
                setFormOpen(true);
              }}
              onDelete={() => setPendingDelete(cert)}
              onMoveUp={() => moveUp(index)}
              onMoveDown={() => moveDown(index)}
              canMoveUp={index > 0}
              canMoveDown={index < items.length - 1}
              reordering={isReordering}
            />
          ))}
        </div>
      )}

      <CertificationFormModal
        open={formOpen}
        cert={editing}
        onClose={() => {
          setFormOpen(false);
          setEditing(null);
        }}
        onSubmit={handleSubmit}
        loading={createMutation.isPending || updateMutation.isPending}
      />

      <ConfirmDialog
        open={Boolean(pendingDelete)}
        onClose={() => setPendingDelete(null)}
        onConfirm={handleDelete}
        loading={deleteMutation.isPending}
        title="Delete this certification?"
        description={pendingDelete ? `"${pendingDelete.name}" will be removed.` : undefined}
      />
    </SectionShell>
  );
}

// --- Languages ---------------------------------------------------------------

function LanguageFormModal({ open, onClose, language, onSubmit, loading }) {
  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm({
    resolver: zodResolver(languageSchema),
    defaultValues: {
      language_name: language?.language_name ?? '',
      proficiency: language?.proficiency ?? '',
    },
  });

  useEffect(() => {
    if (open) {
      reset({
        language_name: language?.language_name ?? '',
        proficiency: language?.proficiency ?? '',
      });
    }
  }, [open, language, reset]);

  const submit = handleSubmit((values) => {
    onSubmit({
      language_name: values.language_name.trim(),
      proficiency: values.proficiency || '',
    });
  });

  return (
    <Modal
      open={open}
      onClose={onClose}
      title={language ? 'Edit language' : 'Add language'}
      size="sm"
      footer={
        <>
          <Button variant="ghost" size="sm" onClick={onClose} disabled={loading}>
            Cancel
          </Button>
          <Button size="sm" onClick={submit} loading={loading}>
            {language ? 'Save changes' : 'Add language'}
          </Button>
        </>
      }
    >
      <form onSubmit={submit} noValidate className="space-y-4">
        <FormField
          id="language_name"
          label="Language"
          placeholder="English"
          error={errors.language_name}
          registration={register('language_name')}
        />
        <SelectField
          id="language_proficiency"
          label="Proficiency"
          placeholder="Select level"
          options={LANGUAGE_PROFICIENCY}
          error={errors.proficiency}
          registration={register('proficiency')}
        />
      </form>
    </Modal>
  );
}

function LanguagesSection() {
  const [formOpen, setFormOpen] = useState(false);
  const [editing, setEditing] = useState(null);
  const [pendingDelete, setPendingDelete] = useState(null);

  const { data: items = [], isLoading } = useLanguages();
  const createMutation = useCreateLanguage();
  const updateMutation = useUpdateLanguage();
  const deleteMutation = useDeleteLanguage();
  const reorderMutation = useReorderLanguages();

  const { moveUp, moveDown, isReordering } = useReorder(items, reorderMutation);

  const handleSubmit = async (payload) => {
    try {
      if (editing) {
        await updateMutation.mutateAsync({ id: editing.id, payload });
      } else {
        await createMutation.mutateAsync(payload);
      }
      setFormOpen(false);
      setEditing(null);
    } catch {
      // toast handled by the mutation
    }
  };

  const handleDelete = async () => {
    try {
      await deleteMutation.mutateAsync(pendingDelete.id);
    } catch {
      // toast handled by the mutation
    } finally {
      setPendingDelete(null);
    }
  };

  return (
    <SectionShell
      title="Languages"
      isLoading={isLoading}
      action={
        <Button
          size="sm"
          onClick={() => {
            setEditing(null);
            setFormOpen(true);
          }}
        >
          + Add language
        </Button>
      }
    >
      {items.length === 0 ? (
        <EmptyState message="No languages yet" />
      ) : (
        <div className="space-y-3">
          {items.map((language, index) => (
            <EntryCard
              key={language.id}
              title={language.language_name}
              subtitle={
                LANGUAGE_PROFICIENCY.find((p) => p.value === language.proficiency)?.label ?? ''
              }
              onEdit={() => {
                setEditing(language);
                setFormOpen(true);
              }}
              onDelete={() => setPendingDelete(language)}
              onMoveUp={() => moveUp(index)}
              onMoveDown={() => moveDown(index)}
              canMoveUp={index > 0}
              canMoveDown={index < items.length - 1}
              reordering={isReordering}
            />
          ))}
        </div>
      )}

      <LanguageFormModal
        open={formOpen}
        language={editing}
        onClose={() => {
          setFormOpen(false);
          setEditing(null);
        }}
        onSubmit={handleSubmit}
        loading={createMutation.isPending || updateMutation.isPending}
      />

      <ConfirmDialog
        open={Boolean(pendingDelete)}
        onClose={() => setPendingDelete(null)}
        onConfirm={handleDelete}
        loading={deleteMutation.isPending}
        title="Delete this language?"
        description={pendingDelete ? `"${pendingDelete.language_name}" will be removed.` : undefined}
      />
    </SectionShell>
  );
}

export function ExtrasStep() {
  return (
    <div className="space-y-6">
      <CertificationsSection />
      <LanguagesSection />
    </div>
  );
}
