import { Badge, Button, Modal, Spinner } from '@/components/ui';

import { useJob } from '../api/jobsQueries';

/* The full listing. The description is only fetched here, never in the list —
   several thousand characters times a page of results would dominate the
   payload for text nobody reads until they open a card. */
export function JobDetailModal({ jobId, open, onClose }) {
  const { data: job, isLoading, isError } = useJob(open ? jobId : null);

  return (
    <Modal
      open={open}
      onClose={onClose}
      title={job?.title || 'Job'}
      description={job ? `${job.company_name}${job.location_raw ? ` · ${job.location_raw}` : ''}` : undefined}
      size="lg"
      footer={
        <>
          <Button variant="ghost" onClick={onClose}>Close</Button>
          {job ? (
            <a href={job.apply_url} target="_blank" rel="noopener noreferrer">
              <Button>Apply on {job.source_label}</Button>
            </a>
          ) : null}
        </>
      }
    >
      {isLoading ? <Spinner className="py-10" /> : null}
      {isError ? (
        <p className="text-sm text-red-600 dark:text-red-400">
          That job could not be loaded. It may have been removed.
        </p>
      ) : null}

      {job ? (
        <div className="space-y-4">
          <div className="flex flex-wrap gap-2 text-xs">
            <Badge variant="brand">{job.source_label}</Badge>
            {job.remote_type ? <Badge>{job.remote_type}</Badge> : null}
            {job.employment_type ? <Badge>{job.employment_type}</Badge> : null}
            {job.salary_text ? <Badge variant="success">{job.salary_text}</Badge> : null}
          </div>

          {/* Both dates are shown, and they mean different things: when the
              employer says it was posted, and when we last saw it in their
              feed. The second is how we know it is still open. */}
          <dl className="grid grid-cols-2 gap-3 rounded-lg border border-slate-200 p-3 text-xs dark:border-slate-800">
            <div>
              <dt className="text-slate-500 dark:text-slate-400">Posted by employer</dt>
              <dd className="mt-0.5 font-medium text-slate-800 dark:text-slate-100">
                {job.posted_at ? new Date(job.posted_at).toLocaleDateString() : 'Not stated'}
                {job.is_long_running ? ' — long-running listing' : ''}
              </dd>
            </div>
            <div>
              <dt className="text-slate-500 dark:text-slate-400">Last seen in their feed</dt>
              <dd className="mt-0.5 font-medium text-slate-800 dark:text-slate-100">
                {new Date(job.last_seen_at).toLocaleDateString()}
              </dd>
            </div>
          </dl>

          <div>
            <h3 className="text-sm font-semibold text-slate-900 dark:text-slate-100">Description</h3>
            <pre className="mt-2 max-h-[45vh] overflow-y-auto whitespace-pre-wrap font-sans text-sm leading-relaxed text-slate-700 dark:text-slate-300">
              {job.description || 'No description was published with this listing.'}
            </pre>
          </div>
        </div>
      ) : null}
    </Modal>
  );
}
