import { Link, Outlet } from 'react-router-dom';

import { Card } from '@/components/ui';

export function AuthLayout() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-gradient-to-br from-indigo-50 via-white to-slate-100 px-4 py-10 dark:from-slate-950 dark:via-slate-900 dark:to-slate-950">
      <div className="w-full max-w-md">
        <div className="mb-6 text-center">
          <Link to="/" className="text-2xl font-bold text-indigo-600">
            HireFlow
          </Link>
          <p className="mt-2 text-sm text-slate-600 dark:text-slate-400">
            Track. Automate. Get Hired.
          </p>
        </div>
        <Card>
          <Outlet />
        </Card>
      </div>
    </div>
  );
}
