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

const googleClientId = import.meta.env.VITE_GOOGLE_CLIENT_ID || '';

export function Providers() {
  return (
    <Provider store={store}>
      <QueryClientProvider client={queryClient}>
        <ThemeProvider>
          <GoogleOAuthProvider clientId={googleClientId}>
            <BrowserRouter>
              <ErrorBoundary>
                <AppRouter />
              </ErrorBoundary>
              <Toaster position="top-right" richColors closeButton />
            </BrowserRouter>
          </GoogleOAuthProvider>
        </ThemeProvider>
      </QueryClientProvider>
    </Provider>
  );
}
