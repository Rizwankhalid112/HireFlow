import { useState } from 'react';
import { toast } from 'sonner';

import { Alert, Badge, Button, Card, Icon, Panel } from '@/components/ui';

import { TailorPanel } from './TailorPanel';

/*
 * What came back from a match.
 *
 * The three keyword lists render as three visually distinct blocks, not one
 * tagged list, because they mean completely different things: one is
 * reassurance, one is a free win, and one is a question the user has to answer
 * honestly. Flattening them is what would turn this into a tool that quietly
 * encourages lying on a CV — so the colour system keeps them apart by design.
 */

const scoreTone = (score) => (score >= 75 ? 'text-ok' : score >= 50 ? 'text-warn' : 'text-bad');

function CopyButton({ text, label = 'Copy' }) {
  const [copied, setCopied] = useState(false);

  return (
    <Button
      size="sm"
      variant="secondary"
      icon={copied ? 'check' : 'copy'}
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

function BucketHead({ tone, icon, title, count, blurb }) {
  return (
    <div className={`flex flex-col gap-1 border-b px-4 py-3 ${tone}`}>
      <div className="flex items-center gap-2">
        <span className="grid size-4 place-items-center rounded">
          <Icon name={icon} size={13} strokeWidth={2.8} />
        </span>
        <h3 className="text-xs font-bold">{title}</h3>
        <span className="tabular ml-auto text-xs font-semibold">{count}</span>
      </div>
      <p className="text-[11px] leading-4">{blurb}</p>
    </div>
  );
}

export function MatchResult({ match }) {
  if (!match) return null;

  const { matched = [], reworded = [], missing = [] } = match;

  return (
    <div className="flex flex-col gap-3">
      <Card className="flex flex-wrap items-center gap-x-5 gap-y-3">
        <div className="flex flex-col gap-0.5">
          <span className={`text-3xl leading-none font-medium tracking-tight tabular-nums ${scoreTone(match.match_score)}`}>
            {match.match_score}%
          </span>
          <span className="text-[11px] text-subtle">keyword alignment</span>
        </div>

        <span className="h-10 w-px bg-line" />

        <div className="flex min-w-0 flex-1 flex-col gap-1">
          <h2 className="truncate text-sm font-semibold">
            {match.job_title || 'This role'}
            {match.company ? <span className="font-normal text-muted"> · {match.company}</span> : null}
          </h2>
          {match.summary ? <p className="text-xs leading-5 text-muted">{match.summary}</p> : null}
          {/* Said plainly, because every competitor implies otherwise. Nothing
              here has the applicant pool or the callback history. */}
          <p className="flex items-start gap-1.5 text-[11px] leading-4 text-subtle">
            <Icon name="info" size={12} className="mt-px" />
            How much of what the posting asks for appears in your CV — not a prediction of being
            interviewed. 75–85% is a good target; chasing 100% reads as keyword stuffing.
          </p>
        </div>

        <Badge>Matched against {match.source_label}</Badge>
      </Card>

      <div className="grid gap-3 lg:grid-cols-3">
        {matched.length ? (
          <div className="overflow-hidden rounded-card border border-ok-line bg-surface">
            <BucketHead
              tone="border-ok-line bg-ok-soft text-ok"
              icon="check"
              title="Matched"
              count={matched.length}
              blurb="Already on your CV, in the posting’s own words."
            />
            <ul className="flex flex-wrap content-start gap-1.5 p-3.5">
              {matched.map((item) => (
                <li
                  key={item.keyword}
                  title={item.evidence}
                  className="rounded-md border border-ok-line bg-ok-soft px-2 py-0.5 text-[11px] font-medium text-ok"
                >
                  {item.keyword}
                </li>
              ))}
            </ul>
          </div>
        ) : null}

        {reworded.length ? (
          <div className="overflow-hidden rounded-card border border-warn-line bg-surface">
            <BucketHead
              tone="border-warn-line bg-warn-soft text-warn"
              icon="swap"
              title="Reworded"
              count={reworded.length}
              blurb="You have it. They call it something else."
            />
            <ul className="flex flex-col gap-2 p-3.5">
              {reworded.map((item) => (
                <li key={item.keyword} className="flex flex-col gap-0.5">
                  <span className="flex flex-wrap items-center gap-1.5 text-[11px]">
                    <span className="text-subtle line-through">{item.current_wording}</span>
                    <Icon name="chevronRight" size={11} className="text-warn" strokeWidth={2.4} />
                    <span className="font-semibold text-warn">{item.keyword}</span>
                  </span>
                  {item.where ? <span className="text-[10px] text-subtle">in {item.where}</span> : null}
                </li>
              ))}
              <li className="mt-1 border-t border-warn-line pt-2 text-[10px] leading-4 text-warn">
                Rename these on your CV and the keyword scan finds them. This is the free win.
              </li>
            </ul>
          </div>
        ) : null}

        {missing.length ? (
          <div className="overflow-hidden rounded-card border border-bad-line bg-surface">
            <BucketHead
              tone="border-bad-line bg-bad-soft text-bad"
              icon="close"
              title="Missing"
              count={missing.length}
              blurb="Not on your CV. We will not add these for you."
            />
            <ul className="flex flex-col gap-2 p-3.5">
              {missing.map((item) => (
                <li key={item.keyword} className="flex flex-col gap-0.5">
                  <span className="flex flex-wrap items-center gap-1.5">
                    <span className="text-[11px] font-semibold text-bad">{item.keyword}</span>
                    {item.importance === 'required' ? (
                      <Badge variant="danger">required</Badge>
                    ) : (
                      <Badge>{item.importance}</Badge>
                    )}
                  </span>
                  {item.question ? (
                    <span className="text-[10px] leading-4 text-subtle">{item.question}</span>
                  ) : null}
                </li>
              ))}
              <li className="mt-1 border-t border-bad-line pt-2 text-[10px] leading-4 text-bad">
                If you have done one of these and simply have not written it down, add it in the
                builder. If you have not, leave it.
              </li>
            </ul>
          </div>
        ) : null}
      </div>

      {/* The buckets above are for reading; this is where the user acts. Only
          `reworded` is offered — see TailorPanel. */}
      {match.id ? <TailorPanel matchId={match.id} company={match.company} /> : null}

      {match.cover_letter ? (
        <Panel
          title="Cover letter"
          description="Drafted from the matched and reworded keywords only."
          action={<CopyButton text={match.cover_letter} label="Copy letter" />}
        >
          <Alert variant="info" className="mb-3">
            Read it before you send it. Every claim should be something you can talk about in an
            interview.
          </Alert>
          <pre className="font-sans text-[13px] leading-6 whitespace-pre-wrap text-ink">
            {match.cover_letter}
          </pre>
        </Panel>
      ) : null}
    </div>
  );
}
