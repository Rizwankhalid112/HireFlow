import { useCallback, useState } from 'react';
import { useNavigate } from 'react-router-dom';

import {
  Alert,
  Button,
  Card,
  ConfirmDialog,
  Icon,
  Input,
  Select,
  SkeletonRows,
} from '@/components/ui';
import { useSuggestionCredits } from '@/features/cvBuilder/api/cvQueries';
import { useDebouncedValue } from '@/features/cvBuilder/hooks/useDebouncedValue';

import * as jobsApi from '../api/jobsApi';
import { useDeleteJob, useJobStats, useJobs } from '../api/jobsQueries';
import { JobCard } from '../components/JobCard';
import { JobDetailModal } from '../components/JobDetailModal';

/*
 * The harvested jobs.
 *
 * Everything here is paginated and server-filtered. Nothing loads the whole
 * table and no filter runs client-side — the table is built for millions of
 * rows, so a page that fetched everything and filtered in the browser would
 * work fine today and fall over in a month.
 */

const PAGE_SIZE = 25;

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
  const [filters, setFilters] = useState({ search: '', location: '', source: '', remoteType: '' });
  const [useCv, setUseCv] = useState(false);
  const [page, setPage] = useState(1);
  const [openJob, setOpenJob] = useState(null);
  const [pendingDelete, setPendingDelete] = useState(null);
  const [tailoringId, setTailoringId] = useState(null);
  const navigate = useNavigate();

  // Debounced so typing does not fire a query per keystroke against a large table.
  const search = useDebouncedValue(filters.search, 400);
  const location = useDebouncedValue(filters.location, 400);

  const params = {
    page,
    ...(useCv ? { match: 'cv' } : {}),
    ...(search ? { search } : {}),
    ...(location ? { location } : {}),
    ...(filters.source ? { source: filters.source } : {}),
    ...(filters.remoteType ? { remote_type: filters.remoteType } : {}),
  };

  const { data, error, isLoading, isFetching, isError } = useJobs(params);
  const { data: stats } = useJobStats();
  /* "Tailor CV" hands the posting to Job Match, which needs a model key. With
     none configured that button leads to a 503, so it is not offered. */
  const { data: aiCredits } = useSuggestionCredits();
  const canTailor = aiCredits?.enabled !== false;
  const remove = useDeleteJob();

  /* A filter change invalidates the current page number. */
  const setFilter = useCallback((key) => (event) => {
    const value = event.target.type === 'checkbox' ? event.target.checked : event.target.value;
    setPage(1);
    if (key === 'useCv') setUseCv(value);
    else setFilters((prev) => ({ ...prev, [key]: value }));
  }, []);

  /* These three are passed to 25 memoised rows — they must not be re-created
     on every render, or the memo buys nothing. */
  const onOpen = useCallback((job) => setOpenJob(job), []);
  const onDelete = useCallback((job) => setPendingDelete(job), []);
  const onTailor = useCallback(
    async (job) => {
      setTailoringId(job.id);
      try {
        /* The description is not in the list payload — several thousand
           characters per row — so it is fetched for the one job being tailored
           and handed to the match page through router state. */
        const { data: full } = await jobsApi.getJob(job.id);
        navigate('/job-match', {
          state: { jdText: full.description, jobTitle: full.title, company: full.company_name },
        });
      } finally {
        setTailoringId(null);
      }
    },
    [navigate],
  );

  const jobs = data?.results ?? [];
  const total = data?.count ?? 0;
  const lastPage = Math.max(1, Math.ceil(total / PAGE_SIZE));
  const filtered = Boolean(search || location || filters.source || filters.remoteType);

  return (
    <div className="mx-auto flex max-w-6xl flex-col gap-4">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold tracking-tight">Jobs</h1>
          <p className="mt-0.5 text-xs text-muted">
            Gathered nightly from company boards. You apply on the employer&apos;s own site.
          </p>
        </div>
        {stats ? (
          <p className="tabular text-[11px] text-subtle">
            {stats.total_jobs.toLocaleString()} indexed ·{' '}
            {stats.by_source.map((s) => `${s.count} ${s.source}`).join(' · ')}
          </p>
        ) : null}
      </div>

      <Card padded={false}>
        <div className="grid gap-2 p-3 sm:grid-cols-2 lg:grid-cols-4">
          <Input
            placeholder="Search title, company or description"
            value={filters.search}
            onChange={setFilter('search')}
            aria-label="Search jobs"
          />
          <Input
            placeholder="Location"
            value={filters.location}
            onChange={setFilter('location')}
            aria-label="Filter by location"
          />
          <Select
            value={filters.source}
            onChange={setFilter('source')}
            aria-label="Filter by source"
            options={SOURCES}
          />
          <Select
            value={filters.remoteType}
            onChange={setFilter('remoteType')}
            aria-label="Filter by working arrangement"
            options={REMOTE}
          />
        </div>

        <div className="flex flex-wrap items-center gap-x-3 gap-y-2 rounded-b-card border-t border-line bg-surface-2 px-3 py-2.5">
          <label className="flex cursor-pointer items-center gap-2 text-xs font-semibold">
            <input
              type="checkbox"
              checked={useCv}
              onChange={setFilter('useCv')}
              className="size-3.5 cursor-pointer rounded border-line-strong accent-[var(--accent)]"
            />
            Rank by my CV
          </label>

          <span className="h-4 w-px bg-line" />

          {useCv && data?.matched_against?.length ? (
            <p className="flex flex-wrap items-center gap-1.5 text-[11px] text-subtle">
              Matching on
              {data.matched_against.slice(0, 6).map((skill) => (
                <span
                  key={skill}
                  className="rounded-full border border-ok-line bg-ok-soft px-1.5 py-px font-medium text-ok"
                >
                  {skill}
                </span>
              ))}
              {data.matched_against.length > 6 ? (
                <span>+{data.matched_against.length - 6} more</span>
              ) : null}
            </p>
          ) : (
            <p className="text-[11px] text-subtle">
              Orders by overlap with your CV&apos;s skills instead of by date.
            </p>
          )}

          {filters.remoteType ? (
            /* Honesty about a real gap: Greenhouse does not publish this field,
               so for those listings it is inferred from wording and some are
               simply unknown. Silently returning fewer rows looks like a bug. */
            <p className="flex w-full items-center gap-1.5 text-[11px] text-subtle">
              <Icon name="info" size={12} />
              Some boards do not state the working arrangement — listings without one are hidden by
              this filter.
            </p>
          ) : null}
        </div>
      </Card>

      {isError ? (
        <Alert variant={useCv ? 'warning' : 'error'}>
          {/* Usually "add some skills first", which the user can act on. */}
          {error?.response?.data?.detail || 'Jobs could not be loaded.'}
        </Alert>
      ) : null}

      {isLoading ? (
        <SkeletonRows rows={6} />
      ) : jobs.length === 0 && !isError ? (
        <Card>
          <p className="py-10 text-center text-xs text-muted">
            {filtered
              ? 'No jobs match those filters.'
              : 'No jobs have been gathered yet. Run the nightly fetch to populate this list.'}
          </p>
        </Card>
      ) : jobs.length ? (
        <>
          <div className="flex items-center justify-between text-[11px] text-subtle">
            <span className="tabular">
              {total.toLocaleString()} {total === 1 ? 'job' : 'jobs'}
              {useCv ? ' · ranked by skill overlap' : ''}
              {isFetching ? ' · updating…' : ''}
            </span>
            <span className="tabular">
              Page {page} of {lastPage}
            </span>
          </div>

          <ul className="flex flex-col gap-2">
            {jobs.map((job) => (
              <JobCard
                key={job.id}
                job={job}
                onOpen={onOpen}
                onDelete={onDelete}
                onTailor={canTailor ? onTailor : undefined}
                tailoring={tailoringId === job.id}
              />
            ))}
          </ul>

          <div className="flex items-center justify-center gap-2">
            <Button
              variant="secondary"
              size="sm"
              icon="chevronLeft"
              disabled={page <= 1 || isFetching}
              onClick={() => setPage((p) => p - 1)}
            >
              Previous
            </Button>
            <Button
              variant="secondary"
              size="sm"
              iconAfter="chevronRight"
              disabled={page >= lastPage || isFetching}
              onClick={() => setPage((p) => p + 1)}
            >
              Next
            </Button>
          </div>
        </>
      ) : null}

      <JobDetailModal job={openJob} open={Boolean(openJob)} onClose={() => setOpenJob(null)} />

      <ConfirmDialog
        open={Boolean(pendingDelete)}
        onClose={() => setPendingDelete(null)}
        loading={remove.isPending}
        title="Remove this job?"
        description={
          `"${pendingDelete?.title}" will be removed from the listings. ` +
          'If the employer still lists it, the next nightly gather brings it back.'
        }
        confirmLabel="Remove"
        onConfirm={() =>
          remove.mutate(pendingDelete.id, { onSuccess: () => setPendingDelete(null) })
        }
      />
    </div>
  );
}
