import { useParams } from 'react-router-dom';

import { Alert } from '@/components/ui';
import { ResetPasswordForm } from '@/features/auth/components/ResetPasswordForm';

export default function ResetPasswordPage() {
  const { token } = useParams();

  if (!token) {
    return <Alert variant="error">Reset token is missing. Please use the link from your email.</Alert>;
  }

  return <ResetPasswordForm token={token} />;
}
