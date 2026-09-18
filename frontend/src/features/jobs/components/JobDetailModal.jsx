import { Badge, Button, Modal, SkeletonText } from '@/components/ui';

import { useJob } from '../api/jobsQueries';

/*
 * The full listing.
 *
 * The description is only fetched here, never in the list — several thousand
 * characters times a page of results would dominate the payload for text
 * nobody reads until they open a row.
 *
 * The row that was clicked is passed in whole, so the title, company and badges
 * paint immediately and only the description arrives late.
 */
export function JobDetailModal({ job: summary, open, onClose }) {
  const { data: full, isLoading, isError } = useJob(open ? summary?.id : null);
  const job = full ?? summary;

  if (!job) return null;

  return (
    <Modal
      open={open}
      onClose={onClose}
      title={job.title}
      description={`${job.company_name}${job.location_raw ? ` · ${job.location_raw}` : ''}`}
      size="lg"
      footer={
        <>
          <Button variant="ghost" onClick={onClose}>
            Close
          </Button>
          <a href={job.apply_url} target="_blank" rel="noopener noreferrer">
            <Button iconAfter="external">Apply on {job.source_label}</Button>
          </a>
        </>
      }
    >
      <div className="flex flex-col gap-3.5">
        <div className="flex flex-wrap gap-1.5">
          <Badge variant="brand">{job.source_label}</Badge>
          {job.remote_type ? <Badge>{job.remote_type}</Badge> : null}
          {job.employment_type ? <Badge>{job.employment_type}</Badge> : null}
          {job.department ? <Badge>{job.department}</Badge> : null}
          {job.salary_text ? <Badge variant="success">{job.salary_text}</Badge> : null}
        </div>

        {/* Both dates are shown and they mean different things: when the
            employer says it was posted, and when we last saw it in their feed.
            The second is how we know it is still open. */}
        <dl className="grid grid-cols-2 gap-3 rounded-control border border-line bg-surface-2 px-3 py-2.5 text-[11px]">
          <div>
            <dt className="text-subtle">Posted by employer</dt>
            <dd className="mt-0.5 font-medium text-ink">
              {job.posted_at ? new Date(job.posted_at).toLocaleDateString() : 'Not stated'}
              {job.is_long_running ? ' — long-running listing' : ''}
            </dd>
          </div>
          <div>
            <dt className="text-subtle">Last seen in their feed</dt>
            <dd className="mt-0.5 font-medium text-ink">
              {job.last_seen_at ? new Date(job.last_seen_at).toLocaleDateString() : '—'}
            </dd>
          </div>
        </dl>

        <div>
          <h3 className="text-xs font-semibold text-ink">Description</h3>
          {isError ? (
            <p className="mt-2 text-xs text-bad">
              The full description could not be loaded. It may have been removed.
            </p>
          ) : isLoading || !full ? (
            <SkeletonText lines={8} className="mt-3" />
          ) : (
            <pre className="mt-2 max-h-[45vh] overflow-y-auto font-sans text-xs leading-6 whitespace-pre-wrap text-muted">
              {full.description || 'No description was published with this listing.'}
            </pre>
          )}
        </div>
      </div>
    </Modal>
  );
}
