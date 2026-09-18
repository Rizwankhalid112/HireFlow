import { useCallback, useEffect, useState } from 'react';

import { usePatchProfile } from '../api/cvQueries';
import { DEFAULT_TEMPLATE_ID } from '../constants';

/*
 * The selected template, held above both the gallery and the preview.
 *
 * It lives here rather than inside TemplateStep because the preview pane is now
 * always on screen and has to render the template the user just clicked, even
 * while they are on a different step.
 */
export function useTemplateSelection(profile) {
  const patchMutation = usePatchProfile();

  // Optimistic, so the preview switches on click rather than after the PATCH.
  const [pending, setPending] = useState(null);
  const saved = profile?.template_id ?? DEFAULT_TEMPLATE_ID;

  useEffect(() => {
    // Server has caught up — stop overriding it, so a later change made
    // elsewhere is not masked by a stale optimistic value.
    if (pending && pending === saved) {
      setPending(null);
    }
  }, [pending, saved]);

  const select = useCallback(
    (templateId) => {
      if (templateId === (pending ?? saved)) {
        return;
      }
      setPending(templateId);
      patchMutation.mutate(
        { template_id: templateId },
        // Without this the preview would keep showing a template the server
        // never stored.
        { onError: () => setPending(null) },
      );
    },
    [patchMutation, pending, saved],
  );

  return {
    selectedId: pending ?? saved,
    select,
    isSaving: patchMutation.isPending,
  };
}
