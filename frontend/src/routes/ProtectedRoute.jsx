import { Navigate, Outlet, useLocation } from 'react-router-dom';

import { Spinner } from '@/components/ui';
import { useAppSelector } from '@/hooks/useAppSelector';

export function ProtectedRoute() {
  const isAuthenticated = useAppSelector((state) => state.auth.isAuthenticated);
  const location = useLocation();

  if (!isAuthenticated) {
    return <Navigate to="/login" replace state={{ from: location }} />;
  }

  return <Outlet />;
}

export function ProtectedRouteFallback() {
  return (
    <div className="flex min-h-screen items-center justify-center">
      <Spinner />
    </div>
  );
}
