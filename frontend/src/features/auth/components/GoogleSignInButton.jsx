import { useGoogleLogin } from '@react-oauth/google';
import { toast } from 'sonner';

import { Button } from '@/components/ui';
import { useGoogleLogin as useGoogleLoginMutation } from '@/features/auth/api/authQueries';

export function GoogleSignInButton() {
  const googleLoginMutation = useGoogleLoginMutation();

  const login = useGoogleLogin({
    onSuccess: (tokenResponse) => {
      googleLoginMutation.mutate({ access_token: tokenResponse.access_token });
    },
    onError: () => {
      toast.error('Google sign-in was cancelled or failed.');
    },
  });

  return (
    <Button
      type="button"
      variant="secondary"
      className="w-full"
      loading={googleLoginMutation.isPending}
      onClick={() => login()}
    >
      Continue with Google
    </Button>
  );
}
