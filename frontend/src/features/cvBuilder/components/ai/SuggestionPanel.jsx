import { useState } from 'react';

import { Alert, Badge, Button, Spinner, Textarea } from '@/components/ui';

import { useAcceptSuggestion, useSuggestionCredits } from '../../api/cvQueries';

/*
 * The shared surface for every AI suggestion in the CV Builder.
 *
 * Two rules are enforced here rather than left to each caller, because getting
 * either wrong in one place would undo the design:
 *
 * 1. Nothing is ever applied automatically. Suggestions are options; the user
 *    picks one. `onApply` only ever fires from a click.
 * 2. With an empty field the trigger asks for a rough note first. Generating
 *    from nothing leaves the model no material but its own invention, which is
 *    the failure mode the whole feature is designed around.
 */

const MAX_REGENERATIONS = 3;

function GapChips({ gaps, onAnswer }) {
  if (!gaps?.length) {
    return null;
  }

  return (
    <div className="mt-3 space-y-2">
      <p className="text-xs font-medium text-amber-700 dark:text-amber-300">
        Answer one of these and the suggestion gets sharper — we won&apos;t make a number up.
      </p>
      <div className="flex flex-wrap gap-2">
        {gaps.map((gap) => (
          <button
            key={gap.question}
            type="button"
            onClick={() => onAnswer(gap)}
            title={gap.why}
            className="inline-flex items-center gap-1.5 rounded-full border border-amber-300 bg-amber-50 px-3 py-1 text-xs font-medium text-amber-800 transition-colors hover:bg-amber-100 dark:border-amber-800 dark:bg-amber-950 dark:text-amber-200 dark:hover:bg-amber-900"
          >
            <span aria-hidden="true">?</span>
            {gap.question}
          </button>
        ))}
      </div>
    </div>
  );
}

function VariantCard({ variant, onUse, onEdit }) {
  return (
    <li className="rounded-lg border border-slate-200 bg-white p-3 dark:border-slate-700 dark:bg-slate-900">
      <p className="text-sm text-slate-800 dark:text-slate-100">{variant.text}</p>

      {variant.why ? (
        <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">{variant.why}</p>
      ) : null}

      {/* Provenance, not decoration: it shows which of the user's own words the
          line rests on, which is what makes the claim checkable. */}
      {variant.grounded_in?.length ? (
        <p className="mt-1.5 text-xs text-slate-500 dark:text-slate-400">
          From your text: {variant.grounded_in.slice(0, 3).join(' · ')}
        </p>
      ) : null}

      <div className="mt-2.5 flex gap-2">
        <Button size="sm" onClick={onUse}>
          Use this
        </Button>
        {onEdit ? (
          <Button size="sm" variant="ghost" onClick={onEdit}>
            Use &amp; edit
          </Button>
        ) : null}
      </div>
    </li>
  );
}

