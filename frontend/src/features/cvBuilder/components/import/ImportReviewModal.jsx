import { useMemo, useState } from 'react';

import { Alert, Button, Input, Modal } from '@/components/ui';

/*
 * The review step between a parse and the CV changing.
 *
 * Three jobs, and the second two are what stop this feature quietly losing
 * someone's data:
 *
 * 1. A per-section keep / replace / merge choice. Nothing is written without
 *    one, and the default for every section is `keep`.
 * 2. Sections we have no model for — Publications, Awards, Volunteering — are
 *    shown rather than dropped. The user can copy anything they want to keep.
 * 3. Rows missing a NOT NULL field get one inline question. We refuse to invent
 *    a start year; asking costs the user a keystroke and keeps the CV true.
 */

const KEEP = 'keep';
const REPLACE = 'replace';
const MERGE = 'merge';

const SECTIONS = [
  { key: 'personal', label: 'Contact details & summary', merge: 'Fill blanks only' },
  { key: 'work_experience', label: 'Work experience', merge: 'Add to existing' },
  { key: 'education', label: 'Education', merge: 'Add to existing' },
  { key: 'skills', label: 'Skills', merge: 'Add missing only' },
  { key: 'projects', label: 'Projects', merge: 'Add to existing' },
  { key: 'certifications', label: 'Certifications', merge: 'Add to existing' },
  { key: 'languages', label: 'Languages', merge: 'Add to existing' },
];

/* Field labels for the questions in §3 above. Kept short because they render
   as a placeholder inside a narrow input. */
const FIELD_LABEL = { start_year: 'Start year' };

function countOf(section, parsed) {
  if (section === 'personal') {
    return Object.values(parsed?.personal ?? {}).filter(Boolean).length;
  }
  return (parsed?.[section] ?? []).length;
}

function rowLabel(section, row, index) {
  if (section === 'work_experience') {
    return [row.role_title, row.company_name].filter(Boolean).join(' at ') || `Role ${index + 1}`;
  }
  if (section === 'education') {
    return [row.field_of_study, row.institution].filter(Boolean).join(' — ')
      || `Entry ${index + 1}`;
  }
  return row.name || row.language_name || `Item ${index + 1}`;
}

function ChoiceButtons({ value, onChange, mergeLabel, hasExisting }) {
  const options = [
    { value: KEEP, label: 'Keep mine' },
    { value: MERGE, label: mergeLabel },
    { value: REPLACE, label: 'Use theirs' },
  ];

  return (
    <div className="flex flex-wrap gap-1.5">
      {options.map((option) => {
        // With nothing to conflict with, "keep mine" and "add to existing" are
        // the same action described two ways, so only one is offered.
        if (!hasExisting && option.value === KEEP) {
          return null;
        }
        const active = value === option.value;
        return (
          <button
            key={option.value}
            type="button"
            onClick={() => onChange(option.value)}
            className={`rounded-full border px-3 py-1 text-xs font-medium transition-colors ${
              active
                ? 'border-slate-900 bg-slate-900 text-white dark:border-slate-100 dark:bg-slate-100 dark:text-slate-900'
                : 'border-slate-300 bg-white text-slate-600 hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-300 dark:hover:bg-slate-800'
            }`}
          >
            {option.label}
          </button>
        );
      })}
    </div>
  );
}

function AttentionRows({ section, rows, answers, onAnswer }) {
  const blocked = rows
    .map((row, index) => ({ row, index }))
    .filter(({ row }) => (row.needs_attention ?? []).length > 0);

  if (!blocked.length) {
    return null;
  }

  return (
    <div className="mt-3 space-y-2 rounded-lg border border-amber-300 bg-amber-50 p-3 dark:border-amber-800 dark:bg-amber-950">
      <p className="text-xs font-medium text-amber-800 dark:text-amber-200">
        Your CV didn&apos;t say these, and we won&apos;t guess. Fill them in to import these
        {blocked.length === 1 ? ' entry' : ' entries'}.
      </p>
      {blocked.map(({ row, index }) => (
        <div key={index} className="flex flex-wrap items-center gap-2">
          <span className="min-w-0 flex-1 truncate text-xs text-amber-900 dark:text-amber-100">
            {rowLabel(section, row, index)}
          </span>
          {(row.needs_attention ?? []).map((field) => (
            <Input
              key={field}
              type="number"
              inputMode="numeric"
              placeholder={FIELD_LABEL[field] ?? field}
              aria-label={`${FIELD_LABEL[field] ?? field} for ${rowLabel(section, row, index)}`}
              value={answers?.[section]?.[index]?.[field] ?? ''}
              onChange={(event) => onAnswer(section, index, field, event.target.value)}
              className="h-8 w-28 text-xs"
            />
          ))}
        </div>
      ))}
    </div>
  );
}

