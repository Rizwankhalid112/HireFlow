import { IconButton } from '@/components/ui';

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
    <div className="group rounded-card border border-line px-3.5 py-3 transition-colors hover:border-line-strong hover:bg-surface-2">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <p className="text-[13px] font-semibold text-ink">{title}</p>
          {subtitle ? <p className="mt-0.5 text-xs text-muted">{subtitle}</p> : null}
          {meta ? <p className="mt-0.5 text-[11px] text-subtle">{meta}</p> : null}
        </div>

        <div className="flex shrink-0 items-center gap-0.5 opacity-60 transition-opacity group-hover:opacity-100 focus-within:opacity-100">
          {onMoveUp ? (
            <IconButton icon="arrowUp" label="Move up" size="sm" disabled={!canMoveUp || reordering} onClick={onMoveUp} />
          ) : null}
          {onMoveDown ? (
            <IconButton icon="arrowDown" label="Move down" size="sm" disabled={!canMoveDown || reordering} onClick={onMoveDown} />
          ) : null}
          {onEdit ? <IconButton icon="cv" label="Edit" size="sm" onClick={onEdit} /> : null}
          {onDelete ? (
            <IconButton icon="trash" label="Delete" size="sm" onClick={onDelete} className="hover:text-bad" />
          ) : null}
        </div>
      </div>

      {children ? <div className="mt-2.5">{children}</div> : null}
    </div>
  );
}
