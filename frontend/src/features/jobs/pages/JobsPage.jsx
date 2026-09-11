import { useState } from 'react';
import { useNavigate } from 'react-router-dom';

import { Alert, Button, Card, ConfirmDialog, Input, Select, Spinner } from '@/components/ui';

import { useDeleteJob, useJobStats, useJobs } from '../api/jobsQueries';
import * as jobsApi from '../api/jobsApi';
import { JobCard } from '../components/JobCard';
import { JobDetailModal } from '../components/JobDetailModal';
import { useDebouncedValue } from '@/features/cvBuilder/hooks/useDebouncedValue';

/*
 * The harvested jobs.
 *
 * Everything on this page is paginated and server-filtered. Nothing loads the
 * whole table, and no filter runs client-side — the table is built to hold
 * millions of rows, so a page that fetched everything and filtered in the
 * browser would work fine today and fall over in a month.
 */

const SOURCES = [
  { value: '', label: 'All sources' },
  { value: 'greenhouse', label: 'Greenhouse' },
  { value: 'ashby', label: 'Ashby' },
  { value: 'lever', label: 'Lever' },
  { value: 'workable', label: 'Workable' },
];

const REMOTE = [
  { value: '', label: 'Any arrangement' },
  { value: 'remote', label: 'Remote' },
  { value: 'hybrid', label: 'Hybrid' },
  { value: 'onsite', label: 'On-site' },
];

