import { Link } from 'react-router-dom';

import { Badge, Button, Card, Icon, Panel, Skeleton } from '@/components/ui';
import { useProfile } from '@/features/auth/api/authQueries';
import { templateSampleUrl } from '@/features/cvBuilder/api/cvApi';
import { useCompletion, useCvSources, useTemplates } from '@/features/cvBuilder/api/cvQueries';
import { COMPLETE_THRESHOLD, STEPS } from '@/features/cvBuilder/constants';
import { useJobStats } from '@/features/jobs/api/jobsQueries';

function Metric({ label, value, foot, loading }) {
  return (
    <Card className="flex flex-col gap-2">
      <p className="text-xs font-medium text-muted">{label}</p>
      {loading ? (
        <Skeleton w="55%" h={24} />
      ) : (
        <p className="text-2xl leading-none font-medium tracking-tight tabular-nums">{value}</p>
      )}
      {foot ? <div className="text-[11px] text-subtle">{foot}</div> : null}
    </Card>
  );
}

/* The CV's score, explained. Scoring is all-or-nothing per section, so a
   half-filled section reads as "no progress" unless the weights are shown. */
function ScoreBreakdown({ sectionCompletion }) {
  const scored = STEPS.filter((step) => step.points > 0);

  return (
    <ul className="divide-y divide-line">
      {scored.map((step) => {
        const done = step.sections.every((section) => sectionCompletion?.[section]);

        return (
          <li key={step.key} className="flex items-center gap-3 py-2">
            <span
              className={`grid size-4 shrink-0 place-items-center rounded-full ${
                done ? 'bg-ok-solid text-white' : 'border-2 border-line-strong'
              }`}
            >
              {done && <Icon name="check" size={9} strokeWidth={3.4} />}
            </span>
            <span className={`flex-1 text-[13px] ${done ? 'font-medium text-ink' : 'text-muted'}`}>
              {step.label}
            </span>
            <span className={`tabular text-xs ${done ? 'text-ok' : 'text-subtle'}`}>
              {done ? `+${step.points}` : `${step.points} pts`}
            </span>
          </li>
        );
      })}
    </ul>
  );
}

export default function HomePage() {
  const { data: profile } = useProfile();
  /* 404s until the builder creates a CV shell — a normal state here, so the
     panel falls back to the "start one" prompt rather than an error. */
  const { data: completion, isError: noCv, isLoading: loadingCv } = useCompletion();
  const { data: templates } = useTemplates();
  const { data: stats, isLoading: loadingStats } = useJobStats();
  const { data: sources } = useCvSources();

  const firstName = (profile?.user?.full_name || '').split(' ')[0] || 'there';
  const hasCv = Boolean(completion) && !noCv;
  const score = completion?.completion_score ?? 0;
  const remaining = Math.max(0, COMPLETE_THRESHOLD - score);
  const matches = sources?.matches;

  return (
    <div className="mx-auto flex max-w-6xl flex-col gap-4">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold tracking-tight">Welcome back, {firstName}</h1>
          <p className="mt-0.5 text-xs text-muted">
            {hasCv && !completion.is_complete
              ? `Your CV is ${remaining} points from complete.`
              : 'Your master CV, your matches and today’s listings.'}
          </p>
        </div>
        <Link to="/cv-builder">
          <Button icon={hasCv ? 'cv' : 'plus'}>{hasCv ? 'Open CV Builder' : 'Start your CV'}</Button>
        </Link>
      </div>

      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <Metric
          label="CV completeness"
          value={hasCv ? `${score}%` : '—'}
          loading={loadingCv && !noCv}
          foot={
            hasCv ? (
              <div className="h-1 overflow-hidden rounded-full bg-surface-3">
                <div
                  className={`h-full rounded-full transition-[width] duration-500 ${
                    completion.is_complete ? 'bg-ok-solid' : 'bg-accent'
                  }`}
                  style={{ width: `${score}%` }}
                />
              </div>
            ) : (
              'Not started yet'
            )
          }
        />
        <Metric
          label="Jobs gathered"
          value={stats ? stats.total_jobs.toLocaleString() : '—'}
          loading={loadingStats}
          foot={stats ? `${stats.by_source.length} boards · refreshed nightly` : null}
        />
        <Metric
          label="Matches left this month"
          value={matches ? `${Math.max(matches.limit - matches.used, 0)} / ${matches.limit}` : '—'}
          foot="The most expensive call in the product"
        />
        <Metric
          label="Company boards"
          value={stats ? stats.companies.length : '—'}
          loading={loadingStats}
          foot={
            stats ? (
              <span className="flex items-center gap-1.5">
                <span
                  className={`size-1.5 rounded-full ${
                    stats.companies.every((c) => c.is_active) ? 'bg-ok-solid' : 'bg-warn-solid'
                  }`}
                />
                {stats.companies.every((c) => c.is_active) ? 'All healthy' : 'Some disabled'}
              </span>
            ) : null
          }
        />
      </div>

      <div className="grid items-start gap-3 lg:grid-cols-[1.3fr_1fr]">
        <Panel
          title="Your master CV"
          description="Scoring is all-or-nothing per section — a half-filled one scores zero."
          action={
            <Link to="/cv-builder">
              <Button variant="secondary" size="sm">
                {hasCv ? 'Continue' : 'Start'}
              </Button>
            </Link>
          }
          bodyClass="px-4 py-1"
        >
          {hasCv ? (
            <ScoreBreakdown sectionCompletion={completion.section_completion} />
          ) : (
            <p className="py-8 text-center text-xs text-muted">
              Build it once. HireFlow tailors it per application from there.
            </p>
          )}
        </Panel>

        <Panel
          title="Templates"
          description="Six layouts, five of them ATS-safe."
          action={
            <Link to="/cv-builder?step=template">
              <Button variant="secondary" size="sm">
                Browse
              </Button>
            </Link>
          }
        >
          <Link to="/cv-builder?step=template" className="grid grid-cols-3 gap-2.5">
            {(templates ?? []).slice(0, 6).map((template) => (
              <figure key={template.id} className="m-0 flex flex-col gap-1.5">
                <img
                  src={templateSampleUrl(template.id)}
                  alt={`${template.name} template`}
                  loading="lazy"
                  className="aspect-[1/1.414] w-full rounded border border-line bg-surface-3 object-cover object-top transition-colors hover:border-accent"
                />
                <figcaption className="flex items-center justify-between gap-1 text-[10px] text-subtle">
                  <span className="truncate">{template.name}</span>
                  {template.ats_safe ? <Badge variant="success">ATS</Badge> : null}
                </figcaption>
              </figure>
            ))}
            {!templates &&
              Array.from({ length: 6 }, (_, i) => (
                <Skeleton key={i} className="aspect-[1/1.414] w-full rounded" h="auto" />
              ))}
          </Link>
        </Panel>
      </div>
    </div>
  );
}
