import { useEffect, useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';

import {
  Button,
  Checkbox,
  ConfirmDialog,
  FormField,
  Modal,
  SelectField,
  TextareaField,
} from '@/components/ui';

import {
  useCreateEducation,
  useDeleteEducation,
  useEducation,
  useReorderEducation,
  useUpdateEducation,
} from '../../api/cvQueries';
import { DEGREE_TYPES } from '../../constants';
import { useReorder } from '../../hooks/useReorder';
import { educationSchema } from '../../schemas/cvSchemas';
import { toNullableDecimal, toNullableInt } from '../../utils/payload';
import { EntryCard } from '../EntryCard';
import { EmptyState, SectionShell } from '../SectionShell';

const EMPTY = {
  institution: '',
  degree_type: '',
  field_of_study: '',
  cgpa: '',
  cgpa_scale: '',
  start_year: '',
  end_year: '',
  is_current: false,
  thesis_title: '',
  achievements: '',
};

function toFormValues(entry) {
  if (!entry) return EMPTY;

  return {
    institution: entry.institution ?? '',
    degree_type: entry.degree_type ?? '',
    field_of_study: entry.field_of_study ?? '',
    cgpa: entry.cgpa != null ? String(entry.cgpa) : '',
    cgpa_scale: entry.cgpa_scale != null ? String(entry.cgpa_scale) : '',
    start_year: entry.start_year != null ? String(entry.start_year) : '',
    end_year: entry.end_year != null ? String(entry.end_year) : '',
    is_current: Boolean(entry.is_current),
    thesis_title: entry.thesis_title ?? '',
    achievements: entry.achievements ?? '',
  };
}

function EducationFormModal({ open, onClose, entry, onSubmit, loading }) {
  const {
    register,
    handleSubmit,
    reset,
    watch,
    formState: { errors },
  } = useForm({
    resolver: zodResolver(educationSchema),
    defaultValues: toFormValues(entry),
  });

  useEffect(() => {
    if (open) {
      reset(toFormValues(entry));
    }
  }, [open, entry, reset]);

  const isCurrent = watch('is_current');

  const submit = handleSubmit((values) => {
    onSubmit({
      institution: values.institution.trim(),
      degree_type: values.degree_type || '',
      field_of_study: values.field_of_study || '',
      cgpa: toNullableDecimal(values.cgpa),
      cgpa_scale: toNullableDecimal(values.cgpa_scale),
      start_year: toNullableInt(values.start_year),
      end_year: values.is_current ? null : toNullableInt(values.end_year),
      is_current: values.is_current,
      thesis_title: values.thesis_title || '',
      achievements: values.achievements || '',
    });
  });

  return (
    <Modal
      open={open}
      onClose={onClose}
      title={entry ? 'Edit education' : 'Add education'}
      size="lg"
      footer={
        <>
          <Button variant="ghost" size="sm" onClick={onClose} disabled={loading}>
            Cancel
          </Button>
          <Button size="sm" onClick={submit} loading={loading}>
            {entry ? 'Save changes' : 'Add education'}
          </Button>
        </>
      }
    >
      <form onSubmit={submit} noValidate className="space-y-4">
        <FormField
          id="institution"
          label="Institution"
          placeholder="University of Engineering and Technology"
          error={errors.institution}
          registration={register('institution')}
        />

        <div className="grid gap-4 sm:grid-cols-2">
          <SelectField
            id="degree_type"
            label="Degree"
            placeholder="Select degree"
            options={DEGREE_TYPES}
            error={errors.degree_type}
            registration={register('degree_type')}
          />
          <FormField
            id="field_of_study"
            label="Field of study"
            placeholder="Software Engineering"
            error={errors.field_of_study}
            registration={register('field_of_study')}
          />
          <FormField
            id="cgpa"
            label="CGPA"
            type="number"
            step="0.01"
            placeholder="3.30"
            error={errors.cgpa}
            registration={register('cgpa')}
          />
          <FormField
            id="cgpa_scale"
            label="Out of"
            type="number"
            step="0.1"
            placeholder="4.0"
            hint="Defaults to 4.0 if left blank."
            error={errors.cgpa_scale}
            registration={register('cgpa_scale')}
          />
          <FormField
            id="edu_start_year"
            label="Start year"
            type="number"
            placeholder="2019"
            error={errors.start_year}
            registration={register('start_year')}
          />
          {!isCurrent ? (
            <FormField
              id="edu_end_year"
              label="End year"
              type="number"
              placeholder="2023"
              error={errors.end_year}
              registration={register('end_year')}
            />
          ) : null}
        </div>

        <Checkbox id="edu_is_current" label="I am still studying here" {...register('is_current')} />

        <FormField
          id="thesis_title"
          label="Thesis title"
          placeholder="Optional"
          error={errors.thesis_title}
          registration={register('thesis_title')}
        />

        <TextareaField
          id="achievements"
          label="Achievements"
          rows={3}
          placeholder="Dean's list, scholarships, awards"
          error={errors.achievements}
          registration={register('achievements')}
        />
      </form>
    </Modal>
  );
}

export function EducationStep() {
  const [formOpen, setFormOpen] = useState(false);
  const [editing, setEditing] = useState(null);
  const [pendingDelete, setPendingDelete] = useState(null);

  const { data: entries = [], isLoading } = useEducation();
  const createMutation = useCreateEducation();
  const updateMutation = useUpdateEducation();
  const deleteMutation = useDeleteEducation();
  const reorderMutation = useReorderEducation();

  const { moveUp, moveDown, isReordering } = useReorder(entries, reorderMutation);

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
      title="Education"
      description="Degrees, institutions and academic achievements."
      isLoading={isLoading}
      action={
        <Button
          size="sm"
          onClick={() => {
            setEditing(null);
            setFormOpen(true);
          }}
        >
          + Add education
        </Button>
      }
    >
      {entries.length === 0 ? (
        <EmptyState
          message="No education added yet"
          hint="One entry earns the full 15 points for this section."
        />
      ) : (
        <div className="space-y-3">
          {entries.map((entry, index) => {
            const degree = DEGREE_TYPES.find((d) => d.value === entry.degree_type)?.label;
            const years = entry.is_current
              ? `${entry.start_year} — Present`
              : [entry.start_year, entry.end_year].filter(Boolean).join(' — ');
            const cgpa = entry.cgpa ? `CGPA ${entry.cgpa}/${entry.cgpa_scale || '4.0'}` : '';

            return (
              <EntryCard
                key={entry.id}
                title={[degree, entry.field_of_study].filter(Boolean).join(' in ') || 'Education'}
                subtitle={entry.institution}
                meta={[years, cgpa].filter(Boolean).join('  •  ')}
                onEdit={() => {
                  setEditing(entry);
                  setFormOpen(true);
                }}
                onDelete={() => setPendingDelete(entry)}
                onMoveUp={() => moveUp(index)}
                onMoveDown={() => moveDown(index)}
                canMoveUp={index > 0}
                canMoveDown={index < entries.length - 1}
                reordering={isReordering}
              />
            );
          })}
        </div>
      )}

      <EducationFormModal
        open={formOpen}
        entry={editing}
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
        title="Delete this education entry?"
        description={pendingDelete ? `"${pendingDelete.institution}" will be removed.` : undefined}
      />
    </SectionShell>
  );
}
