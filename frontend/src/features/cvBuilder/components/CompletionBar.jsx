import { Badge } from '@/components/ui';

import { COMPLETE_THRESHOLD } from '../constants';

export function CompletionBar({ score = 0, isComplete = false, compact = false }) {
  const safe = Math.max(0, Math.min(100, Number(score) || 0));
  const remaining = Math.max(0, COMPLETE_THRESHOLD - safe);

  return (
    <div className="flex flex-col gap-1.5">
      <div className="flex items-center justify-between gap-2">
        <span className="truncate text-xs font-medium text-ink">Completeness</span>
        <span className="flex shrink-0 items-center gap-1.5">
          {isComplete ? (
            <Badge variant="success">Complete</Badge>
          ) : (
            <Badge variant="warning">Draft</Badge>
          )}
          <span className="tabular text-[13px] font-semibold">{safe}%</span>
        </span>
      </div>

      <div
        className="h-1.5 overflow-hidden rounded-full bg-surface-3"
        role="progressbar"
        aria-valuenow={safe}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label="CV completeness"
      >
        <div
          className={`h-full rounded-full transition-[width] duration-500 ${isComplete ? 'bg-ok-solid' : 'bg-accent'}`}
          style={{ width: `${safe}%` }}
        />
      </div>

      {!compact ? (
        <p className="text-[11px] leading-4 text-subtle">
          {isComplete
            ? 'Complete, and safe from automatic draft cleanup.'
            : `${remaining} points to reach ${COMPLETE_THRESHOLD}% — sections score all or nothing.`}
        </p>
      ) : null}
    </div>
  );
}
