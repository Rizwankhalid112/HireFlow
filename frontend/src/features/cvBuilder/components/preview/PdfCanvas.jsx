import { useEffect, useRef, useState } from 'react';
import * as pdfjsLib from 'pdfjs-dist';
import workerUrl from 'pdfjs-dist/build/pdf.worker.min.mjs?url';

import { Spinner } from '@/components/ui';

/* The worker must be the exact version pdfjs-dist ships, so resolve it through
   Vite rather than a CDN or a hand-written path. */
pdfjsLib.GlobalWorkerOptions.workerSrc = workerUrl;

/* A4 is 595pt wide at scale 1, so container width / 595 is fit-to-width. */
const A4_WIDTH_PT = 595;

/* Past this the canvas costs more memory than the extra sharpness is worth —
   and a 1600px-wide pane does not need a 3x render. */
const MAX_SCALE = 2;

/*
 * Renders the real PDF to <canvas>. This is why the preview is a true snapshot:
 * we are not re-laying-out the CV in the browser, we are drawing the same
 * document the download returns.
 *
 * `scale` is measured from the container by default. A fixed value overflowed
 * the side pane; a phone and a 1600px desktop pane need different numbers, and
 * only the DOM knows which one we are in.
 */
export function PdfCanvas({ data, scale, onPageCount }) {
  const measureRef = useRef(null);
  const pagesRef = useRef(null);
  const [containerWidth, setContainerWidth] = useState(0);
  const [pageCount, setPageCount] = useState(0);
  const [error, setError] = useState(null);

  /* Held in a ref so an inline arrow from the caller does not land in the
     render effect's deps and redraw the whole document every commit. */
  const onPageCountRef = useRef(onPageCount);
  onPageCountRef.current = onPageCount;

  useEffect(() => {
    const element = measureRef.current;
    if (!element || typeof ResizeObserver === 'undefined') {
      return undefined;
    }

    /* Measured on a wrapper the canvases do not size, so a wider canvas can
       never widen the box being measured and start a feedback loop. Floored so
       sub-pixel jitter does not re-render the document. */
    const observer = new ResizeObserver(([entry]) => {
      setContainerWidth(Math.floor(entry.contentRect.width));
    });

    observer.observe(element);
    setContainerWidth(Math.floor(element.clientWidth));
    return () => observer.disconnect();
  }, []);

  const fitScale = containerWidth > 0
    ? Math.min(containerWidth / A4_WIDTH_PT, MAX_SCALE)
    : 0;
  const effectiveScale = scale ?? fitScale;

  useEffect(() => {
    // Width of 0 means we have not measured yet; rendering now would produce a
    // zero-size canvas that has to be thrown away.
    if (!data || effectiveScale <= 0) {
      return undefined;
    }

    let cancelled = false;
    let pdf = null;

    async function render() {
      setError(null);

      try {
        // pdf.js takes ownership of the buffer it is given, so hand it a copy —
        // otherwise a re-render of the same blob throws on a detached buffer.
        const task = pdfjsLib.getDocument({ data: data.slice(0) });
        pdf = await task.promise;
        if (cancelled) return;

        const dpr = window.devicePixelRatio || 1;

        /* Drawn into a fragment and swapped in at the end. Clearing the live
           container first would blank the preview on every save, which is
           exactly the flicker stale-while-revalidate exists to avoid. */
        const fragment = document.createDocumentFragment();

        for (let pageNumber = 1; pageNumber <= pdf.numPages; pageNumber += 1) {
          const page = await pdf.getPage(pageNumber);
          if (cancelled) return;

          const viewport = page.getViewport({ scale: effectiveScale });
          const canvas = document.createElement('canvas');
          const context = canvas.getContext('2d');

          // Back the canvas at device resolution so text stays crisp, then let
          // CSS scale it back down to layout size.
          canvas.width = Math.floor(viewport.width * dpr);
          canvas.height = Math.floor(viewport.height * dpr);
          canvas.style.width = `${viewport.width}px`;
          canvas.style.height = `${viewport.height}px`;
          canvas.className =
            'mx-auto mb-4 rounded-lg border border-slate-200 bg-white shadow-sm dark:border-slate-700';
          canvas.setAttribute('aria-label', `CV page ${pageNumber}`);

          fragment.appendChild(canvas);
          await page.render({
            canvasContext: context,
            viewport,
            transform: dpr === 1 ? null : [dpr, 0, 0, dpr, 0, 0],
          }).promise;
          if (cancelled) return;
        }

        pagesRef.current?.replaceChildren(fragment);
        setPageCount(pdf.numPages);
        onPageCountRef.current?.(pdf.numPages);
      } catch (renderError) {
        // An aborted render is the expected outcome of a superseded refresh,
        // not something to show the user.
        if (!cancelled && renderError?.name !== 'RenderingCancelledException') {
          setError(renderError?.message || 'Could not display the PDF.');
        }
      }
    }

    render();

    return () => {
      cancelled = true;
      pdf?.destroy?.();
    };
  }, [data, effectiveScale]);

  return (
    <div ref={measureRef} className="w-full">
      {/* Only ever shown before the first page exists — a refresh keeps the
          previous render on screen instead. */}
      {pageCount === 0 && !error ? <Spinner className="py-10" /> : null}

      {error ? (
        <p className="py-6 text-center text-sm text-red-600 dark:text-red-400">{error}</p>
      ) : null}

      <div ref={pagesRef} />
    </div>
  );
}