function UnmappedSections({ sections }) {
  if (!sections?.length) {
    return null;
  }

  return (
    <div className="rounded-lg border border-slate-200 bg-slate-50 p-3 dark:border-slate-700 dark:bg-slate-800/50">
      <p className="text-xs font-medium text-slate-700 dark:text-slate-200">
        We found {sections.length} section{sections.length === 1 ? '' : 's'} HireFlow has
        nowhere to put yet
      </p>
      <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
        Nothing here will be imported. Copy anything you want to keep before you finish.
      </p>
      <div className="mt-2 space-y-2">
        {sections.map((section) => (
          <details
            key={section.heading}
            className="rounded border border-slate-200 bg-white p-2 dark:border-slate-700 dark:bg-slate-900"
          >
            <summary className="cursor-pointer text-xs font-medium text-slate-700 dark:text-slate-200">
              {section.heading}
            </summary>
            <p className="mt-1.5 whitespace-pre-wrap text-xs text-slate-600 dark:text-slate-400">
              {section.content}
            </p>
          </details>
        ))}
      </div>
    </div>
  );
}

export function ImportReviewModal({ open, onClose, parsed, existing, onApply, isApplying }) {
  const [choices, setChoices] = useState({});
  const [answers, setAnswers] = useState({});

  const visible = useMemo(
    () => SECTIONS.filter((section) => countOf(section.key, parsed) > 0),
    [parsed],
  );

  const setChoice = (key, value) => setChoices((previous) => ({ ...previous, [key]: value }));

  const setAnswer = (section, index, field, value) =>
    setAnswers((previous) => ({
      ...previous,
      [section]: {
        ...(previous[section] ?? {}),
        [index]: { ...(previous[section]?.[index] ?? {}), [field]: value },
      },
    }));

  const chosenCount = Object.values(choices).filter((value) => value && value !== KEEP).length;

  return (
    <Modal
      open={open}
      onClose={onClose}
      title="Review what we found"
      description="Nothing has been changed yet. Choose what to bring across."
      size="lg"
      footer={
        <>
          <Button variant="ghost" onClick={onClose} disabled={isApplying}>
            Cancel
          </Button>
          <Button
            onClick={() => onApply(choices, answers)}
            loading={isApplying}
            disabled={chosenCount === 0}
          >
            {chosenCount === 0 ? 'Choose a section' : `Import ${chosenCount} section${chosenCount === 1 ? '' : 's'}`}
          </Button>
        </>
      }
    >
      <div className="space-y-4">
        {parsed?.notes?.length ? (
          <Alert variant="info">
            <ul className="list-inside list-disc space-y-1">
              {parsed.notes.map((note) => (
                <li key={note}>{note}</li>
              ))}
            </ul>
          </Alert>
        ) : null}

        {visible.map((section) => {
          const rows = section.key === 'personal' ? [] : parsed[section.key] ?? [];
          const found = countOf(section.key, parsed);
          const have = section.key === 'personal'
            ? (existing?.personal?.full_name ? 1 : 0)
            : existing?.[section.key]?.count ?? 0;

          return (
            <div
              key={section.key}
              className="rounded-lg border border-slate-200 p-3 dark:border-slate-700"
            >
              <div className="flex flex-wrap items-start justify-between gap-2">
                <div className="min-w-0">
                  <p className="text-sm font-medium text-slate-900 dark:text-slate-100">
                    {section.label}
                  </p>
                  <p className="mt-0.5 text-xs text-slate-500 dark:text-slate-400">
                    Found {found} · you have {have}
                  </p>
                </div>
                <ChoiceButtons
                  value={choices[section.key] ?? KEEP}
                  onChange={(value) => setChoice(section.key, value)}
                  mergeLabel={section.merge}
                  hasExisting={have > 0}
                />
              </div>

              {rows.length ? (
                <p className="mt-2 truncate text-xs text-slate-500 dark:text-slate-400">
                  {rows.slice(0, 3).map((row, index) => rowLabel(section.key, row, index)).join(' · ')}
                  {rows.length > 3 ? ` and ${rows.length - 3} more` : ''}
                </p>
              ) : null}

              <AttentionRows
                section={section.key}
                rows={rows}
                answers={answers}
                onAnswer={setAnswer}
              />
            </div>
          );
        })}

        <UnmappedSections sections={parsed?.unmapped_sections} />
      </div>
    </Modal>
  );
}
