import { Link } from 'react-router-dom';

import { Button } from '@/components/ui';

export default function NotFoundPage() {
  return (
    <div className="flex min-h-[60vh] flex-col items-center justify-center gap-3 px-5 text-center">
      <p className="tabular text-xs font-semibold tracking-widest text-accent uppercase">404</p>
      <h1 className="text-2xl font-semibold tracking-tight">Page not found</h1>
      <p className="max-w-sm text-[13px] leading-6 text-muted">
        The page you are looking for does not exist, or may have been moved.
      </p>
      <Link to="/" className="mt-2">
        <Button icon="chevronLeft">Back to home</Button>
      </Link>
    </div>
  );
}
