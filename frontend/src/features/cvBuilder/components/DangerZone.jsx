import { useState } from 'react';

import { Button, Card, ConfirmDialog } from '@/components/ui';

import { useDeleteCv, useResetCv } from '../api/cvQueries';

/*
 * Clearing the CV without deleting nine roles one row at a time.
 *
 * Three actions rather than one, because they are genuinely different
 * intentions and collapsing them would make the safe one feel dangerous:
 *
 * - Clear one section — the common case, and what you want after an import
 *   brought in the wrong roles.
 * - Start over — empties everything but keeps the CV, the template you chose
 *   and the email on your account.
 * - Delete — removes the CV entirely.
 *
 * Every one of them is behind a confirm, and the confirm names what will go.
 */

const SECTIONS = [
  { key: 'work_experience', label: 'Work experience' },
  { key: 'education', label: 'Education' },
  { key: 'skills', label: 'Skills' },
  { key: 'projects', label: 'Projects' },
  { key: 'certifications', label: 'Certifications' },
  { key: 'languages', label: 'Languages' },
  { key: 'personal', label: 'Contact details & summary' },
  { key: 'photo', label: 'Photo' },
];

export function DangerZone({ onCleared }) {
  const [pending, setPending] = useState(null);
  const reset = useResetCv();
  const remove = useDeleteCv();

  const run = () => {
    if (!pending) {
      return;
    }
    if (pending.kind === 'delete') {
      remove.mutate(undefined, { onSuccess: () => { setPending(null); onCleared?.('deleted'); } });
      return;
    }
    reset.mutate(pending.sections, {
      onSuccess: () => { setPending(null); onCleared?.('reset'); },
    });
  };

  const busy = reset.isPending || remove.isPending;

  return (
    <Card>
      {/* Collapsed by default: it sits at the bottom of every step, and a row of
          eight delete buttons permanently open is a lot of destructive surface
          for something used once or twice. */}
      <details className="group">
        <summary className="cursor-pointer list-none">
          <span className="text-sm font-semibold text-slate-700 group-open:text-slate-900 dark:text-slate-300 dark:group-open:text-slate-100">
            Clear or delete
          </span>
          <span className="ml-2 text-xs text-slate-500 dark:text-slate-400">
            start a section again, or clear the whole CV
          </span>
        </summary>

      <div className="mt-4">
        <p className="text-xs font-medium text-slate-500 dark:text-slate-400">
          Clear one section
        </p>
        <div className="mt-2 flex flex-wrap gap-2">
          {SECTIONS.map((section) => (
            <button
              key={section.key}
              type="button"
              disabled={busy}
              onClick={() => setPending({
                kind: 'section',
                sections: [section.key],
                label: section.label,
              })}
              className="rounded-full border border-slate-300 px-3 py-1 text-xs font-medium text-slate-600 transition-colors hover:border-red-300 hover:bg-red-50 hover:text-red-700 disabled:opacity-50 dark:border-slate-700 dark:text-slate-300 dark:hover:border-red-800 dark:hover:bg-red-950 dark:hover:text-red-200"
            >
              {section.label}
            </button>
          ))}
        </div>
      </div>

      <div className="mt-5 flex flex-wrap gap-3 border-t border-slate-200 pt-4 dark:border-slate-800">
        <Button
          variant="secondary"
          size="sm"
          disabled={busy}
          onClick={() => setPending({ kind: 'all' })}
        >
          Start over
        </Button>
        <Button
          variant="danger"
          size="sm"
          disabled={busy}
          onClick={() => setPending({ kind: 'delete' })}
        >
          Delete my CV
        </Button>
      </div>

      <ConfirmDialog
        open={Boolean(pending)}
        onClose={() => setPending(null)}
        loading={busy}
        title={
          pending?.kind === 'delete'
            ? 'Delete your CV?'
            : pending?.kind === 'all'
              ? 'Start over?'
              : `Clear ${pending?.label?.toLowerCase()}?`
        }
        description={
          pending?.kind === 'delete'
            ? 'This removes your CV and everything in it, including imports. You can build a new one afterwards, but this one cannot be recovered.'
            : pending?.kind === 'all'
              ? 'This empties every section. You keep your CV, your chosen template and the email on your account.'
              : `This removes everything in ${pending?.label?.toLowerCase()}. Nothing else is touched.`
        }
        confirmLabel={
          pending?.kind === 'delete' ? 'Delete' : pending?.kind === 'all' ? 'Start over' : 'Clear'
        }
        onConfirm={run}
      />
      </details>
    </Card>
  );
}
