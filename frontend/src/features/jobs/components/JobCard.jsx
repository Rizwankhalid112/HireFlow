import { Badge, Button } from '@/components/ui';

/*
 * One job.
 *
 * The source and the posting date are given real prominence rather than being
 * footnotes: where a listing came from and how old it is are the two things a
 * candidate needs to judge it, and both were the hardest data to get right.
 */

/* Which board it came from. Colour-coded because after a few hundred cards the
   source becomes something you scan for rather than read. */
const SOURCE_STYLE = {
  greenhouse: 'border-emerald-200 bg-emerald-50 text-emerald-800 dark:border-emerald-900 dark:bg-emerald-950 dark:text-emerald-200',
  ashby: 'border-violet-200 bg-violet-50 text-violet-800 dark:border-violet-900 dark:bg-violet-950 dark:text-violet-200',
  lever: 'border-sky-200 bg-sky-50 text-sky-800 dark:border-sky-900 dark:bg-sky-950 dark:text-sky-200',
  workable: 'border-amber-200 bg-amber-50 text-amber-800 dark:border-amber-900 dark:bg-amber-950 dark:text-amber-200',
};

const REMOTE_LABEL = { remote: 'Remote', hybrid: 'Hybrid', onsite: 'On-site' };

/*
 * How old, in words.
 *
 * Past a year we say "long-running listing" instead of a number. Some employers
 * keep requisitions open for years — one live listing in our own data is
 * published as posted in 2009 — and "posted 6,123 days ago" is noise rather
 * than information. It is still worth telling the candidate, because a role
 * open that long is worth knowing about before spending an evening on it.
 */
function postedLabel(job) {
  if (job.is_long_running) {
    return 'Long-running listing';
  }
  const days = job.age_days;
  if (days === null || days === undefined) {
    return 'Date not given';
  }
  if (days <= 0) return 'Posted today';
  if (days === 1) return 'Posted yesterday';
  if (days < 30) return `Posted ${days} days ago`;
  if (days < 60) return 'Posted about a month ago';
  return `Posted ${Math.round(days / 30)} months ago`;
}

function freshnessTone(job) {
  if (job.is_long_running) return 'text-amber-700 dark:text-amber-300';
  if (job.age_days !== null && job.age_days <= 14) return 'text-emerald-700 dark:text-emerald-300';
  return 'text-slate-500 dark:text-slate-400';
}

export function JobCard({ job, onOpen, onDelete, onTailor }) {
  return (
    <li className="rounded-xl border border-slate-200 bg-white p-4 transition-colors hover:border-slate-300 dark:border-slate-800 dark:bg-slate-900 dark:hover:border-slate-700">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <button
            type="button"
            onClick={() => onOpen(job)}
            className="text-left text-base font-semibold text-slate-900 hover:underline dark:text-slate-100"
          >
            {job.title}
          </button>
          <p className="mt-0.5 text-sm text-slate-600 dark:text-slate-400">
            {job.company_name}
            {job.location_raw ? ` · ${job.location_raw}` : ''}
          </p>
        </div>

        <span
          className={`shrink-0 rounded-full border px-2.5 py-0.5 text-xs font-medium ${
            SOURCE_STYLE[job.source] || SOURCE_STYLE.greenhouse
          }`}
          title={`Sourced from ${job.source_label}`}
        >
          {job.source_label}
        </span>
      </div>

      <div className="mt-3 flex flex-wrap items-center gap-2 text-xs">
        <span className={`font-medium ${freshnessTone(job)}`}>{postedLabel(job)}</span>
        {job.remote_type ? <Badge variant="brand">{REMOTE_LABEL[job.remote_type]}</Badge> : null}
        {job.employment_type ? <Badge>{job.employment_type}</Badge> : null}
        {job.department ? (
          <span className="text-slate-500 dark:text-slate-400">{job.department}</span>
        ) : null}
        {/* Shown when present, never used as a filter: it is a per-company
            opt-in and absent from most listings. */}
        {job.salary_text ? (
          <Badge variant="success">{job.salary_text}</Badge>
        ) : null}
      </div>

      {/* Which of the user's own skills this job mentions. Shown as the actual
          skill names rather than a score, because "matched Python, Django" is
          something they can check and a percentage is not. */}
      {job.matched_skills?.length ? (
        <p className="mt-2 text-xs text-emerald-700 dark:text-emerald-300">
          Matches your {job.matched_skills.slice(0, 6).join(', ')}
          {job.matched_skills.length > 6 ? ` and ${job.matched_skills.length - 6} more` : ''}
        </p>
      ) : null}

      <div className="mt-3 flex flex-wrap gap-2">
        <Button size="sm" variant="secondary" onClick={() => onOpen(job)}>
          View
        </Button>
        {/* The join between the two modules: hands this description straight to
            the match page instead of making the user copy and paste it. */}
        <Button size="sm" variant="secondary" onClick={() => onTailor(job)}>
          Tailor CV for this
        </Button>
        <a href={job.apply_url} target="_blank" rel="noopener noreferrer">
          <Button size="sm">Apply on {job.source_label}</Button>
        </a>
        <Button size="sm" variant="ghost" onClick={() => onDelete(job)}>
          Remove
        </Button>
      </div>
    </li>
  );
}
