import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';

import { extractApiError } from '@/utils/extractApiError';

import * as jobsApi from './jobsApi';

export const jobKeys = {
  all: ['jobs'],
  list: (params) => ['jobs', 'list', params],
  detail: (id) => ['jobs', 'detail', id],
  stats: ['jobs', 'stats'],
};

/* `keepPreviousData` holds the current page on screen while the next one loads,
   so paging and typing in the search box do not flash an empty list. */
export function useJobs(params) {
  return useQuery({
    queryKey: jobKeys.list(params),
    queryFn: () => jobsApi.listJobs(params).then((r) => r.data),
    placeholderData: keepPreviousData,
    retry: false,
  });
}

export function useJob(id) {
  return useQuery({
    queryKey: jobKeys.detail(id),
    queryFn: () => jobsApi.getJob(id).then((r) => r.data),
    enabled: Boolean(id),
    retry: false,
  });
}

export function useJobStats() {
  return useQuery({
    queryKey: jobKeys.stats,
    queryFn: () => jobsApi.getJobStats().then((r) => r.data),
    staleTime: 60 * 1000,
    retry: false,
  });
}

export function useDeleteJob() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id) => jobsApi.deleteJob(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: jobKeys.all });
      // Worth saying out loud: this only removes our copy. The next nightly
      // gather brings it back if the employer still lists it.
      toast.success('Removed from your list.');
    },
    onError: (error) => toast.error(extractApiError(error)),
  });
}
