import { zodResolver } from '@hookform/resolvers/zod';
import { useForm } from 'react-hook-form';
import { Link } from 'react-router-dom';

import { Button, FormField } from '@/components/ui';
import { GoogleSignInButton } from '@/features/auth/components/GoogleSignInButton';
import { useLogin } from '@/features/auth/api/authQueries';
import { loginSchema } from '@/features/auth/schemas/authSchemas';

export function LoginForm() {
  const loginMutation = useLogin();
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm({
    resolver: zodResolver(loginSchema),
    defaultValues: {
      email: '',
      password: '',
    },
  });

  return (
    <form
      className="space-y-4"
      onSubmit={handleSubmit((values) => loginMutation.mutate(values))}
      noValidate
    >
      <div className="space-y-1">
        <h1 className="text-2xl font-semibold text-slate-900 dark:text-slate-100">Welcome back</h1>
        <p className="text-sm text-slate-600 dark:text-slate-400">
          Sign in to continue tracking your job search.
        </p>
      </div>

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
        autoComplete="current-password"
        placeholder="Enter your password"
        registration={register('password')}
        error={errors.password}
      />

      <div className="flex justify-end">
        <Link to="/forgot-password" className="text-sm font-medium text-indigo-600 hover:text-indigo-700">
          Forgot password?
        </Link>
      </div>

      <Button type="submit" className="w-full" loading={loginMutation.isPending}>
        Sign in
      </Button>

      <div className="relative py-2 text-center text-xs uppercase tracking-wide text-slate-400">
        <span className="bg-white px-2 dark:bg-slate-900">or</span>
      </div>

      <GoogleSignInButton />

      <p className="text-center text-sm text-slate-600 dark:text-slate-400">
        Don&apos;t have an account?{' '}
        <Link to="/register" className="font-medium text-indigo-600 hover:text-indigo-700">
          Create one
        </Link>
      </p>
    </form>
  );
}