export function SuggestionPanel({
  mutation,
  buildPayload,
  onApply,
  onApplyAndEdit,
  label = 'Suggest with AI',
  emptyLabel = 'Draft from a note',
  needsNote = false,
  notePlaceholder = 'Roughly what did you do? A few words is enough.',
  resultKey = 'variants',
  hasResult,
  renderResult,
  active = true,
}) {
  const { data: credits } = useSuggestionCredits();
  const acceptMutation = useAcceptSuggestion();

  const [note, setNote] = useState('');
  const [noteOpen, setNoteOpen] = useState(false);
  const [attempts, setAttempts] = useState(0);

  /* `active` exists for lists that share one mutation across many rows — the
     project cards. Every row keeps a working trigger, but only the row that
     asked renders the response, so a sibling never displays someone else's
     suggestions. */
  const result = active ? mutation.data : undefined;
  const variants = result?.[resultKey] ?? [];
  // Skills return two lists rather than one, so a section can say for itself
  // whether the response was empty.
  const gotSomething = result ? (hasResult ? hasResult(result) : variants.length > 0) : false;
  const status = active ? mutation.error?.response?.status : undefined;

  const disabled = credits?.enabled === false || credits?.remaining === 0;

  const run = (extraNote) => {
    setAttempts((count) => count + 1);
    mutation.mutate(buildPayload({ note: extraNote ?? note }));
  };

  const start = () => {
    // An empty field means there is nothing to rewrite, so ask for material
    // before spending a credit on a guess.
    if (needsNote && !note.trim() && !noteOpen) {
      setNoteOpen(true);
      return;
    }
    run();
  };

  const accept = (variant, index, handler) => {
    if (result?.log_id) {
      acceptMutation.mutate({ logId: result.log_id, index });
    }
    handler(variant.text);
  };

  if (credits?.enabled === false) {
    return null;
  }

  return (
    <div className="mt-3 rounded-lg border border-dashed border-indigo-200 bg-indigo-50/40 p-3 dark:border-indigo-900 dark:bg-indigo-950/30">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <Button
            size="sm"
            variant="secondary"
            onClick={start}
            loading={active && mutation.isPending}
            disabled={disabled || attempts >= MAX_REGENERATIONS}
          >
            ✨ {needsNote && !note.trim() ? emptyLabel : label}
          </Button>
          {attempts > 0 && attempts < MAX_REGENERATIONS && gotSomething ? (
            <Button size="sm" variant="ghost" onClick={() => run()} disabled={mutation.isPending}>
              Try again
            </Button>
          ) : null}
        </div>

        {typeof credits?.remaining === 'number' ? (
          <Badge variant={credits.remaining === 0 ? 'warning' : 'neutral'}>
            {credits.remaining} left this month
          </Badge>
        ) : null}
      </div>

      {noteOpen && !gotSomething ? (
        <div className="mt-3 space-y-2">
          <Textarea
            rows={2}
            value={note}
            onChange={(event) => setNote(event.target.value)}
            placeholder={notePlaceholder}
          />
          <div className="flex justify-end gap-2">
            <Button size="sm" variant="ghost" onClick={() => setNoteOpen(false)}>
              Cancel
            </Button>
            <Button size="sm" onClick={() => run()} disabled={!note.trim()} loading={mutation.isPending}>
              Suggest
            </Button>
          </div>
        </div>
      ) : null}

      {attempts >= MAX_REGENERATIONS ? (
        <p className="mt-2 text-xs text-slate-500 dark:text-slate-400">
          That&apos;s three tries — the next one rarely helps. Editing by hand from here is
          usually faster.
        </p>
      ) : null}

      {/* 429 and 503 are states the user can act on, so they render inline
          rather than as a toast that disappears. */}
      {status === 429 ? (
        <Alert variant="warning" className="mt-3">
          <span className="text-xs">
            You&apos;ve used all your AI suggestions for this month. They reset on the 1st.
          </span>
        </Alert>
      ) : null}
      {status === 503 ? (
        <Alert variant="error" className="mt-3">
          <span className="text-xs">
            The writing assistant is unavailable right now. Your text is unchanged — try again in
            a moment.
          </span>
        </Alert>
      ) : null}

      {active && mutation.isPending ? <Spinner className="py-6" /> : null}

      {!mutation.isPending && gotSomething ? (
        <>
          {renderResult ? (
            renderResult(result)
          ) : (
            <ul className="mt-3 space-y-2">
              {variants.map((variant, index) => (
                <VariantCard
                  key={variant.text}
                  variant={variant}
                  onUse={() => accept(variant, index, onApply)}
                  onEdit={onApplyAndEdit ? () => accept(variant, index, onApplyAndEdit) : undefined}
                />
              ))}
            </ul>
          )}

          <GapChips
            gaps={result?.gaps}
            onAnswer={(gap) => {
              setNoteOpen(true);
              setNote((current) => (current ? `${current} — ${gap.question} ` : `${gap.question} `));
            }}
          />

          {result?.rejected > 0 ? (
            <p className="mt-2 text-xs text-slate-500 dark:text-slate-400">
              {result.rejected} suggestion{result.rejected === 1 ? '' : 's'} withheld — {result.rejected === 1 ? 'it' : 'they'} contained
              figures you hadn&apos;t mentioned.
            </p>
          ) : null}
        </>
      ) : null}

      {active && !mutation.isPending && mutation.isSuccess && !gotSomething && !status ? (
        <p className="mt-3 text-xs text-slate-500 dark:text-slate-400">
          Nothing solid to suggest from what&apos;s here yet. Add a little more detail and try
          again.
        </p>
      ) : null}
    </div>
  );
}
