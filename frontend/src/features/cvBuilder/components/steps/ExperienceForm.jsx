import { useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';

import { Button, Checkbox, FormField, Modal, SelectField } from '@/components/ui';

import { EMPLOYMENT_TYPES, LOCATION_TYPES, MONTHS } from '../../constants';
import { experienceSchema } from '../../schemas/cvSchemas';
import { toNullableInt } from '../../utils/payload';

const EMPTY = {
  company_name: '',
  role_title: '',
  employment_type: '',
  location: '',
  location_type: '',
  start_month: '',
  start_year: '',
  end_month: '',
  end_year: '',
  is_current: false,
};

function toFormValues(experience) {
  if (!experience) return EMPTY;

  return {
    company_name: experience.company_name ?? '',
    role_title: experience.role_title ?? '',
    employment_type: experience.employment_type ?? '',
    location: experience.location ?? '',
    location_type: experience.location_type ?? '',
    start_month: experience.start_month != null ? String(experience.start_month) : '',
    start_year: experience.start_year != null ? String(experience.start_year) : '',
    end_month: experience.end_month != null ? String(experience.end_month) : '',
    end_year: experience.end_year != null ? String(experience.end_year) : '',
    is_current: Boolean(experience.is_current),
  };
}

export function ExperienceForm({ open, onClose, experience, onSubmit, loading }) {
  const {
    register,
    handleSubmit,
    reset,
    watch,
    formState: { errors },
  } = useForm({
    resolver: zodResolver(experienceSchema),
    defaultValues: toFormValues(experience),
  });

  useEffect(() => {
    if (open) {
      reset(toFormValues(experience));
    }
  }, [open, experience, reset]);

  const isCurrent = watch('is_current');

  const submit = handleSubmit((values) => {
    onSubmit({
      company_name: values.company_name.trim(),
      role_title: values.role_title.trim(),
      employment_type: values.employment_type || '',
      location: values.location || '',
      location_type: values.location_type || '',
      start_month: toNullableInt(values.start_month),
      start_year: toNullableInt(values.start_year),
      // The backend nulls these when is_current, but sending them clean avoids
      // a confusing echo in the response.
      end_month: values.is_current ? null : toNullableInt(values.end_month),
      end_year: values.is_current ? null : toNullableInt(values.end_year),
      is_current: values.is_current,
    });
  });

  return (
    <Modal
      open={open}
      onClose={onClose}
      title={experience ? 'Edit experience' : 'Add experience'}
      size="lg"
      footer={
        <>
          <Button variant="ghost" size="sm" onClick={onClose} disabled={loading}>
            Cancel
          </Button>
          <Button size="sm" onClick={submit} loading={loading}>
            {experience ? 'Save changes' : 'Add experience'}
          </Button>
        </>
      }
    >
      <form onSubmit={submit} noValidate className="space-y-4">
        <div className="grid gap-4 sm:grid-cols-2">
          <FormField
            id="company_name"
            label="Company"
            placeholder="Aqua Security"
            error={errors.company_name}
            registration={register('company_name')}
          />
          <FormField
            id="role_title"
            label="Role"
            placeholder="Backend Engineer"
            error={errors.role_title}
            registration={register('role_title')}
          />
          <SelectField
            id="employment_type"
            label="Employment type"
            placeholder="Select type"
            options={EMPLOYMENT_TYPES}
            error={errors.employment_type}
            registration={register('employment_type')}
          />
          <SelectField
            id="location_type"
            label="Work setting"
            placeholder="Select setting"
            options={LOCATION_TYPES}
            error={errors.location_type}
            registration={register('location_type')}
          />
        </div>

        <FormField
          id="location"
          label="Location"
          placeholder="Lahore, Pakistan"
          error={errors.location}
          registration={register('location')}
        />

        <div className="grid gap-4 sm:grid-cols-2">
          <SelectField
            id="start_month"
            label="Start month"
            placeholder="Month (optional)"
            options={MONTHS}
            error={errors.start_month}
            registration={register('start_month')}
          />
          <FormField
            id="start_year"
            label="Start year"
            type="number"
            placeholder="2023"
            error={errors.start_year}
            registration={register('start_year')}
          />
        </div>

        <Checkbox
          id="is_current"
          label="I currently work here"
          {...register('is_current')}
        />

        {!isCurrent ? (
          <div className="grid gap-4 sm:grid-cols-2">
            <SelectField
              id="end_month"
              label="End month"
              placeholder="Month (optional)"
              options={MONTHS}
              error={errors.end_month}
              registration={register('end_month')}
            />
            <FormField
              id="end_year"
              label="End year"
              type="number"
              placeholder="2025"
              error={errors.end_year}
              registration={register('end_year')}
            />
          </div>
        ) : null}
      </form>
    </Modal>
  );
}
