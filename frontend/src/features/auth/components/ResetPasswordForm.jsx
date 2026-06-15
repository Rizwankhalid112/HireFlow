import { zodResolver } from '@hookform/resolvers/zod';
import { useForm } from 'react-hook-form';
import { Link } from 'react-router-dom';

import { Button, FormField } from '@/components/ui';
import { useResetPassword } from '@/features/auth/api/authQueries';
import { resetPasswordSchema } from '@/features/auth/schemas/authSchemas';

export function ResetPasswordForm({ token }) {
  const resetPasswordMutation = useResetPassword();
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm({
    resolver: zodResolver(resetPasswordSchema),
    defaultValues: {
      new_password: '',
      new_password2: '',
    },
  });

  return (
    <form
      className="space-y-4"
      onSubmit={handleSubmit((values) =>
        resetPasswordMutation.mutate({
          token,
          new_password: values.new_password,
          new_password2: values.new_password2,
        }),
      )}
      noValidate
    >
      <div className="space-y-1">
        <h1 className="text-2xl font-semibold text-slate-900 dark:text-slate-100">Reset password</h1>
        <p className="text-sm text-slate-600 dark:text-slate-400">
          Choose a new password for your account.
        </p>
      </div>

      <FormField
        id="new_password"
        label="New password"
        type="password"
        autoComplete="new-password"
        placeholder="At least 8 characters"
        registration={register('new_password')}
        error={errors.new_password}
      />

      <FormField
        id="new_password2"
        label="Confirm new password"
        type="password"
        autoComplete="new-password"
        placeholder="Repeat your password"
        registration={register('new_password2')}
        error={errors.new_password2}
      />

      <Button type="submit" className="w-full" loading={resetPasswordMutation.isPending}>
        Reset password
      </Button>

      <p className="text-center text-sm text-slate-600 dark:text-slate-400">
        <Link to="/login" className="font-medium text-indigo-600 hover:text-indigo-700">
          Back to sign in
        </Link>
      </p>
    </form>
  );
}
