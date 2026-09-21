import { useGoogleLogin } from '@react-oauth/google';
import { toast } from 'sonner';

import { googleEnabled } from '@/app/providers';
import { Button } from '@/components/ui';
import { useGoogleLogin as useGoogleLoginMutation } from '@/features/auth/api/authQueries';

/* `useGoogleLogin` requires GoogleOAuthProvider above it, and that provider is
   only mounted when a client id was compiled into the bundle. Hooks cannot be
   called conditionally, so the guard has to be a separate component — the
   inner one is simply never rendered without a client id. */
function GoogleButton() {
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
      size="lg"
      className="w-full"
      loading={googleLoginMutation.isPending}
      onClick={() => login()}
    >
      Continue with Google
    </Button>
  );
}

export function GoogleSignInButton() {
  return googleEnabled ? <GoogleButton /> : null;
}
