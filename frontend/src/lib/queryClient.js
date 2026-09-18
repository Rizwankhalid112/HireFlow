import { QueryClient } from '@tanstack/react-query';

/*
 * Defaults, and why each one is what it is.
 *
 * `retry: 1` — a 401 is handled by the axios interceptor (refresh + replay),
 * so a retry here only helps a genuine network blip. Retrying a 400 or a 404
 * wastes a round trip and delays the error the user needs to see, hence the
 * predicate rather than a flat count.
 *
 * `staleTime` — most of this data changes only when the user changes it, and
 * every mutation already invalidates its own keys. Five minutes stops React
 * Query re-fetching a CV that nothing has touched.
 *
 * `gcTime` — a cache entry outlives its last observer by half an hour, which
 * is what makes going Jobs → CV Builder → Jobs paint instantly instead of
 * re-fetching a list the user saw thirty seconds ago.
 */
const isClientError = (error) => {
  const status = error?.response?.status;
  return typeof status === 'number' && status >= 400 && status < 500;
};

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: (failureCount, error) => !isClientError(error) && failureCount < 1,
      staleTime: 1000 * 60 * 5,
      gcTime: 1000 * 60 * 30,
      refetchOnWindowFocus: false,
      refetchOnReconnect: true,
    },
    mutations: {
      retry: 0,
    },
  },
});
