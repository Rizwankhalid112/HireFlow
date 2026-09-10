import { useState } from 'react';

import { Badge, Spinner } from '@/components/ui';

import { templateSampleUrl } from '../api/cvApi';

/*
 * Canva-style picker: each card shows the template rendered with a realistic
 * demo CV, so the layout is visible before choosing. Clicking anywhere on a
 * card selects it — no separate confirm step.
 *
 * Thumbnails come from the same WeasyPrint pipeline as the real export, so a
 * card cannot misrepresent what the template actually produces.
 */
function TemplateCard({ template, selected, onSelect, disabled }) {
  const [loaded, setLoaded] = useState(false);
  const [failed, setFailed] = useState(false);

  return (
    <button
      type="button"
      onClick={() => onSelect(template.id)}
      disabled={disabled}
      aria-pressed={selected}
      aria-label={`Select the ${template.name} template`}
      className={`group flex flex-col overflow-hidden rounded-xl border text-left transition-all disabled:cursor-not-allowed disabled:opacity-60 ${
        selected
          ? 'border-indigo-500 ring-2 ring-indigo-400 dark:ring-indigo-500'
          : 'border-slate-200 hover:-translate-y-0.5 hover:border-indigo-300 hover:shadow-lg dark:border-slate-800 dark:hover:border-indigo-700'
      }`}
    >
      {/* A4 aspect so the card never reflows once the image arrives. */}
      <div className="relative aspect-[1/1.414] w-full overflow-hidden bg-slate-100 dark:bg-slate-800">
        {!loaded && !failed ? (
          <div className="absolute inset-0 flex items-center justify-center">
            <Spinner />
          </div>
        ) : null}

        {failed ? (
          <div className="absolute inset-0 flex items-center justify-center px-4 text-center text-xs text-slate-500 dark:text-slate-400">
            Preview unavailable
          </div>
        ) : (
          <img
            src={templateSampleUrl(template.id)}
            alt={`${template.name} template example`}
            loading="lazy"
            onLoad={() => setLoaded(true)}
            onError={() => setFailed(true)}
            className={`h-full w-full object-cover object-top transition-opacity duration-300 ${
              loaded ? 'opacity-100' : 'opacity-0'
            }`}
          />
        )}

        {selected ? (
          <span className="absolute right-2 top-2 flex h-7 w-7 items-center justify-center rounded-full bg-indigo-600 text-sm font-bold text-white shadow">
            ✓
          </span>
        ) : null}
      </div>

      <div className="border-t border-slate-200 p-3 dark:border-slate-800">
        <div className="flex items-center justify-between gap-2">
          <span className="font-medium text-slate-900 dark:text-slate-100">{template.name}</span>
          {selected ? (
            <span className="text-xs font-medium text-indigo-600 dark:text-indigo-400">
              Selected
            </span>
          ) : null}
        </div>

        <p className="mt-1 text-xs text-slate-600 dark:text-slate-400">{template.description}</p>

        <div className="mt-2 flex flex-wrap gap-1.5">
          {template.ats_safe ? (
            <Badge variant="success">ATS-safe</Badge>
          ) : (
            <Badge variant="warning">Not ATS-safe</Badge>
          )}
          {template.photo ? <Badge variant="neutral">Photo</Badge> : null}
          <Badge variant="neutral">{template.columns === 2 ? '2 column' : '1 column'}</Badge>
        </div>
      </div>
    </button>
  );
}

export function TemplateGallery({ templates, selectedId, onSelect, disabled }) {
  return (
    <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
      {templates.map((template) => (
        <TemplateCard
          key={template.id}
          template={template}
          selected={template.id === selectedId}
          onSelect={onSelect}
          disabled={disabled}
        />
      ))}
    </div>
  );
}
