import { useCallback, useEffect, useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';

import * as cvApi from '../api/cvApi';
import { cvKeys } from '../api/cvQueries';
import { useDebouncedValue } from './useDebouncedValue';

/*
 * Everything the live preview knows, in one place, so no step component has to
 * know how the preview works.
 *
 * The preview is a *server* render displayed through pdf.js rather than a
 * client-side HTML reproduction, because the standing requirement is that what
 * you see is byte-identical to what you download — and WeasyPrint and a browser
 * disagree about font metrics and line breaking, so a reproduction would drift.
 * The cost of that choice is that every refresh is a real render, which is what
 * the debounce, the auto toggle and the visibility gate below exist to contain.
 */

// A render is ~360ms, so 600ms debounce + render lands inside the ~1s window
// where an update still reads as immediate. It is also comfortably longer than
// the gap between two quick adds, so a burst collapses into one render.
export const PREVIEW_DEBOUNCE_MS = 600;

const AUTO_STORAGE_KEY = 'cv_preview_auto';

/* Wrapped like every other storage access in the app — Safari private mode
   throws on access rather than returning null. */
function readAutoPreference() {
  try {
    return localStorage.getItem(AUTO_STORAGE_KEY) !== 'off';
  } catch {
    return true;
  }
}

function writeAutoPreference(value) {
  try {
    localStorage.setItem(AUTO_STORAGE_KEY, value ? 'on' : 'off');
  } catch {
    // Preference is not worth failing over; it just won't survive a reload.
  }
}

/*
 * True when there is genuinely nothing to draw. Rendering this state produces a
 * near-blank page that reads as a bug, and it costs a full render to produce.
 *
 * A name or a summary alone is worth previewing, and any section at all moves
 * completion_score off zero — so this is only ever the untouched shell.
 */
export function isCvEmpty(profile) {
  if (!profile) {
    return true;
  }
  return (
    !profile.full_name &&
    !profile.summary &&
    (profile.completion_score ?? 0) === 0
  );
}

export function usePreview({ profile, templateId, enabled = true }) {
  const [auto, setAutoState] = useState(readAutoPreference);

  const setAuto = useCallback((next) => {
    setAutoState(next);
    writeAutoPreference(next);
  }, []);

  /* content_updated_at is bumped by the backend signals on every write, so it
     is the one value that changes whenever the CV does — whichever section was
     edited. Trigger off it rather than off keystrokes: our saves are already
     explicit per section, so the debounce collapses bursts of saves rather than
     characters. */
  const liveStamp = profile?.content_updated_at ?? '';
  const debouncedStamp = useDebouncedValue(liveStamp, PREVIEW_DEBOUNCE_MS);

  const [activeStamp, setActiveStamp] = useState(liveStamp);

  useEffect(() => {
    // With auto off the preview holds the last render until Refresh is pressed;
    // tracking it while auto is on means flipping the toggle off freezes on
    // what is currently displayed rather than on something older.
    if (auto) {
      setActiveStamp(debouncedStamp);
    }
  }, [auto, debouncedStamp]);

  useEffect(() => {
    // The very first stamp is adopted without waiting for the debounce.
    // Debouncing the initial load only delays the first paint, and it is not
    // collapsing a burst — there is nothing before it.
    setActiveStamp((current) => (current === '' && liveStamp ? liveStamp : current));
  }, [liveStamp]);

  const isEmpty = useMemo(() => isCvEmpty(profile), [profile]);

  const query = useQuery({
    queryKey: [...cvKeys.preview(templateId), activeStamp],
    // The signal aborts a superseded request: a render nobody will look at
    // still occupies a worker the form's own saves are queued behind.
    queryFn: ({ signal }) => cvApi.getPreviewPdf(templateId, signal).then((r) => r.data),
    /* Boolean(activeStamp) is what keeps the first render from firing under a
       blank stamp and then again under the real one — two requests for one
       page load, the second immediately superseding the first. */
    enabled: enabled && Boolean(profile) && Boolean(activeStamp) && !isEmpty,
    /* Stale-while-revalidate: keep the previous PDF on screen while the next
       one renders. Blanking to a spinner on every save reads as breakage. */
    placeholderData: (previous) => previous,
    /* The key already carries the content stamp, so data under a given key can
       never go out of date — only a new key can. */
    staleTime: Infinity,
    retry: false,
  });

  const { refetch } = query;

  const refresh = useCallback(() => {
    if (liveStamp !== activeStamp) {
      // Adopting the newer stamp changes the key, which fetches on its own.
      setActiveStamp(liveStamp);
    } else {
      refetch();
    }
  }, [liveStamp, activeStamp, refetch]);

  return {
    data: query.data,
    /* Content has moved on from what is displayed — either mid-debounce, or
       auto is off and this render is deliberately frozen. */
    isStale: liveStamp !== activeStamp,
    isFetching: query.isFetching,
    hasLoaded: Boolean(query.data),
    isError: query.isError,
    error: query.error,
    isEmpty,
    refresh,
    auto,
    setAuto,
  };
}
