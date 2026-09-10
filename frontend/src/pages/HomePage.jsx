import { Link } from 'react-router-dom';

import { Card, Spinner } from '@/components/ui';
import { useProfile } from '@/features/auth/api/authQueries';
import { CompletionBar } from '@/features/cvBuilder/components/CompletionBar';
import { useCompletion, useTemplates } from '@/features/cvBuilder/api/cvQueries';
import { templateSampleUrl } from '@/features/cvBuilder/api/cvApi';

const stats = [
  { label: 'Total Applications', value: '0' },
  { label: 'Interviews', value: '0' },
  { label: 'Offers', value: '0' },
  { label: 'Pending', value: '0' },
];

export default function HomePage() {
  const { data: profile, isLoading } = useProfile();
  // 404s until the user opens the builder and a CV shell is created — that is a
  // normal state here, so the card just falls back to the empty prompt.
  const { data: completion, isError: noCv } = useCompletion();
  const { data: templates } = useTemplates();

  const fullName = profile?.user?.full_name || 'there';
  const hasCv = Boolean(completion) && !noCv;

  return (
    <div className="space-y-6">
      <Card>
        {isLoading ? (
          <Spinner className="py-4" />
        ) : (
          <>
            <h1 className="text-2xl font-semibold text-slate-900 dark:text-slate-100">
              Welcome back, {fullName}
            </h1>
            <p className="mt-2 text-sm text-slate-600 dark:text-slate-400">
              Your dashboard is ready. The Kanban board and application tracker will live here next.
            </p>
          </>
        )}
      </Card>

      <Card>
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div className="min-w-0 flex-1">
            <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-100">
              Your master CV
            </h2>
            <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">
              {hasCv
                ? 'Keep it complete so HireFlow can tailor it to each application.'
                : 'Build it once. HireFlow tailors it per application from there.'}
            </p>
            {hasCv ? (
              <div className="mt-4 max-w-md">
                <CompletionBar
                  score={completion.completion_score}
                  isComplete={completion.is_complete}
                />
              </div>
            ) : null}
          </div>
          <Link
            to="/cv-builder"
            className="inline-flex h-11 shrink-0 items-center justify-center rounded-lg bg-[rgb(var(--color-primary))] px-4 text-sm font-medium text-white transition-colors hover:bg-[rgb(var(--color-primary-hover))] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:ring-offset-2"
          >
            {hasCv ? 'Continue CV' : 'Start your CV'}
          </Link>
        </div>
      </Card>

      <Card>
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-100">
              CV Templates
            </h2>
            <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">
              Six layouts, each shown with a real CV so you can see how yours will look.
            </p>
          </div>
          <Link
            to="/cv-builder?step=template"
            className="inline-flex h-11 shrink-0 items-center justify-center rounded-lg border border-slate-200 bg-white px-4 text-sm font-medium text-slate-900 transition-colors hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-100 dark:hover:bg-slate-800"
          >
            Browse templates
          </Link>
        </div>

        {/* A strip of the real thumbnails — the tile shows the product rather
            than describing it. */}
        <Link to="/cv-builder?step=template" className="mt-4 flex gap-3 overflow-x-auto pb-1">
          {(templates ?? []).slice(0, 6).map((template) => (
            <span
              key={template.id}
              className="relative block w-[92px] shrink-0 overflow-hidden rounded-lg border border-slate-200 transition-colors hover:border-indigo-400 dark:border-slate-700"
            >
              <img
                src={templateSampleUrl(template.id)}
                alt={`${template.name} template`}
                loading="lazy"
                className="aspect-[1/1.414] w-full bg-slate-100 object-cover object-top dark:bg-slate-800"
              />
            </span>
          ))}
        </Link>
      </Card>

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {stats.map((stat) => (
          <Card key={stat.label}>
            <p className="text-sm text-slate-500 dark:text-slate-400">{stat.label}</p>
            <p className="mt-2 text-3xl font-semibold text-slate-900 dark:text-slate-100">
              {stat.value}
            </p>
          </Card>
        ))}
      </div>
    </div>
  );
}
