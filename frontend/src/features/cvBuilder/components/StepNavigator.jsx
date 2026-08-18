import { STEPS } from '../constants';

function StepDot({ state }) {
  if (state === 'done') {
    return (
      <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-emerald-500 text-[11px] font-bold text-white">
        ✓
      </span>
    );
  }

  return (
    <span
      className={`h-5 w-5 shrink-0 rounded-full border-2 ${
        state === 'partial'
          ? 'border-amber-400 bg-amber-100 dark:bg-amber-950'
          : 'border-slate-300 dark:border-slate-600'
      }`}
    />
  );
}

/* `sectionCompletion` is the backend's section_completion dict, so the dots
   always reflect server-side scoring rather than a local guess. */
function stepState(step, sectionCompletion) {
  if (!step.sections.length) {
    return 'optional';
  }

  const flags = step.sections.map((section) => Boolean(sectionCompletion?.[section]));
  if (flags.every(Boolean)) return 'done';
  if (flags.some(Boolean)) return 'partial';
  return 'todo';
}

export function StepNavigator({ activeStep, onStepChange, sectionCompletion }) {
  return (
    <nav aria-label="CV sections" className="space-y-1">
      {STEPS.map((step) => {
        const isActive = step.key === activeStep;
        const state = stepState(step, sectionCompletion);

        return (
          <button
            key={step.key}
            type="button"
            onClick={() => onStepChange(step.key)}
            aria-current={isActive ? 'step' : undefined}
            className={`flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-left text-sm font-medium transition-colors ${
              isActive
                ? 'bg-indigo-50 text-indigo-700 dark:bg-slate-800 dark:text-indigo-300'
                : 'text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800'
            }`}
          >
            <StepDot state={state} />
            <span className="flex-1">{step.label}</span>
          </button>
        );
      })}
    </nav>
  );
}
