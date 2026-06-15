import { useEffect } from 'react';
import { Link, useParams } from 'react-router-dom';

import { Alert, Button, Spinner } from '@/components/ui';
import { useVerifyEmail } from '@/features/auth/api/authQueries';

export default function VerifyEmailPage() {
  const { token } = useParams();
  const verifyEmailMutation = useVerifyEmail();

  useEffect(() => {
    if (token) {
      verifyEmailMutation.mutate(token);
    }
  }, [token]);

  if (!token) {
    return <Alert variant="error">Verification token is missing.</Alert>;
  }

  if (verifyEmailMutation.isPending) {
    return (
      <div className="space-y-4 text-center">
        <Spinner />
        <p className="text-sm text-slate-600 dark:text-slate-400">Verifying your email...</p>
      </div>
    );
  }

  if (verifyEmailMutation.isError) {
    return (
      <div className="space-y-4 text-center">
        <Alert variant="error">
          {verifyEmailMutation.error?.response?.data?.detail ||
            'This verification link is invalid or has expired.'}
        </Alert>
        <Link to="/register">
          <Button variant="secondary">Create a new account</Button>
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-4 text-center">
      <Alert variant="success">Email verified! Redirecting to your dashboard...</Alert>
      <Spinner />
    </div>
  );
}