export default function JobsPage() {
  const [search, setSearch] = useState('');
  const [location, setLocation] = useState('');
  const [source, setSource] = useState('');
  const [remoteType, setRemoteType] = useState('');
  const [page, setPage] = useState(1);
  const [openJobId, setOpenJobId] = useState(null);
  const [pendingDelete, setPendingDelete] = useState(null);
  const [useCv, setUseCv] = useState(false);
  const [tailoring, setTailoring] = useState(null);
  const navigate = useNavigate();

  // Debounced so typing does not fire a query per keystroke against a large table.
  const debouncedSearch = useDebouncedValue(search, 400);
  const debouncedLocation = useDebouncedValue(location, 400);

  const params = {
    page,
    ...(useCv ? { match: 'cv' } : {}),
    ...(debouncedSearch ? { search: debouncedSearch } : {}),
    ...(debouncedLocation ? { location: debouncedLocation } : {}),
    ...(source ? { source } : {}),
    ...(remoteType ? { remote_type: remoteType } : {}),
  };

  const { data, error, isLoading, isFetching, isError } = useJobs(params);
  const { data: stats } = useJobStats();
  const remove = useDeleteJob();

  /* The description is not in the list payload — it would be several thousand
     characters per row — so it is fetched for the one job being tailored, then
     handed to the match page through router state. */
  const tailor = async (job) => {
    setTailoring(job.id);
    try {
      const { data: full } = await jobsApi.getJob(job.id);
      navigate('/job-match', {
        state: {
          jdText: full.description,
          jobTitle: full.title,
          company: full.company_name,
        },
      });
    } finally {
      setTailoring(null);
    }
  };

  const jobs = data?.results ?? [];
  const total = data?.count ?? 0;
  const pageSize = 25;
  const lastPage = Math.max(1, Math.ceil(total / pageSize));

  const onFilterChange = (setter) => (value) => {
    setter(value);
    setPage(1); // a filter change invalidates the current page number
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold text-slate-900 dark:text-slate-100">Jobs</h1>
          <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">
            Gathered daily from company job boards. Apply on the employer&apos;s own site.
          </p>
        </div>
        {stats ? (
          <p className="text-xs text-slate-500 dark:text-slate-400">
            {stats.total_jobs.toLocaleString()} jobs ·{' '}
            {stats.by_source.map((s) => `${s.count} ${s.source}`).join(' · ')}
          </p>
        ) : null}
      </div>

      <Card>
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <Input
            placeholder="Search title or company"
            value={search}
            onChange={(e) => onFilterChange(setSearch)(e.target.value)}
            aria-label="Search jobs"
          />
          <Input
            placeholder="Location"
            value={location}
            onChange={(e) => onFilterChange(setLocation)(e.target.value)}
            aria-label="Filter by location"
          />
          <Select
            value={source}
            onChange={(e) => onFilterChange(setSource)(e.target.value)}
            aria-label="Filter by source"
            options={SOURCES}
          />
          <Select
            value={remoteType}
            onChange={(e) => onFilterChange(setRemoteType)(e.target.value)}
            aria-label="Filter by working arrangement"
            options={REMOTE}
          />
        </div>
        <div className="mt-3 flex flex-wrap items-center gap-3 border-t border-slate-200 pt-3 dark:border-slate-800">
          <label className="flex cursor-pointer items-center gap-2 text-sm text-slate-700 dark:text-slate-200">
            <input
              type="checkbox"
              checked={useCv}
              onChange={(e) => onFilterChange(setUseCv)(e.target.checked)}
              className="h-4 w-4 rounded border-slate-300 dark:border-slate-600"
            />
            Find jobs using my CV
          </label>
          {useCv && data?.matched_against?.length ? (
            <span className="text-xs text-slate-500 dark:text-slate-400">
              Matching on {data.matched_against.slice(0, 8).join(', ')}
            </span>
          ) : (
            <span className="text-xs text-slate-500 dark:text-slate-400">
              Ranks by the skills on your CV instead of by date.
            </span>
          )}
        </div>

        {remoteType ? (
          // Honesty about a real gap: Greenhouse does not publish this field, so
          // for those listings it is inferred from wording and some are simply
          // unknown. Silently returning fewer results would look like a bug.
          <p className="mt-2 text-xs text-slate-500 dark:text-slate-400">
            Some boards do not state the working arrangement, so listings without one are hidden
            by this filter.
          </p>
        ) : null}
      </Card>

      {isError ? (
        <Alert variant={useCv ? 'warning' : 'error'}>
          {/* Usually "add some skills first", which the user can act on. */}
          {error?.response?.data?.detail || 'Jobs could not be loaded.'}
        </Alert>
      ) : null}

      {isLoading ? (
        <Spinner className="py-16" />
      ) : jobs.length === 0 ? (
        <Card>
          <p className="py-8 text-center text-sm text-slate-600 dark:text-slate-400">
            {total === 0 && !debouncedSearch && !debouncedLocation && !source && !remoteType
              ? 'No jobs have been gathered yet. Run the daily fetch to populate this list.'
              : 'No jobs match those filters.'}
          </p>
        </Card>
      ) : (
        <>
          <div className="flex items-center justify-between text-xs text-slate-500 dark:text-slate-400">
            <span>
              {total.toLocaleString()} {total === 1 ? 'job' : 'jobs'}
              {isFetching ? ' · updating…' : ''}
            </span>
            <span>Page {page} of {lastPage}</span>
          </div>

          <ul className="space-y-3">
            {jobs.map((job) => (
              <JobCard
                key={job.id}
                job={job}
                onOpen={(j) => setOpenJobId(j.id)}
                onDelete={setPendingDelete}
                onTailor={tailor}
              />
            ))}
          </ul>

          <div className="flex items-center justify-center gap-3">
            <Button
              variant="secondary"
              size="sm"
              disabled={page <= 1 || isFetching}
              onClick={() => setPage((p) => p - 1)}
            >
              ← Previous
            </Button>
            <Button
              variant="secondary"
              size="sm"
              disabled={page >= lastPage || isFetching}
              onClick={() => setPage((p) => p + 1)}
            >
              Next →
            </Button>
          </div>
        </>
      )}

      <JobDetailModal
        jobId={openJobId}
        open={Boolean(openJobId)}
        onClose={() => setOpenJobId(null)}
      />

      <ConfirmDialog
        open={Boolean(pendingDelete)}
        onClose={() => setPendingDelete(null)}
        loading={remove.isPending}
        title="Remove this job?"
        description={
          `"${pendingDelete?.title}" will be removed from your list. This only affects your copy — ` +
          'if the employer still lists it, the next daily gather will bring it back.'
        }
        confirmLabel="Remove"
        onConfirm={() =>
          remove.mutate(pendingDelete.id, { onSuccess: () => setPendingDelete(null) })
        }
      />
    </div>
  );
}
