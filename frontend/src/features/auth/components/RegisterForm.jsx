import { zodResolver } from '@hookform/resolvers/zod';
import { useForm } from 'react-hook-form';
import { Link } from 'react-router-dom';

import { Button, FormField } from '@/components/ui';
import { useRegister } from '@/features/auth/api/authQueries';
import { registerSchema } from '@/features/auth/schemas/authSchemas';

export function RegisterForm() {
  const registerMutation = useRegister();
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm({
    resolver: zodResolver(registerSchema),
    defaultValues: {
      email: '',
      full_name: '',
      password: '',
      password2: '',
    },
  });

  return (
    <form
      className="space-y-4"
      onSubmit={handleSubmit((values) => registerMutation.mutate(values))}
      noValidate
    >
      <div className="space-y-1">
        <h1 className="text-2xl font-semibold text-slate-900 dark:text-slate-100">Create account</h1>
        <p className="text-sm text-slate-600 dark:text-slate-400">
          Start organizing your job search in minutes.
        </p>
      </div>

      <FormField
        id="full_name"
        label="Full name"
        autoComplete="name"
        placeholder="Jane Doe"
        registration={register('full_name')}
        error={errors.full_name}
      />

      <FormField
        id="email"
        label="Email"
        type="email"
        autoComplete="email"
        placeholder="you@example.com"
        registration={register('email')}
        error={errors.email}
      />

      <FormField
        id="password"
        label="Password"
        type="password"
        autoComplete="new-password"
        placeholder="At least 8 characters"
        registration={register('password')}
        error={errors.password}
      />

      <FormField
        id="password2"
        label="Confirm password"
        type="password"
        autoComplete="new-password"
        placeholder="Repeat your password"
        registration={register('password2')}
        error={errors.password2}
      />

      <Button type="submit" className="w-full" loading={registerMutation.isPending}>
        Create account
      </Button>

      <p className="text-center text-sm text-slate-600 dark:text-slate-400">
        Already have an account?{' '}
        <Link to="/login" className="font-medium text-indigo-600 hover:text-indigo-700">
          Sign in
        </Link>
      </p>
    </form>
  );
}
