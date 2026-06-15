import { Link } from 'react-router-dom';

import { Button } from '@/components/ui';

export default function NotFoundPage() {
  return (
    <div className="flex min-h-[60vh] flex-col items-center justify-center px-4 text-center">
      <p className="text-sm font-semibold uppercase tracking-wide text-indigo-600">404</p>
      <h1 className="mt-2 text-3xl font-bold text-slate-900 dark:text-slate-100">Page not found</h1>
      <p className="mt-2 max-w-md text-sm text-slate-600 dark:text-slate-400">
        The page you are looking for does not exist or may have been moved.
      </p>
      <Link to="/" className="mt-6">
        <Button>Back to home</Button>
      </Link>
    </div>
  );
}
