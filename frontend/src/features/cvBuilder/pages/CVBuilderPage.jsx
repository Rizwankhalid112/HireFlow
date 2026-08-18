import { useEffect, useRef, useState } from 'react';

import { Alert, Button, Card, Spinner } from '@/components/ui';

import { useCompletion, useCvProfile, useEnsureProfile } from '../api/cvQueries';
import { CompletionBar } from '../components/CompletionBar';
import { StepNavigator } from '../components/StepNavigator';
import { ContactStep } from '../components/steps/ContactStep';
import { EducationStep } from '../components/steps/EducationStep';
import { ExperienceStep } from '../components/steps/ExperienceStep';
import { ExtrasStep } from '../components/steps/ExtrasStep';
import { ProjectsStep } from '../components/steps/ProjectsStep';
import { SkillsStep } from '../components/steps/SkillsStep';
import { TemplateStep } from '../components/steps/TemplateStep';
import { STEPS } from '../constants';

export default function CVBuilderPage() {
  const [activeStep, setActiveStep] = useState('contact');
  const [ready, setReady] = useState(false);

  const ensureProfile = useEnsureProfile();
  // POST /cv/profile/ is idempotent, but a ref keeps StrictMode's double effect
  // from firing a second pointless request in development.
  const ensureStarted = useRef(false);

  useEffect(() => {
    if (ensureStarted.current) return;
    ensureStarted.current = true;

    ensureProfile
      .mutateAsync()
      .then(() => setReady(true))
      .catch(() => setReady(false));
  }, [ensureProfile]);

  const { data: profile, isLoading, isError } = useCvProfile({ enabled: ready });
  const { data: completion } = useCompletion({ enabled: ready });

  // completion_score is recomputed on every write, so prefer the dedicated
  // endpoint and fall back to the copy embedded in the profile.
  const score = completion?.completion_score ?? profile?.completion_score ?? 0;
  const isComplete = completion?.is_complete ?? profile?.is_complete ?? false;
  const sectionCompletion = completion?.section_completion ?? profile?.section_completion ?? {};

  const activeIndex = STEPS.findIndex((step) => step.key === activeStep);
  const previousStep = activeIndex > 0 ? STEPS[activeIndex - 1] : null;
  const nextStep = activeIndex < STEPS.length - 1 ? STEPS[activeIndex + 1] : null;

  if (!ready && ensureProfile.isPending) {
    return <Spinner className="py-20" />;
  }

  if (ensureProfile.isError) {
    return (
      <Alert variant="error">
        We could not open your CV. Refresh the page, and if it keeps happening your session may have
        expired.
      </Alert>
    );
  }

  const renderStep = () => {
    switch (activeStep) {
      case 'contact':
        return <ContactStep profile={profile} />;
      case 'experience':
        return <ExperienceStep />;
      case 'education':
        return <EducationStep />;
      case 'skills':
        return <SkillsStep />;
      case 'projects':
        return <ProjectsStep />;
      case 'extras':
        return <ExtrasStep />;
      case 'template':
        return <TemplateStep profile={profile} />;
      default:
        return null;
    }
  };

  return (
    <div className="space-y-6">
      <Card>
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <h1 className="text-2xl font-semibold text-slate-900 dark:text-slate-100">
              CV Builder
            </h1>
            <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">
              One master CV. HireFlow tailors it per application rather than storing many copies.
            </p>
          </div>
          <div className="w-full max-w-sm">
            <CompletionBar score={score} isComplete={isComplete} />
            <p className="mt-2 text-xs text-slate-500 dark:text-slate-400">
              Every section saves as soon as you add or edit an entry — there is no separate save
              step outside Contact &amp; Summary.
            </p>
          </div>
        </div>
      </Card>

      {isError ? (
        <Alert variant="error">
          Your CV could not be loaded. Refresh to try again.
        </Alert>
      ) : null}

      <div className="grid gap-6 lg:grid-cols-[260px_1fr]">
        <Card className="h-fit lg:sticky lg:top-6">
          {/* Repeated here because the header card scrolls out of view while
              you work, and the score is the main feedback that a save landed. */}
          <div className="mb-4 border-b border-slate-200 pb-4 dark:border-slate-800">
            <CompletionBar score={score} isComplete={isComplete} />
          </div>
          <StepNavigator
            activeStep={activeStep}
            onStepChange={setActiveStep}
            sectionCompletion={sectionCompletion}
          />
        </Card>

        <div className="space-y-6">
          {isLoading ? <Spinner className="py-20" /> : renderStep()}

          <div className="flex items-center justify-between gap-3">
            <Button
              variant="secondary"
              disabled={!previousStep}
              onClick={() => previousStep && setActiveStep(previousStep.key)}
            >
              ← {previousStep ? previousStep.label : 'Back'}
            </Button>
            <Button
              disabled={!nextStep}
              onClick={() => nextStep && setActiveStep(nextStep.key)}
            >
              {nextStep ? nextStep.label : 'Done'} →
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
