import { Alert } from '@/components/ui';

import { useTemplates } from '../../api/cvQueries';
import { SectionShell } from '../SectionShell';
import { TemplateGallery } from '../TemplateGallery';
import { PhotoUploader } from './PhotoUploader';

/*
 * The gallery only. The preview used to live here too, but it is now a
 * permanent pane owned by CVBuilderPage — a preview that only exists on one
 * step is not a live preview.
 *
 * Selection state is lifted for the same reason: the pane has to render the
 * template the user just clicked even while they are editing another section.
 */
export function TemplateStep({ profile, selectedId, onSelect, isSaving }) {
  const { data: templates = [], isLoading } = useTemplates();

  const selected = templates.find((template) => template.id === selectedId);

  return (
    <SectionShell
      title="CV Templates"
      description="Each card shows a real CV in that layout. Click one to select it — the preview updates immediately."
      isLoading={isLoading}
    >
      <div className="space-y-5">
        <TemplateGallery
          templates={templates}
          selectedId={selectedId}
          onSelect={onSelect}
          disabled={isSaving}
        />

        {selected && !selected.ats_safe ? (
          <Alert variant="warning">
            <strong>{selected.name}</strong> uses two columns. Many applicant tracking systems read
            straight across the page and scramble side-by-side text, so this looks great to a human
            but may parse poorly. Prefer a one-column template when applying through a job portal.
          </Alert>
        ) : null}

        {selected?.photo ? <PhotoUploader photoUrl={profile?.photo} /> : null}
      </div>
    </SectionShell>
  );
}
