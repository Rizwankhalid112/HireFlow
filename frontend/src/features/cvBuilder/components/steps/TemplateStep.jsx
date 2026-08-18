import { lazy, Suspense, useState } from 'react';

import { Alert, Badge, Button, Spinner } from '@/components/ui';

import {
  usePatchProfile,
  usePreviewMeta,
  usePreviewPdf,
  useTemplates,
} from '../../api/cvQueries';
import { SectionShell } from '../SectionShell';
import { PhotoUploader } from './PhotoUploader';

/* pdfjs-dist is ~450 kB. Loading it lazily keeps it out of the main CV Builder
   chunk for users who never open this step. */
const PdfCanvas = lazy(() =>
  import('../preview/PdfCanvas').then((module) => ({ default: module.PdfCanvas })),
);

function TemplateCard({ template, selected, onSelect, disabled }) {
  return (
    <button
      type="button"
      onClick={() => onSelect(template.id)}
      disabled={disabled}
      aria-pressed={selected}
      className={`rounded-xl border p-4 text-left transition-colors disabled:opacity-60 ${
        selected
          ? 'border-indigo-500 bg-indigo-50 ring-2 ring-indigo-200 dark:bg-slate-800 dark:ring-indigo-900'
          : 'border-slate-200 hover:border-slate-300 dark:border-slate-800 dark:hover:border-slate-700'
      }`}
    >
      <div className="flex items-start justify-between gap-2">
        <span className="font-medium text-slate-900 dark:text-slate-100">{template.name}</span>
        {selected ? <Badge variant="brand">Selected</Badge> : null}
      </div>

      <p className="mt-1 text-xs text-slate-600 dark:text-slate-400">{template.description}</p>

      <div className="mt-3 flex flex-wrap gap-1.5">
        {template.ats_safe ? (
          <Badge variant="success">ATS-safe</Badge>
        ) : (
          <Badge variant="warning">Not ATS-safe</Badge>
        )}
        {template.photo ? <Badge variant="neutral">Photo</Badge> : null}
        <Badge variant="neutral">
          {template.columns === 2 ? '2 column' : '1 column'}
        </Badge>
      </div>
    </button>
  );
}

export function TemplateStep({ profile }) {
  const { data: templates = [], isLoading } = useTemplates();
  const patchMutation = usePatchProfile();

  // Optimistic local choice so the preview switches instantly while the PATCH
  // that persists template_id is still in flight.
  const [pending, setPending] = useState(null);
  const selectedId = pending ?? profile?.template_id ?? 'minimal';

  const selected = templates.find((template) => template.id === selectedId);

  /* content_updated_at is bumped by the backend signals on every edit, so using
     it in the query key means the preview refetches exactly when the CV changes
     and is served from cache when it hasn't. */
  const stamp = profile?.content_updated_at ?? '';

  const { data: pdfData, isFetching: pdfLoading, isError: pdfError } = usePreviewPdf(
    selectedId,
    stamp,
    { enabled: Boolean(profile) },
  );
  const { data: meta } = usePreviewMeta(selectedId, stamp, { enabled: Boolean(profile) });

  const choose = (templateId) => {
    setPending(templateId);
    patchMutation.mutate({ template_id: templateId });
  };

  return (
    <div className="space-y-6">
      <SectionShell
        title="Template"
        description="Pick a layout. The preview below is the exact PDF you will download."
        isLoading={isLoading}
      >
        <div className="space-y-5">
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
            {templates.map((template) => (
              <TemplateCard
                key={template.id}
                template={template}
                selected={template.id === selectedId}
                onSelect={choose}
                disabled={patchMutation.isPending}
              />
            ))}
          </div>

          {selected && !selected.ats_safe ? (
            <Alert variant="warning">
              <strong>{selected.name}</strong> uses two columns. Many applicant tracking systems
              read straight across the page and scramble side-by-side text, so this looks great to
              a human but may parse poorly. Prefer a one-column template when applying through a
              job portal.
            </Alert>
          ) : null}

          {selected?.photo ? <PhotoUploader photoUrl={profile?.photo} /> : null}
        </div>
      </SectionShell>

      <SectionShell title="Preview" autosaves={false} description="Rendered from your saved CV.">
        {pdfError ? (
          <Alert variant="error">
            The preview could not be generated. If this persists, the PDF service may be
            unavailable.
          </Alert>
        ) : null}

        {pdfLoading && !pdfData ? <Spinner className="py-16" /> : null}

        {meta?.overflows ? (
          <Alert variant="warning" className="mb-4">
            Your CV runs to {meta.page_count} pages on {selected?.name}. That is perfectly normal
            for a longer career — or switch to <strong>Compact</strong> to tighten it up. Nothing
            is removed either way.
          </Alert>
        ) : null}

        {pdfData ? (
          <>
            <Suspense fallback={<Spinner className="py-16" />}>
              <PdfCanvas data={pdfData} />
            </Suspense>
            <div className="mt-4 flex justify-end">
              <Button
                variant="secondary"
                onClick={() => {
                  const blob = new Blob([pdfData.slice(0)], { type: 'application/pdf' });
                  const url = URL.createObjectURL(blob);
                  window.open(url, '_blank', 'noopener');
                  // Revoke on the next tick so the new tab has claimed it.
                  setTimeout(() => URL.revokeObjectURL(url), 60000);
                }}
              >
                Open PDF in new tab
              </Button>
            </div>
          </>
        ) : null}
      </SectionShell>
    </div>
  );
}
