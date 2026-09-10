import { useCallback, useEffect, useRef, useState } from 'react';
import { useSearchParams } from 'react-router-dom';

import { useMediaQuery } from '@/hooks/useMediaQuery';
import { Alert, Button, Card, Spinner } from '@/components/ui';

import { useCompletion, useCvProfile, useEnsureProfile, useTemplates } from '../api/cvQueries';
import { CompletionBar } from '../components/CompletionBar';
import { DangerZone } from '../components/DangerZone';
import { StepNavigator } from '../components/StepNavigator';
import { PreviewPane } from '../components/preview/PreviewPane';
import { PreviewSheet } from '../components/preview/PreviewSheet';
import { ContactStep } from '../components/steps/ContactStep';
import { EducationStep } from '../components/steps/EducationStep';
import { ExperienceStep } from '../components/steps/ExperienceStep';
import { ExtrasStep } from '../components/steps/ExtrasStep';
import { ProjectsStep } from '../components/steps/ProjectsStep';
import { SkillsStep } from '../components/steps/SkillsStep';
import { TemplateStep } from '../components/steps/TemplateStep';
import { usePreview } from '../hooks/usePreview';
import { useTemplateSelection } from '../hooks/useTemplateSelection';
import { STEPS } from '../constants';

const STEP_KEYS = STEPS.map((step) => step.key);

/* Tailwind's `xl`. Read in JS as well as CSS because the pane must not merely
   be hidden below this width — it must not mount, or a phone pays for a server
   render it never displays. */
const PREVIEW_PANE_QUERY = '(min-width: 1280px)';

export default function CVBuilderPage() {
  /* The step lives in the URL so the Dashboard can deep-link straight to the
     template gallery, and so back/forward and refresh behave sensibly. */
  const [searchParams, setSearchParams] = useSearchParams();
  const requested = searchParams.get('step');
  const activeStep = STEP_KEYS.includes(requested) ? requested : 'contact';

  const setActiveStep = useCallback(
    (key) => setSearchParams(key === 'contact' ? {} : { step: key }, { replace: true }),
    [setSearchParams],
  );

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

  /* Deleting removes the profile row, so every query below would 404 against a
     CV that no longer exists. Re-create the shell immediately and send the user
     back to the first step — the alternative is an error screen after a button
     they deliberately pressed. */
  const onCleared = (kind) => {
    if (kind !== 'deleted') {
      return;
    }
    setReady(false);
    ensureProfile
      .mutateAsync()
      .then(() => {
        setReady(true);
        setActiveStep(STEPS[0].key);
      })
      .catch(() => setReady(false));
  };

  const { data: profile, isLoading, isError } = useCvProfile({ enabled: ready });
  const { data: completion } = useCompletion({ enabled: ready });
  const { data: templates = [] } = useTemplates();

  const { selectedId, select, isSaving } = useTemplateSelection(profile);
  const selectedTemplate = templates.find((template) => template.id === selectedId);

  const hasPane = useMediaQuery(PREVIEW_PANE_QUERY);
  const [sheetOpen, setSheetOpen] = useState(false);

  /* Held here rather than inside the pane because the mobile trigger shows it
     too, and it is only known once pdf.js has parsed the rendered document. */
  const [pageCount, setPageCount] = useState(0);
  const onPageCount = useCallback((count) => setPageCount(count), []);

  /* One preview query for both surfaces, so the pane and the mobile sheet share
     a single request and a single auto-refresh preference. */
  const preview = usePreview({
    profile,
    templateId: selectedId,
    enabled: ready && (hasPane || sheetOpen),
  });

  // Crossing the breakpoint with the sheet open would leave it stacked on top
  // of the pane showing the same document.
  useEffect(() => {
    if (hasPane && sheetOpen) {
      setSheetOpen(false);
    }
  }, [hasPane, sheetOpen]);

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
        return (
          <TemplateStep
            profile={profile}
            selectedId={selectedId}
            onSelect={select}
            isSaving={isSaving}
          />
        );
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

      <div className="grid gap-6 lg:grid-cols-[260px_minmax(0,1fr)] xl:grid-cols-[240px_minmax(0,1fr)_380px] 2xl:grid-cols-[260px_minmax(0,1fr)_460px]">
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

        <div className="min-w-0 space-y-6">
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

          <DangerZone onCleared={onCleared} />
        </div>

        {/* Mounted only above xl — see PREVIEW_PANE_QUERY. */}
        {hasPane ? (
          <Card className="sticky top-6 flex max-h-[calc(100vh-3rem)] flex-col">
            <PreviewPane
              preview={preview}
              template={selectedTemplate}
              profile={profile}
              pageCount={pageCount}
              onPageCount={onPageCount}
            />
          </Card>
        ) : null}
      </div>

      {/* Sticky rather than a floating circle, so it never covers a form field.
          Negative margins cancel AppLayout's own padding on <main>. */}
      {!hasPane ? (
        <div className="sticky bottom-0 z-30 -mx-4 -mb-4 border-t border-slate-200 bg-white/90 px-4 py-3 backdrop-blur md:-mx-6 md:-mb-6 md:px-6 dark:border-slate-800 dark:bg-slate-900/90">
          <Button className="w-full" onClick={() => setSheetOpen(true)}>
            Preview CV
            {pageCount > 0 ? ` · ${pageCount} ${pageCount === 1 ? 'page' : 'pages'}` : ''}
          </Button>
        </div>
      ) : null}

      {sheetOpen ? (
        <PreviewSheet
          open={sheetOpen}
          onClose={() => setSheetOpen(false)}
          preview={preview}
          template={selectedTemplate}
          profile={profile}
          pageCount={pageCount}
          onPageCount={onPageCount}
        />
      ) : null}
    </div>
  );
}
