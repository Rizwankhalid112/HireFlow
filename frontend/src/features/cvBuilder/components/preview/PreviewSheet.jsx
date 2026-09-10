import { useState } from 'react';

import { Badge, Button, Modal } from '@/components/ui';

import { downloadPdf } from '../../utils/downloadPdf';
import { PreviewPane } from './PreviewPane';

/*
 * The preview on phones and tablets, where there is no room for a third column.
 *
 * Opened on demand, and — this is the point of the visibility gate in
 * CVBuilderPage — nothing is fetched until it is. A phone must not pay for a
 * WeasyPrint render it never displays.
 */
export function PreviewSheet({ open, onClose, preview, template, profile, pageCount, onPageCount }) {
  /* A4 fit-to-width on a 375px screen is roughly 0.63 scale: readable as a
     layout, but too small to read the body text. So zoom is required here
     rather than a nicety. */
  const [zoomed, setZoomed] = useState(false);

  return (
    <Modal open={open} onClose={onClose} size="full">
      <div className="flex h-full min-h-0 flex-col">
        <div className="flex items-center justify-between gap-2 border-b border-slate-200 px-4 py-3 dark:border-slate-800">
          <div className="flex min-w-0 items-center gap-2">
            <h2 className="truncate text-sm font-semibold text-slate-900 dark:text-slate-100">
              {template?.name ?? 'Preview'}
            </h2>
            {pageCount > 0 ? (
              <Badge variant="neutral">
                {pageCount} {pageCount === 1 ? 'page' : 'pages'}
              </Badge>
            ) : null}
          </div>

          <div className="flex shrink-0 items-center gap-1">
            <Button size="sm" variant="ghost" onClick={() => setZoomed((value) => !value)}>
              {zoomed ? 'Fit' : '100%'}
            </Button>
            <Button
              size="sm"
              variant="secondary"
              disabled={!preview.data}
              onClick={() => downloadPdf(preview.data, profile?.full_name)}
            >
              Download
            </Button>
            <Button size="sm" variant="ghost" onClick={onClose} aria-label="Close preview">
              ✕
            </Button>
          </div>
        </div>

        <div
          className="min-h-0 flex-1 overflow-auto bg-slate-100 p-4 dark:bg-slate-950"
          // Leave native pinch-zoom alone; the toggle above is a shortcut, not
          // a replacement for it.
          style={{ touchAction: 'pan-x pan-y pinch-zoom' }}
        >
          <PreviewPane
            preview={preview}
            template={template}
            profile={profile}
            scale={zoomed ? 1 : undefined}
            pageCount={pageCount}
            onPageCount={onPageCount}
            showHeader={false}
          />
        </div>
      </div>
    </Modal>
  );
}
