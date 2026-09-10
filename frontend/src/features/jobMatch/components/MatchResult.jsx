import { useState } from 'react';
import { toast } from 'sonner';

import { Alert, Badge, Button, Card } from '@/components/ui';

/*
 * What came back from a match.
 *
 * The three keyword lists are rendered as three visually distinct things, not one
 * list with tags, because they mean completely different things to the user:
 * one is reassurance, one is a free win, and one is a question they have to
 * answer honestly. Flattening them is what would turn this into a tool that
 * quietly encourages lying on a CV.
 */

function scoreTone(score) {
  if (score >= 75) return 'text-emerald-600 dark:text-emerald-400';
  if (score >= 50) return 'text-amber-600 dark:text-amber-400';
  return 'text-red-600 dark:text-red-400';
}

function ScoreDial({ score }) {
  return (
    <div className="flex items-baseline gap-2">
      <span className={`text-4xl font-semibold tabular-nums ${scoreTone(score)}`}>{score}%</span>
      <span className="text-xs text-slate-500 dark:text-slate-400">keyword match</span>
    </div>
  );
}

function CopyButton({ text, label = 'Copy' }) {
  const [copied, setCopied] = useState(false);

  return (
    <Button
      size="sm"
      variant="secondary"
      onClick={async () => {
        try {
          await navigator.clipboard.writeText(text);
          setCopied(true);
          setTimeout(() => setCopied(false), 2000);
        } catch {
          toast.error('Could not copy — select the text and copy it manually.');
        }
      }}
    >
      {copied ? 'Copied' : label}
    </Button>
  );
}

export function MatchResult({ match }) {
  if (!match) {
    return null;
  }

  const { matched = [], reworded = [], missing = [] } = match;

  return (
    <div className="space-y-4">
      <Card>
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="min-w-0">
            <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-100">
              {match.job_title || 'This role'}
              {match.company ? (
                <span className="font-normal text-slate-500 dark:text-slate-400">
                  {' '}
                  at {match.company}
                </span>
              ) : null}
            </h2>
            <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">{match.summary}</p>
            <p className="mt-2 text-xs text-slate-500 dark:text-slate-400">
              Matched against {match.source_label}
            </p>
          </div>
          <ScoreDial score={match.match_score} />
        </div>

        {/* Said plainly, because every competitor implies otherwise. A keyword
            score is not a prediction, and pretending it is would be inventing a
            number about someone's livelihood. */}
        <p className="mt-4 border-t border-slate-200 pt-3 text-xs text-slate-500 dark:border-slate-800 dark:text-slate-400">
          This is how much of what the posting asks for appears in your CV — not a
          prediction of whether you&apos;ll be interviewed. Around 75–85% is a good
          target; pushing for 100% is wasted effort and can read as keyword stuffing.
        </p>
      </Card>

      {reworded.length ? (
        <Card>
          <h3 className="text-sm font-semibold text-slate-900 dark:text-slate-100">
            Worth rewording — you already have these
          </h3>
          <p className="mt-1 text-xs text-slate-600 dark:text-slate-400">
            Same skill, different word. Matching the posting&apos;s wording costs you
            nothing and is the highest-value change here.
          </p>
          <ul className="mt-3 space-y-2">
            {reworded.map((item) => (
              <li
                key={item.keyword}
                className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm dark:border-amber-900 dark:bg-amber-950"
              >
                <div className="flex flex-wrap items-center gap-2">
                  <span className="text-slate-500 line-through dark:text-slate-400">
                    {item.current_wording}
                  </span>
                  <span aria-hidden="true" className="text-slate-400">→</span>
                  <span className="font-medium text-slate-900 dark:text-slate-100">
                    {item.keyword}
                  </span>
                </div>
                {item.where ? (
                  <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">in {item.where}</p>
                ) : null}
              </li>
            ))}
          </ul>
        </Card>
      ) : null}

      {missing.length ? (
        <Card>
          <h3 className="text-sm font-semibold text-slate-900 dark:text-slate-100">
            Not on your CV
          </h3>
          <p className="mt-1 text-xs text-slate-600 dark:text-slate-400">
            We won&apos;t add these for you. If you genuinely have one, add it to your CV
            yourself with a real example.
          </p>
          <ul className="mt-3 space-y-2">
            {missing.map((item) => (
              <li key={item.keyword} className="flex flex-wrap items-center gap-2 text-sm">
                <Badge variant={item.importance === 'required' ? 'warning' : 'neutral'}>
                  {item.importance}
                </Badge>
                <span className="font-medium text-slate-900 dark:text-slate-100">
                  {item.keyword}
                </span>
                <span className="text-xs text-slate-500 dark:text-slate-400">{item.question}</span>
              </li>
            ))}
          </ul>
        </Card>
      ) : null}

      {matched.length ? (
        <Card>
          <h3 className="text-sm font-semibold text-slate-900 dark:text-slate-100">
            Already matching ({matched.length})
          </h3>
          <div className="mt-3 flex flex-wrap gap-2">
            {matched.map((item) => (
              <span
                key={item.keyword}
                title={item.evidence}
                className="rounded-full border border-emerald-200 bg-emerald-50 px-3 py-1 text-xs font-medium text-emerald-800 dark:border-emerald-900 dark:bg-emerald-950 dark:text-emerald-200"
              >
                {item.keyword}
              </span>
            ))}
          </div>
        </Card>
      ) : null}

      {match.cover_letter ? (
        <Card>
          <div className="flex flex-wrap items-center justify-between gap-3">
            <h3 className="text-sm font-semibold text-slate-900 dark:text-slate-100">
              Cover letter
            </h3>
            <CopyButton text={match.cover_letter} label="Copy letter" />
          </div>
          <Alert variant="info" className="mt-3">
            Read it before you send it. Every claim should be something you can talk
            about in an interview.
          </Alert>
          <pre className="mt-3 whitespace-pre-wrap font-sans text-sm leading-relaxed text-slate-800 dark:text-slate-100">
            {match.cover_letter}
          </pre>
        </Card>
      ) : null}
    </div>
  );
}
