import { useEffect, useMemo, useRef, useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { toast } from 'sonner';

import { Alert, Button, FormField, TextareaField } from '@/components/ui';

import { usePatchProfile, useUpdateProfile } from '../../api/cvQueries';
import { SUMMARY_MIN_LENGTH } from '../../constants';
import { clearBackup, readBackup, useAutosave } from '../../hooks/useAutosave';
import { profileSchema } from '../../schemas/cvSchemas';
import { toAbsoluteUrl } from '../../utils/payload';
import { SectionShell } from '../SectionShell';
import { SaveStatus } from '../SaveStatus';

const FIELDS = [
  'full_name',
  'professional_title',
  'email',
  'phone',
  'city',
  'country',
  'linkedin_url',
  'github_url',
  'portfolio_url',
  'summary',
];

const URL_FIELDS = ['linkedin_url', 'github_url', 'portfolio_url'];

function toFormValues(profile) {
  return FIELDS.reduce((values, field) => {
    values[field] = profile?.[field] ?? '';
    return values;
  }, {});
}

/* Django's URLField rejects scheme-less input before the backend can normalize
   it, so the scheme is added here. */
function toPayload(values) {
  const payload = { ...values };
  URL_FIELDS.forEach((field) => {
    payload[field] = toAbsoluteUrl(payload[field]);
  });
  return payload;
}

export function ContactStep({ profile }) {
  const patchMutation = usePatchProfile();
  const updateMutation = useUpdateProfile();

  const defaultValues = useMemo(() => toFormValues(profile), [profile]);

  const {
    register,
    handleSubmit,
    reset,
    watch,
    formState: { errors, isDirty },
  } = useForm({
    resolver: zodResolver(profileSchema),
    defaultValues,
  });

  /* Seed the form once per profile. Re-seeding on every `profile` change would
     let an autosave response overwrite whatever the user is currently typing,
     since each save writes a fresh object into the query cache. */
  const seededIdRef = useRef(null);
  const [recovered, setRecovered] = useState(false);

  useEffect(() => {
    if (!profile?.id || seededIdRef.current === profile.id) {
      return;
    }
    seededIdRef.current = profile.id;

    // A previous session's autosave may have failed after the user left.
    const backup = readBackup('contact');
    if (backup) {
      reset({ ...toFormValues(profile), ...backup });
      setRecovered(true);
      return;
    }

    reset(toFormValues(profile));
  }, [profile, reset]);

  const summary = watch('summary') || '';
  const summaryTooShort = summary.trim().length > 0 && summary.trim().length < SUMMARY_MIN_LENGTH;

  const autosave = useAutosave({
    sectionName: 'contact',
    getPayload: () => toPayload(watch()),
    // Never PATCH a half-typed URL or email — a failed autosave is invisible.
    canSave: (payload) => profileSchema.safeParse(payload).success,
    save: (payload) => patchMutation.mutateAsync(payload),
  });

  const { markDirty, flush } = autosave;

  /* Subscribe to value changes rather than RHF's isDirty: isDirty latches true
     and never fires again, so edits after the first autosave would be lost. */
  useEffect(() => {
    const subscription = watch(() => markDirty());
    return () => subscription.unsubscribe();
  }, [watch, markDirty]);

  // Flush pending edits when the step unmounts (user switched sections).
  useEffect(() => () => { flush(); }, [flush]);

  const onSubmit = async (values) => {
    const payload = toPayload(values);
    try {
      await updateMutation.mutateAsync(payload);
      toast.success('Contact details saved.');
      reset(payload);
      clearBackup('contact');
      setRecovered(false);
    } catch {
      // useUpdateProfile already surfaces the error toast.
    }
  };

  return (
    <SectionShell
      title="Contact & Summary"
      description="How employers reach you, plus the summary the AI tailors per application."
      action={<SaveStatus status={autosave.status} lastSavedAt={autosave.lastSavedAt} />}
    >
      <form onSubmit={handleSubmit(onSubmit)} noValidate className="space-y-5">
        {recovered ? (
          <Alert variant="info">
            We recovered unsaved changes from your last session. Review them and save, or{' '}
            <button
              type="button"
              className="font-medium underline"
              onClick={() => {
                clearBackup('contact');
                reset(toFormValues(profile));
                setRecovered(false);
              }}
            >
              discard them
            </button>
            .
          </Alert>
        ) : null}

        <div className="grid gap-4 sm:grid-cols-2">
          <FormField
            id="full_name"
            label="Full name"
            placeholder="Muhammad Rizwan"
            error={errors.full_name}
            registration={register('full_name')}
          />
          <FormField
            id="professional_title"
            label="Professional title"
            placeholder="Full Stack Web App Developer"
            error={errors.professional_title}
            registration={register('professional_title')}
          />
          <FormField
            id="cv_email"
            label="Display email"
            type="email"
            placeholder="you@example.com"
            hint="Shown on your CV — separate from your login email."
            error={errors.email}
            registration={register('email')}
          />
          <FormField
            id="phone"
            label="Phone"
            placeholder="+92 300 1234567"
            hint="Include the country code."
            error={errors.phone}
            registration={register('phone')}
          />
          <FormField
            id="city"
            label="City"
            placeholder="Lahore"
            error={errors.city}
            registration={register('city')}
          />
          <FormField
            id="country"
            label="Country"
            placeholder="Pakistan"
            error={errors.country}
            registration={register('country')}
          />
        </div>

        <div className="grid gap-4 sm:grid-cols-3">
          <FormField
            id="linkedin_url"
            label="LinkedIn"
            placeholder="linkedin.com/in/you"
            error={errors.linkedin_url}
            registration={register('linkedin_url')}
          />
          <FormField
            id="github_url"
            label="GitHub"
            placeholder="github.com/you"
            error={errors.github_url}
            registration={register('github_url')}
          />
          <FormField
            id="portfolio_url"
            label="Portfolio"
            placeholder="yoursite.dev"
            error={errors.portfolio_url}
            registration={register('portfolio_url')}
          />
        </div>

        <TextareaField
          id="summary"
          label="Professional summary"
          rows={5}
          placeholder="Two or three sentences on what you build and the impact you have had."
          error={errors.summary}
          registration={register('summary')}
          hint={`${summary.trim().length} characters — ${SUMMARY_MIN_LENGTH}+ earns the summary points.`}
        />

        {summaryTooShort ? (
          <Alert variant="warning">
            Your summary is under {SUMMARY_MIN_LENGTH} characters. It will still save, but a longer
            summary scores better and gives the AI more to work with when tailoring applications.
          </Alert>
        ) : null}

        <div className="flex items-center justify-end gap-3">
          <Button type="submit" loading={updateMutation.isPending}>
            Save section
          </Button>
        </div>
      </form>
    </SectionShell>
  );
}
