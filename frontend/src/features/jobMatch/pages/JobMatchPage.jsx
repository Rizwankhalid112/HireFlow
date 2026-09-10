import { useState } from 'react';

import { Alert, Button, Card, Select, Spinner, Textarea } from '@/components/ui';

import {
  useCvSources,
  useJobMatches,
  useRunJobMatch,
} from '@/features/cvBuilder/api/cvQueries';
import { MatchResult } from '../components/MatchResult';

/*
 * Module 1 — paste a job, pick a CV, get keywords and a cover letter.
 *
 * One screen rather than a wizard: there are only two inputs, and a two-step
 * flow for two fields is ceremony. The result appears underneath rather than
 * replacing the form, so re-running against an edited posting is one click.
 *
 * The call behind this is the most expensive in the product, so the remaining
 * allowance is always visible and the button is genuinely disabled while it
 * runs — a double submit here costs real money twice.
 */

const MIN_JD_CHARS = 120;

export default function JobMatchPage() {
  const [jdText, setJdText] = useState('');
  const [sourceKey, setSourceKey] = useState('profile');
  const [result, setResult] = useState(null);

  const { data: sourceData, isLoading: sourcesLoading } = useCvSources();
  const { data: history } = useJobMatches();
  const run = useRunJobMatch();

  const sources = sourceData?.sources ?? [];
  const used = sourceData?.matches?.used ?? 0;
  const limit = sourceData?.matches?.limit ?? 0;
  const remaining = Math.max(limit - used, 0);

  const tooShort = jdText.trim().length > 0 && jdText.trim().length < MIN_JD_CHARS;
  const canRun = jdText.trim().length >= MIN_JD_CHARS && !run.isPending && remaining > 0;

  const submit = () => {
    if (!canRun) {
      return;
    }
    const [type, id] = sourceKey.split(':');
    run.mutate(
      {
        jd_text: jdText.trim(),
        source_type: type,
        ...(type === 'upload' ? { upload_id: id } : {}),
      },
      { onSuccess: setResult },
    );
  };

  const status = run.error?.response?.status;
  const errorDetail = run.error?.response?.data?.detail;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-slate-900 dark:text-slate-100">
          Match your CV to a job
        </h1>
        <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">
          Paste the job description. We&apos;ll show which of its keywords your CV already
          covers, which are just worded differently, and write you a cover letter.
        </p>
      </div>

      <Card>
        <div className="space-y-4">
          <div>
            <label
              htmlFor="cv-source"
              className="mb-1.5 block text-sm font-medium text-slate-700 dark:text-slate-200"
            >
              Which CV?
            </label>
            {sourcesLoading ? (
              <Spinner />
            ) : (
              <Select
                id="cv-source"
                value={sourceKey}
                onChange={(event) => setSourceKey(event.target.value)}
              >
                {sources.map((source) => (
                  <option
                    key={`${source.type}:${source.id ?? ''}`}
                    value={`${source.type}:${source.id ?? ''}`}
                  >
                    {source.label} — {source.detail}
                  </option>
                ))}
              </Select>
            )}
            {sources.length === 1 ? (
              <p className="mt-1.5 text-xs text-slate-500 dark:text-slate-400">
                Upload a CV in the builder and it will appear here too.
              </p>
            ) : null}
          </div>

          <div>
            <label
              htmlFor="jd"
              className="mb-1.5 block text-sm font-medium text-slate-700 dark:text-slate-200"
            >
              Job description
            </label>
            <Textarea
              id="jd"
              rows={12}
              value={jdText}
              onChange={(event) => setJdText(event.target.value)}
              placeholder="Paste the whole posting here — including the requirements section, which is where most of the keywords live."
            />
            <div className="mt-1.5 flex flex-wrap items-center justify-between gap-2 text-xs">
              <span className={tooShort ? 'text-amber-600 dark:text-amber-400' : 'text-slate-500 dark:text-slate-400'}>
                {tooShort
                  ? `A bit more, please — ${MIN_JD_CHARS - jdText.trim().length} more characters.`
                  : `${jdText.trim().length} characters`}
              </span>
              <span className="text-slate-500 dark:text-slate-400">
                {remaining} of {limit} matches left this month
              </span>
            </div>
          </div>

          {status === 400 && errorDetail ? (
            <Alert variant="warning">{errorDetail}</Alert>
          ) : null}
          {status === 429 ? (
            <Alert variant="warning">
              {errorDetail || 'You have used all your matches for this month.'}
            </Alert>
          ) : null}
          {status === 503 ? (
            <Alert variant="error">
              {errorDetail || 'The job matcher is unavailable right now.'}
            </Alert>
          ) : null}

          <div className="flex items-center gap-3">
            <Button onClick={submit} disabled={!canRun} loading={run.isPending}>
              {run.isPending ? 'Reading the posting…' : 'Match my CV'}
            </Button>
            {run.isPending ? (
              <span className="text-xs text-slate-500 dark:text-slate-400">
                This takes a few seconds — it reads both documents in full.
              </span>
            ) : null}
          </div>
        </div>
      </Card>

      <MatchResult match={result} />

      {!result && history?.length ? (
        <Card>
          <h2 className="text-sm font-semibold text-slate-900 dark:text-slate-100">
            Earlier matches
          </h2>
          <ul className="mt-3 divide-y divide-slate-200 dark:divide-slate-800">
            {history.slice(0, 8).map((item) => (
              <li key={item.id} className="flex items-center justify-between gap-3 py-2">
                <div className="min-w-0">
                  <p className="truncate text-sm text-slate-800 dark:text-slate-100">
                    {item.job_title || 'Untitled role'}
                    {item.company ? ` — ${item.company}` : ''}
                  </p>
                  <p className="text-xs text-slate-500 dark:text-slate-400">
                    {new Date(item.created_at).toLocaleDateString()} · {item.source_label}
                  </p>
                </div>
                <span className="shrink-0 text-sm font-medium tabular-nums text-slate-600 dark:text-slate-300">
                  {item.match_score}%
                </span>
              </li>
            ))}
          </ul>
        </Card>
      ) : null}
    </div>
  );
}
