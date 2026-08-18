import { Card, Spinner } from '@/components/ui';

export function SectionShell({ title, description, action, isLoading, children }) {
  return (
    <Card>
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-100">{title}</h2>
          {description ? (
            <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">{description}</p>
          ) : null}
        </div>
        {action}
      </div>

      <div className="mt-5">{isLoading ? <Spinner className="py-8" /> : children}</div>
    </Card>
  );
}

export function EmptyState({ message, hint }) {
  return (
    <div className="rounded-xl border border-dashed border-slate-300 px-4 py-10 text-center dark:border-slate-700">
      <p className="text-sm font-medium text-slate-700 dark:text-slate-200">{message}</p>
      {hint ? <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">{hint}</p> : null}
    </div>
  );
}
