import { lazy, Suspense } from 'react';

import { Alert, Badge, Button, Icon, Spinner } from '@/components/ui';

import { downloadPdf } from '../../utils/downloadPdf';

/* pdfjs-dist is ~450 kB. Loading it lazily keeps it out of the CV Builder's
   main chunk, which matters more now the preview is on every step. */
const PdfCanvas = lazy(() =>
  import('./PdfCanvas').then((module) => ({ default: module.PdfCanvas })),
);

function EmptyPreview() {
  return (
    <div className="flex flex-col items-center gap-2 rounded-card border border-dashed border-line-strong px-4 py-12 text-center">
      <Icon name="cv" size={22} className="text-subtle" />
      <p className="text-[13px] font-medium text-ink">Your CV will appear here</p>
      <p className="text-[11px] text-subtle">Add your name or a summary and this updates as you go.</p>
    </div>
  );
}

function PaneHeader({ template, pageCount, busy, preview, profile }) {
  const { data, isEmpty, refresh, auto, setAuto } = preview;

  return (
    <div className="flex flex-wrap items-center justify-between gap-2 border-b border-line px-3.5 py-2.5">
      <div className="flex min-w-0 items-center gap-2">
        <h2 className="truncate text-sm font-semibold text-ink">
          {template?.name ?? 'Preview'}
        </h2>
        {pageCount > 0 ? (
          <Badge variant="neutral">
            {pageCount} {pageCount === 1 ? 'page' : 'pages'}
          </Badge>
        ) : null}
        {busy ? (
          <span className="inline-flex items-center gap-1.5 text-xs text-subtle">
            <span className="h-3 w-3 animate-spin rounded-full border-2 border-line-strong border-t-accent" />
            Updating…
          </span>
        ) : null}
      </div>

      <div className="flex items-center gap-2">
        <label className="inline-flex cursor-pointer items-center gap-1.5 text-xs text-muted">
          <input
            type="checkbox"
            checked={auto}
            onChange={(event) => setAuto(event.target.checked)}
            className="h-3.5 w-3.5 rounded border-line-strong text-accent focus:ring-2 ring-accent/25"
          />
          Auto
        </label>
        <Button size="sm" variant="ghost" onClick={refresh} disabled={isEmpty}>
          Refresh
        </Button>
        <Button
          size="sm"
          variant="secondary"
          disabled={!data}
          onClick={() => downloadPdf(data, profile?.full_name)}
        >
          Download
        </Button>
      </div>
    </div>
  );
}

/*
 * The live preview: header controls plus the rendered document.
 *
 * It never clears while refreshing. The previous PDF stays on screen behind an
 * "Updating…" pill, because blanking to a spinner every time a section saves
 * reads as the app breaking rather than as it working.
 *
 * `pageCount` is owned by the caller so the mobile trigger and the sheet header
 * can show it too — it is only discovered once pdf.js has parsed the document.
 */
export function PreviewPane({
  preview,
  template,
  profile,
  scale,
  pageCount = 0,
  onPageCount,
  showHeader = true,
  className = '',
}) {
  const { data, isFetching, isStale, isError, isEmpty, refresh, auto } = preview;

  const overflows = Boolean(template) && pageCount > 0 && pageCount > template.max_pages;
  const busy = isFetching || (isStale && auto);

  return (
    <div className={`flex min-h-0 flex-col ${className}`}>
      {/* The mobile sheet renders its own header, so the pane skips this one
          rather than showing the template name twice on one screen. */}
      {showHeader ? (
        <PaneHeader
          template={template}
          pageCount={pageCount}
          busy={busy}
          preview={preview}
          profile={profile}
        />
      ) : null}

      <div className={`min-h-0 flex-1 ${showHeader ? 'overflow-y-auto bg-surface-3 p-3' : ''}`}>
        {/* Auto off is a deliberate choice, so it gets a quiet note rather than
            a warning — but the user must know the document is not current. */}
        {isStale && !auto ? (
          <p className="mb-3 rounded-lg bg-surface-3 px-3 py-2 text-xs text-muted">
            Your CV has changed since this render.{' '}
            <button
              type="button"
              onClick={refresh}
              className="font-medium text-accent underline"
            >
              Refresh
            </button>{' '}
            to update it.
          </p>
        ) : null}

        {/* A failed render keeps the last good document on screen — replacing
            working output with an error state loses the user more than it
            tells them. */}
        {isError ? (
          <Alert variant="error" className="mb-3">
            <span className="text-xs">
              {data
                ? 'The latest render failed, so this is the previous version. '
                : 'The preview could not be generated. '}
              <button type="button" onClick={refresh} className="font-medium underline">
                Try again
              </button>
            </span>
          </Alert>
        ) : null}

        {overflows ? (
          <Alert variant="warning" className="mb-3">
            <span className="text-xs">
              This runs to {pageCount} pages on {template.name}. Perfectly normal for a longer
              career — or switch to <strong>Compact</strong> to tighten it up. Nothing is removed
              either way.
            </span>
          </Alert>
        ) : null}

        {isEmpty ? <EmptyPreview /> : null}

        {!isEmpty && data ? (
          <Suspense fallback={<Spinner className="py-16" />}>
            <PdfCanvas data={data} scale={scale} onPageCount={onPageCount} />
          </Suspense>
        ) : null}

        {!isEmpty && !data && !isError ? <Spinner className="py-16" /> : null}
      </div>
    </div>
  );
}
