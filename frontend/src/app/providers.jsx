import { GoogleOAuthProvider } from '@react-oauth/google';
import { QueryClientProvider } from '@tanstack/react-query';
import { Provider } from 'react-redux';
import { BrowserRouter } from 'react-router-dom';
import { Toaster } from 'sonner';

import { AppRouter } from '@/app/router';
import { store } from '@/app/store';
import { ErrorBoundary } from '@/components/ErrorBoundary';
import { ThemeProvider } from '@/context/ThemeContext';
import { queryClient } from '@/lib/queryClient';

/* Baked in at build time, so it is either present in this bundle or it never
   will be. Exported because the sign-in button uses the same answer to decide
   whether to render at all. */
export const googleClientId = import.meta.env.VITE_GOOGLE_CLIENT_ID || '';
export const googleEnabled = Boolean(googleClientId);

/* Mounting GoogleOAuthProvider with an empty clientId loads Google's script
   and lets it fail inside its own minified code the moment anything calls
   useGoogleLogin — which took down the whole login page, the one route that
   renders the button. Social sign-in is optional; a missing client id should
   remove the button, not the page. */
function WithGoogle({ children }) {
  if (!googleEnabled) return children;

  return <GoogleOAuthProvider clientId={googleClientId}>{children}</GoogleOAuthProvider>;
}

export function Providers() {
  return (
    <Provider store={store}>
      <QueryClientProvider client={queryClient}>
        <ThemeProvider>
          <WithGoogle>
            <BrowserRouter>
              <ErrorBoundary>
                <AppRouter />
              </ErrorBoundary>
              <Toaster position="top-right" richColors closeButton />
            </BrowserRouter>
          </WithGoogle>
        </ThemeProvider>
      </QueryClientProvider>
    </Provider>
  );
}
