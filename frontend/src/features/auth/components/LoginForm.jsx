import { zodResolver } from '@hookform/resolvers/zod';
import { useForm } from 'react-hook-form';
import { Link } from 'react-router-dom';

import { googleEnabled } from '@/app/providers';
import { Button, FormField } from '@/components/ui';
import { useLogin } from '@/features/auth/api/authQueries';
import { GoogleSignInButton } from '@/features/auth/components/GoogleSignInButton';
import { loginSchema } from '@/features/auth/schemas/authSchemas';

export function LoginForm() {
  const loginMutation = useLogin();
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm({
    resolver: zodResolver(loginSchema),
    defaultValues: { email: '', password: '' },
  });

  return (
    <form
      className="flex flex-col gap-5"
      onSubmit={handleSubmit((values) => loginMutation.mutate(values))}
      noValidate
    >
      <header className="flex flex-col gap-1">
        <h1 className="text-2xl font-semibold tracking-tight">Welcome back</h1>
        <p className="text-[13px] text-muted">Sign in to pick up where you left off.</p>
      </header>

      <div className="flex flex-col gap-3.5">
        <FormField
          id="email"
          label="Email"
          type="email"
          autoComplete="email"
          placeholder="you@company.com"
          error={errors.email}
          registration={register('email')}
        />

        <div className="flex flex-col gap-1.5">
          <div className="flex items-center justify-between">
            <label htmlFor="password" className="text-xs font-medium text-ink">
              Password
            </label>
            <Link to="/forgot-password" className="text-xs font-medium text-accent hover:underline">
              Forgot?
            </Link>
          </div>
          <FormField
            id="password"
            type="password"
            autoComplete="current-password"
            placeholder="••••••••"
            error={errors.password}
            registration={register('password')}
          />
        </div>

        <Button type="submit" size="lg" className="w-full" loading={loginMutation.isPending}>
          Sign in
        </Button>
      </div>

      {/* Both hidden together when no Google client id was built in, or the
          divider is left pointing at nothing. */}
      {googleEnabled ? (
        <>
          <div className="flex items-center gap-3">
            <span className="h-px flex-1 bg-line" />
            <span className="text-[11px] text-subtle">OR</span>
            <span className="h-px flex-1 bg-line" />
          </div>

          <GoogleSignInButton />
        </>
      ) : null}

      <p className="text-center text-xs text-muted">
        New here?{' '}
        <Link to="/register" className="font-medium text-accent hover:underline">
          Create an account
        </Link>
      </p>
    </form>
  );
}
