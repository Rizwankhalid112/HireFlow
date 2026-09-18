import { Icon } from '@/components/ui';

import { STEPS } from '../constants';

/* `sectionCompletion` is the backend's section_completion dict, so the marks
   always reflect server-side scoring rather than a local guess. */
function stepState(step, sectionCompletion) {
  if (!step.sections.length) return 'optional';

  const flags = step.sections.map((section) => Boolean(sectionCompletion?.[section]));
  if (flags.every(Boolean)) return 'done';
  if (flags.some(Boolean)) return 'partial';
  return 'todo';
}

function StepMark({ state }) {
  if (state === 'done') {
    return (
      <span className="mt-0.5 grid size-4 shrink-0 place-items-center rounded-full bg-ok-solid text-white">
        <Icon name="check" size={9} strokeWidth={3.6} />
      </span>
    );
  }

  return (
    <span
      className={`mt-0.5 size-4 shrink-0 rounded-full border-2 ${
        state === 'partial' ? 'border-warn-solid bg-warn-soft' : 'border-line-strong'
      }`}
    />
  );
}

export function StepNavigator({ activeStep, onStepChange, sectionCompletion }) {
  return (
    <nav aria-label="CV sections" className="flex flex-col gap-0.5">
      {STEPS.map((step) => {
        const isActive = step.key === activeStep;
        const state = stepState(step, sectionCompletion);

        return (
          <button
            key={step.key}
            type="button"
            onClick={() => onStepChange(step.key)}
            aria-current={isActive ? 'step' : undefined}
            className={`flex w-full items-start gap-2.5 rounded-control px-2 py-1.5 text-left transition-colors ${
              isActive ? 'bg-accent-soft' : 'hover:bg-surface-3'
            }`}
          >
            <StepMark state={state} />

            <span className="min-w-0 flex-1">
              <span className="flex items-center justify-between gap-2">
                <span
                  className={`text-[13px] ${isActive ? 'font-semibold text-accent' : 'font-medium text-ink'}`}
                >
                  {step.label}
                </span>
                {step.points ? (
                  <span
                    className={`tabular shrink-0 text-[11px] ${
                      state === 'done' ? 'text-ok' : state === 'partial' ? 'text-warn' : 'text-subtle'
                    }`}
                  >
                    {state === 'done' ? `+${step.points}` : step.points}
                  </span>
                ) : null}
              </span>

              {/* Explains an apparently stalled score: these thresholds are
                  all-or-nothing, so a half-filled section scores zero. */}
              {state !== 'done' && step.requirement ? (
                <span className="mt-0.5 block text-[11px] leading-4 font-normal text-subtle">
                  {step.requirement}
                </span>
              ) : null}
            </span>
          </button>
        );
      })}
    </nav>
  );
}
