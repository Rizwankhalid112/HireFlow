import { Icon, Panel, SkeletonRows } from '@/components/ui';

/* `autosaves` is on by default: every section except Contact & Summary writes
   immediately on add/edit, and users read a missing save button as data loss. */
export function SectionShell({ title, description, action, isLoading, autosaves = true, children }) {
  return (
    <Panel
      title={
        <span className="flex flex-wrap items-center gap-2">
          {title}
          {autosaves ? (
            <span className="inline-flex items-center gap-1 rounded-full border border-ok-line bg-ok-soft px-2 py-0.5 text-[11px] font-medium text-ok">
              <Icon name="check" size={10} strokeWidth={3} />
              Saves automatically
            </span>
          ) : null}
        </span>
      }
      description={description}
      action={action}
    >
      {isLoading ? <SkeletonRows rows={3} /> : children}
    </Panel>
  );
}

export function EmptyState({ message, hint }) {
  return (
    <div className="rounded-card border border-dashed border-line-strong px-4 py-9 text-center">
      <p className="text-[13px] font-medium text-ink">{message}</p>
      {hint ? <p className="mt-1 text-[11px] text-subtle">{hint}</p> : null}
    </div>
  );
}
