import { Badge } from '@/components/ui';

import { COMPLETE_THRESHOLD } from '../constants';

export function CompletionBar({ score = 0, isComplete = false }) {
  const safeScore = Math.max(0, Math.min(100, Number(score) || 0));
  const remaining = Math.max(0, COMPLETE_THRESHOLD - safeScore);

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium text-slate-700 dark:text-slate-200">
            CV completeness
          </span>
          {isComplete ? (
            <Badge variant="success">Complete</Badge>
          ) : (
            <Badge variant="warning">Draft</Badge>
          )}
        </div>
        <span className="text-sm font-semibold tabular-nums text-slate-900 dark:text-slate-100">
          {safeScore}%
        </span>
      </div>

      <div
        className="h-2 w-full overflow-hidden rounded-full bg-slate-200 dark:bg-slate-800"
        role="progressbar"
        aria-valuenow={safeScore}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label="CV completeness"
      >
        <div
          className={`h-full rounded-full transition-all duration-500 ${
            isComplete ? 'bg-emerald-500' : 'bg-indigo-600'
          }`}
          style={{ width: `${safeScore}%` }}
        />
      </div>

      <p className="text-xs text-slate-500 dark:text-slate-400">
        {isComplete
          ? 'Your CV is complete and safe from automatic draft cleanup.'
          : `${remaining}% more to reach ${COMPLETE_THRESHOLD}% and mark this CV complete.`}
      </p>
    </div>
  );
}
