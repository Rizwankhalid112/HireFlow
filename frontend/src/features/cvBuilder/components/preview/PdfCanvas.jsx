import { useEffect, useRef, useState } from 'react';
import * as pdfjsLib from 'pdfjs-dist';
import workerUrl from 'pdfjs-dist/build/pdf.worker.min.mjs?url';

import { Spinner } from '@/components/ui';

/* The worker must be the exact version pdfjs-dist ships, so resolve it through
   Vite rather than a CDN or a hand-written path. */
pdfjsLib.GlobalWorkerOptions.workerSrc = workerUrl;

/*
 * Renders the real PDF to <canvas>. This is why the preview is a true snapshot:
 * we are not re-laying-out the CV in the browser, we are drawing the same
 * document the download returns.
 */
export function PdfCanvas({ data, scale = 1.35 }) {
  const containerRef = useRef(null);
  const [pageCount, setPageCount] = useState(0);
  const [error, setError] = useState(null);
  const [rendering, setRendering] = useState(true);

  useEffect(() => {
    if (!data) return undefined;

    let cancelled = false;
    let pdf = null;
    const container = containerRef.current;

    async function render() {
      setRendering(true);
      setError(null);

      try {
        // pdf.js takes ownership of the buffer it is given, so hand it a copy —
        // otherwise a re-render of the same blob throws on a detached buffer.
        const task = pdfjsLib.getDocument({ data: data.slice(0) });
        pdf = await task.promise;
        if (cancelled) return;

        setPageCount(pdf.numPages);
        container.replaceChildren();

        const dpr = window.devicePixelRatio || 1;

        for (let pageNumber = 1; pageNumber <= pdf.numPages; pageNumber += 1) {
          const page = await pdf.getPage(pageNumber);
          if (cancelled) return;

          const viewport = page.getViewport({ scale });
          const canvas = document.createElement('canvas');
          const context = canvas.getContext('2d');

          // Back the canvas at device resolution so text stays crisp, then let
          // CSS scale it back down to layout size.
          canvas.width = Math.floor(viewport.width * dpr);
          canvas.height = Math.floor(viewport.height * dpr);
          canvas.style.width = `${viewport.width}px`;
          canvas.style.height = `${viewport.height}px`;
          canvas.className =
            'mx-auto mb-4 max-w-full rounded-lg border border-slate-200 bg-white shadow-sm dark:border-slate-700';
          canvas.setAttribute('aria-label', `CV page ${pageNumber}`);

          container.appendChild(canvas);
          await page.render({
            canvasContext: context,
            viewport,
            transform: dpr === 1 ? null : [dpr, 0, 0, dpr, 0, 0],
          }).promise;
        }
      } catch (renderError) {
        if (!cancelled) {
          setError(renderError?.message || 'Could not display the PDF.');
        }
      } finally {
        if (!cancelled) setRendering(false);
      }
    }

    render();

    return () => {
      cancelled = true;
      pdf?.destroy?.();
    };
  }, [data, scale]);

  return (
    <div>
      {rendering ? <Spinner className="py-10" /> : null}
      {error ? <p className="py-6 text-center text-sm text-red-600">{error}</p> : null}
      <div ref={containerRef} className={rendering ? 'hidden' : ''} />
      {!rendering && !error && pageCount > 0 ? (
        <p className="text-center text-xs text-slate-500 dark:text-slate-400">
          {pageCount} {pageCount === 1 ? 'page' : 'pages'}
        </p>
      ) : null}
    </div>
  );
}
