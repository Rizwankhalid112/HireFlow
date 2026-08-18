import { Button } from '@/components/ui';

/*
 * One row in a section list, with reorder controls.
 *
 * Reorder uses up/down buttons rather than drag-and-drop: the backend reorder
 * endpoint is all-or-nothing on the full ordered_ids array, and buttons keep
 * that contract honest without pulling in a DnD dependency. They are also
 * keyboard-accessible for free.
 */
export function EntryCard({
  title,
  subtitle,
  meta,
  children,
  onEdit,
  onDelete,
  onMoveUp,
  onMoveDown,
  canMoveUp = false,
  canMoveDown = false,
  reordering = false,
}) {
  return (
    <div className="rounded-xl border border-slate-200 p-4 transition-colors hover:border-slate-300 dark:border-slate-800 dark:hover:border-slate-700">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <p className="font-medium text-slate-900 dark:text-slate-100">{title}</p>
          {subtitle ? (
            <p className="mt-0.5 text-sm text-slate-600 dark:text-slate-400">{subtitle}</p>
          ) : null}
          {meta ? (
            <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">{meta}</p>
          ) : null}
        </div>

        <div className="flex shrink-0 items-center gap-1">
          {onMoveUp ? (
            <Button
              variant="ghost"
              size="sm"
              className="px-2"
              aria-label="Move up"
              disabled={!canMoveUp || reordering}
              onClick={onMoveUp}
            >
              ↑
            </Button>
          ) : null}
          {onMoveDown ? (
            <Button
              variant="ghost"
              size="sm"
              className="px-2"
              aria-label="Move down"
              disabled={!canMoveDown || reordering}
              onClick={onMoveDown}
            >
              ↓
            </Button>
          ) : null}
          {onEdit ? (
            <Button variant="ghost" size="sm" onClick={onEdit}>
              Edit
            </Button>
          ) : null}
          {onDelete ? (
            <Button
              variant="ghost"
              size="sm"
              className="text-red-600 hover:bg-red-50 dark:text-red-400 dark:hover:bg-red-950"
              onClick={onDelete}
            >
              Delete
            </Button>
          ) : null}
        </div>
      </div>

      {children ? <div className="mt-3">{children}</div> : null}
    </div>
  );
}
