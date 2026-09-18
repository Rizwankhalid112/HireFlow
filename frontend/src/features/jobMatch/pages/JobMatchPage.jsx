import { useState } from 'react';
import { useLocation } from 'react-router-dom';

import { Alert, Button, Card, Icon, Panel, Select, Skeleton, Textarea } from '@/components/ui';
import { useCvSources, useJobMatches, useRunJobMatch } from '@/features/cvBuilder/api/cvQueries';

import { MatchResult } from '../components/MatchResult';

/*
 * Module 1 — paste a job, pick a CV, get keywords and a cover letter.
 *
 * One screen rather than a wizard: there are only two inputs, and a two-step
 * flow for two fields is ceremony. The result sits beside the form (below it on
 * narrow screens) so re-running against an edited posting stays one click.
 *
 * The call behind this is the most expensive in the product, so the remaining
 * allowance is always visible and the button is genuinely disabled while it
 * runs — a double submit costs real money twice.
 */

const MIN_JD_CHARS = 120;

export default function JobMatchPage() {
  /* A job handed over from the jobs list, so the user does not copy and paste a
     description they were already looking at. Read once as the initial value
     rather than synced, so their edits are never overwritten by a re-render. */
  const handedOver = useLocation().state ?? null;

  const [jdText, setJdText] = useState(handedOver?.jdText ?? '');
  const [sourceKey, setSourceKey] = useState('profile');
  const [result, setResult] = useState(null);

  const { data: sourceData, isLoading: sourcesLoading } = useCvSources();
  const { data: history } = useJobMatches();
  const run = useRunJobMatch();

  const sources = sourceData?.sources ?? [];
  const limit = sourceData?.matches?.limit ?? 0;
  const remaining = Math.max(limit - (sourceData?.matches?.used ?? 0), 0);

  const length = jdText.trim().length;
  const tooShort = length > 0 && length < MIN_JD_CHARS;
  const canRun = length >= MIN_JD_CHARS && !run.isPending && remaining > 0;

  const submit = () => {
    if (!canRun) return;
    const [type, id] = sourceKey.split(':');
    run.mutate(
      { jd_text: jdText.trim(), source_type: type, ...(type === 'upload' ? { upload_id: id } : {}) },
      { onSuccess: setResult },
    );
  };

  const status = run.error?.response?.status;
  const detail = run.error?.response?.data?.detail;

  return (
    <div className="mx-auto flex max-w-6xl flex-col gap-4">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold tracking-tight">Match your CV to a job</h1>
          <p className="mt-0.5 text-xs text-muted">
            See which of the posting&apos;s keywords your CV already covers, which it only words
            differently, and which it genuinely does not claim.
          </p>
        </div>
        <span className="tabular text-[11px] text-subtle">
          {remaining} of {limit} matches left this month
        </span>
      </div>

      {handedOver?.jobTitle ? (
        <Alert variant="info">
          Using <strong className="font-semibold">{handedOver.jobTitle}</strong>
          {handedOver.company ? ` at ${handedOver.company}` : ''} from your jobs list. Edit the
          description below if you want to.
        </Alert>
      ) : null}

      <div className="grid gap-3 xl:grid-cols-[400px_minmax(0,1fr)]">
        <Card className="flex flex-col gap-3.5">
          <div className="flex flex-col gap-1.5">
            <label htmlFor="cv-source" className="text-xs font-medium text-ink">
              Which CV?
            </label>
            {sourcesLoading ? (
              <Skeleton h={32} className="rounded-control" />
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
              <p className="text-[11px] text-subtle">
                Upload a CV in the builder and it will appear here too.
              </p>
            ) : null}
          </div>

          <div className="flex flex-col gap-1.5">
            <label htmlFor="jd" className="text-xs font-medium text-ink">
              Job description
            </label>
            <Textarea
              id="jd"
              rows={16}
              value={jdText}
              onChange={(event) => setJdText(event.target.value)}
              placeholder="Paste the whole posting here — including the requirements section, which is where most of the keywords live."
            />
            <div className="flex flex-wrap items-center justify-between gap-2 text-[11px]">
              <span className={`tabular ${tooShort ? 'text-warn' : 'text-subtle'}`}>
                {tooShort ? `${MIN_JD_CHARS - length} more characters` : `${length} characters`}
              </span>
              <span className="text-subtle">Requirements section included</span>
            </div>
          </div>

          {status === 400 && detail ? <Alert variant="warning">{detail}</Alert> : null}
          {status === 429 ? (
            <Alert variant="warning">
              {detail || 'You have used all your matches for this month.'}
            </Alert>
          ) : null}
          {status === 503 ? (
            <Alert variant="error">{detail || 'The job matcher is unavailable right now.'}</Alert>
          ) : null}

          <div className="flex flex-wrap items-center gap-2.5">
            <Button icon="match" onClick={submit} disabled={!canRun} loading={run.isPending}>
              {run.isPending ? 'Reading the posting…' : 'Match my CV'}
            </Button>
            {run.isPending ? (
              <span className="text-[11px] text-subtle">
                A few seconds — it reads both documents in full.
              </span>
            ) : null}
          </div>
        </Card>

        <div className="min-w-0">
          {result ? (
            <MatchResult match={result} />
          ) : run.isPending ? (
            <Card className="flex h-full min-h-60 flex-col items-center justify-center gap-2.5 text-center">
              <Icon name="sparkle" size={22} className="animate-pulse text-accent" />
              <p className="text-[13px] font-medium">Reading your CV against the posting</p>
              <p className="max-w-xs text-[11px] leading-5 text-muted">
                Both documents go in whole — a truncated CV would make real skills look missing.
              </p>
            </Card>
          ) : history?.length ? (
            <Panel title="Earlier matches" bodyClass="px-4 py-1">
              <ul className="divide-y divide-line">
                {history.slice(0, 8).map((item) => (
                  <li key={item.id} className="flex items-center justify-between gap-3 py-2.5">
                    <div className="min-w-0">
                      <p className="truncate text-[13px] font-medium">
                        {item.job_title || 'Untitled role'}
                        {item.company ? ` — ${item.company}` : ''}
                      </p>
                      <p className="text-[11px] text-subtle">
                        {new Date(item.created_at).toLocaleDateString()} · {item.source_label}
                      </p>
                    </div>
                    <span
                      className={`tabular shrink-0 text-[13px] font-semibold ${
                        item.match_score >= 75 ? 'text-ok' : item.match_score >= 50 ? 'text-warn' : 'text-bad'
                      }`}
                    >
                      {item.match_score}%
                    </span>
                  </li>
                ))}
              </ul>
            </Panel>
          ) : (
            <Card className="flex h-full min-h-60 flex-col items-center justify-center gap-2.5 text-center">
              <Icon name="match" size={22} className="text-subtle" />
              <p className="text-[13px] font-medium">Your analysis will appear here</p>
              <p className="max-w-xs text-[11px] leading-5 text-muted">
                Three keyword lists — what your CV already proves, what it only words differently,
                and what it genuinely lacks — plus a cover letter drafted from the first two.
              </p>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}
