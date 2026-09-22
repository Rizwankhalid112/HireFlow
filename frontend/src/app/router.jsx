import { lazy, Suspense } from 'react';
import { Route, Routes } from 'react-router-dom';

import { AppLayout } from '@/components/layout/AppLayout';
import { AuthLayout } from '@/components/layout/AuthLayout';
import { PublicLayout } from '@/components/layout/PublicLayout';
import { ProtectedRoute } from '@/routes/ProtectedRoute';
import { PublicOnlyRoute } from '@/routes/PublicOnlyRoute';
import { Spinner } from '@/components/ui';

import { routeLoaders } from './routes';

/* Loaders live in routes.js so the sidebar can warm a chunk on hover — see the
   note there. `lazy()` resolves instantly when the prefetch already ran. */
const LandingPage = lazy(routeLoaders['/']);
const HomePage = lazy(routeLoaders['/home']);
const NotFoundPage = lazy(() => import('@/pages/NotFoundPage'));
const LoginPage = lazy(routeLoaders['/login']);
const RegisterPage = lazy(routeLoaders['/register']);
const ForgotPasswordPage = lazy(routeLoaders['/forgot-password']);
const ResetPasswordPage = lazy(routeLoaders['/reset-password']);
const VerifyEmailPage = lazy(routeLoaders['/verify-email']);
const CVBuilderPage = lazy(routeLoaders['/cv-builder']);
const JobMatchPage = lazy(routeLoaders['/job-match']);
const JobsPage = lazy(routeLoaders['/jobs']);
const MyCVsPage = lazy(routeLoaders['/my-cvs']);

function PageLoader() {
  return (
    <div className="flex min-h-[40vh] items-center justify-center">
      <Spinner />
    </div>
  );
}

export function AppRouter() {
  return (
    <Suspense fallback={<PageLoader />}>
      <Routes>
        <Route element={<PublicLayout />}>
          <Route index element={<LandingPage />} />
        </Route>

        <Route element={<AuthLayout />}>
          <Route element={<PublicOnlyRoute />}>
            <Route path="login" element={<LoginPage />} />
            <Route path="register" element={<RegisterPage />} />
          </Route>
          <Route path="forgot-password" element={<ForgotPasswordPage />} />
          <Route path="reset-password/:token" element={<ResetPasswordPage />} />
          <Route path="verify-email/:token" element={<VerifyEmailPage />} />
        </Route>

        <Route element={<ProtectedRoute />}>
          <Route element={<AppLayout />}>
            <Route path="home" element={<HomePage />} />
            <Route path="cv-builder" element={<CVBuilderPage />} />
            <Route path="job-match" element={<JobMatchPage />} />
            <Route path="jobs" element={<JobsPage />} />
            <Route path="my-cvs" element={<MyCVsPage />} />
          </Route>
        </Route>

        <Route element={<PublicLayout />}>
          <Route path="*" element={<NotFoundPage />} />
        </Route>
      </Routes>
    </Suspense>
  );
}
