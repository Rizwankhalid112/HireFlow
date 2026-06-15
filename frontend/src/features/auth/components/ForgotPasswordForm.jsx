import { zodResolver } from '@hookform/resolvers/zod';
import { useForm } from 'react-hook-form';
import { Link } from 'react-router-dom';

import { Alert, Button, FormField } from '@/components/ui';
import { useForgotPassword } from '@/features/auth/api/authQueries';
import { forgotPasswordSchema } from '@/features/auth/schemas/authSchemas';

export function ForgotPasswordForm() {
  const forgotPasswordMutation = useForgotPassword();
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm({
    resolver: zodResolver(forgotPasswordSchema),
    defaultValues: { email: '' },
  });

  return (
    <form
      className="space-y-4"
      onSubmit={handleSubmit((values) => forgotPasswordMutation.mutate(values))}
      noValidate
    >
      <div className="space-y-1">
        <h1 className="text-2xl font-semibold text-slate-900 dark:text-slate-100">Forgot password</h1>
        <p className="text-sm text-slate-600 dark:text-slate-400">
          Enter your email and we&apos;ll send you a reset link if an account exists.
        </p>
      </div>

      {forgotPasswordMutation.isSuccess ? (
        <Alert variant="success">
          If that email is registered, you&apos;ll receive a link.
        </Alert>
      ) : null}

      <FormField
        id="email"
        label="Email"
        type="email"
        autoComplete="email"
        placeholder="you@example.com"
        registration={register('email')}
        error={errors.email}
      />

      <Button type="submit" className="w-full" loading={forgotPasswordMutation.isPending}>
        Send reset link
      </Button>

      <p className="text-center text-sm text-slate-600 dark:text-slate-400">
        <Link to="/login" className="font-medium text-indigo-600 hover:text-indigo-700">
          Back to sign in
        </Link>
      </p>
    </form>
  );
}
