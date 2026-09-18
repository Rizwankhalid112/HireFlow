import { memo } from 'react';

import { Button, Icon, IconButton } from '@/components/ui';

/*
 * One job, as a dense row.
 *
 * Memoised on purpose. A page holds 25 of these while the parent also owns the
 * open-modal id, the pending-delete row and every filter — so without `memo`,
 * opening one dialog re-renders all 25. The handlers below must therefore stay
 * referentially stable in the parent (see JobsPage's useCallback).
 */

/* Which board it came from. An identity scale, not a status one: it sits
   outside the semantic palette deliberately, because after a few hundred rows
   the source becomes something you scan for rather than read. */
const SOURCE_STYLE = {
  greenhouse: 'border-emerald-200 bg-emerald-50 text-emerald-700 dark:border-emerald-900 dark:bg-emerald-950 dark:text-emerald-300',
  ashby: 'border-violet-200 bg-violet-50 text-violet-700 dark:border-violet-900 dark:bg-violet-950 dark:text-violet-300',
  lever: 'border-sky-200 bg-sky-50 text-sky-700 dark:border-sky-900 dark:bg-sky-950 dark:text-sky-300',
  workable: 'border-amber-200 bg-amber-50 text-amber-700 dark:border-amber-900 dark:bg-amber-950 dark:text-amber-300',
};

const REMOTE_LABEL = { remote: 'Remote', hybrid: 'Hybrid', onsite: 'On-site' };

/*
 * How old, in words.
 *
 * Past a year we say "long-running listing" instead of a number. Some employers
 * keep requisitions open for years — one live listing in our own data is
 * published as posted in 2009 — and "posted 6,123 days ago" is noise rather
 * than information.
 */
function postedLabel(job) {
  if (job.is_long_running) return 'Long-running listing';

  const days = job.age_days;
  if (days === null || days === undefined) return 'Date not given';
  if (days <= 0) return 'Posted today';
  if (days === 1) return 'Posted yesterday';
  if (days < 30) return `Posted ${days} days ago`;
  if (days < 60) return 'Posted about a month ago';
  return `Posted ${Math.round(days / 30)} months ago`;
}

function freshness(job) {
  if (job.is_long_running) return 'text-warn';
  if (job.age_days !== null && job.age_days <= 14) return 'text-ok';
  return 'text-subtle';
}

export const JobCard = memo(function JobCard({ job, onOpen, onDelete, onTailor, tailoring }) {
  const isFresh = !job.is_long_running && job.age_days !== null && job.age_days <= 14;
  /* The location string and the arrangement badge say the same thing when a
     job is listed as "Remote" in both — show it once. */
  const showLocation =
    job.location_raw && job.location_raw.toLowerCase() !== (job.remote_type || '').toLowerCase();

  return (
    <li className="group rounded-card border border-line bg-surface px-4 py-3 transition-colors hover:border-line-strong hover:bg-surface-2">
      {/* Stacks below sm: side by side, the action group refuses to shrink and
          crushes the title into a one-word-per-line column on a phone. */}
      <div className="flex flex-col gap-2.5 sm:flex-row sm:items-start sm:justify-between sm:gap-4">
        <div className="flex min-w-0 flex-1 flex-col gap-1">
          <div className="flex flex-wrap items-center gap-2">
            <button
              type="button"
              onClick={() => onOpen(job)}
              className="text-left text-sm font-semibold tracking-tight hover:text-accent"
            >
              {job.title}
            </button>
            <span
              className={`rounded-full border px-2 py-px text-[11px] font-medium ${
                SOURCE_STYLE[job.source] ?? SOURCE_STYLE.greenhouse
              }`}
              title={`Sourced from ${job.source_label}`}
            >
              {job.source_label}
            </span>
          </div>

          <p className="flex flex-wrap items-center gap-x-2 gap-y-1 text-xs text-muted">
            <span className="font-medium text-ink">{job.company_name}</span>
            {showLocation ? (
              <>
                <span className="text-line-strong">·</span>
                {job.location_raw}
              </>
            ) : null}
            {job.remote_type ? (
              <span className="rounded-full border border-accent-line bg-accent-soft px-1.5 py-px text-[11px] font-medium text-accent">
                {REMOTE_LABEL[job.remote_type]}
              </span>
            ) : null}
            <span className="text-line-strong">·</span>
            <span className={`inline-flex items-center gap-1 ${freshness(job)}`}>
              {isFresh ? <span className="size-1.5 rounded-full bg-ok-solid" /> : null}
              {job.is_long_running ? <Icon name="clock" size={11} /> : null}
              {postedLabel(job)}
            </span>
            {/* Shown when present, never a filter: it is a per-company opt-in
                and absent from most listings. */}
            {job.salary_text ? (
              <>
                <span className="text-line-strong">·</span>
                <span className="tabular text-[11px] text-ok">{job.salary_text}</span>
              </>
            ) : null}
          </p>

          {/* The user's own skills this job names. Shown as the skills
              themselves rather than a score, because "Python, Django" is
              something they can check and a percentage is not. */}
          {job.matched_skills?.length ? (
            <p className="text-[11px] text-ok">
              Matches your {job.matched_skills.slice(0, 6).join(', ')}
              {job.matched_skills.length > 6 ? ` and ${job.matched_skills.length - 6} more` : ''}
            </p>
          ) : null}
        </div>

        <div className="flex items-center gap-1.5 sm:shrink-0">
          <Button variant="secondary" size="sm" onClick={() => onOpen(job)}>
            View
          </Button>
          {/* The join between the two modules: hands this description straight
              to the match page instead of making the user copy and paste it. */}
          <Button
            variant="secondary"
            size="sm"
            loading={tailoring}
            onClick={() => onTailor(job)}
          >
            Tailor CV
          </Button>
          <a href={job.apply_url} target="_blank" rel="noopener noreferrer">
            <Button size="sm" iconAfter="external">
              Apply
            </Button>
          </a>
          {/* Revealed on hover on a pointer device; always visible on touch,
              where there is no hover and it would otherwise be unreachable. */}
          <IconButton
            icon="trash"
            label={`Remove ${job.title}`}
            size="sm"
            onClick={() => onDelete(job)}
            className="ml-auto transition-opacity sm:ml-0 sm:opacity-0 sm:group-hover:opacity-100 sm:focus-visible:opacity-100"
          />
        </div>
      </div>
    </li>
  );
});
