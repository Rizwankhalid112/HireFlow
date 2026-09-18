import { Navigate, Outlet } from 'react-router-dom';

import { useAppSelector } from '@/hooks/useAppSelector';

export function PublicOnlyRoute() {
  const isAuthenticated = useAppSelector((state) => state.auth.isAuthenticated);

  if (isAuthenticated) {
    return <Navigate to="/home" replace />;
  }

  return <Outlet />;
}
