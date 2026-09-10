import { useMemo, useRef, useState } from 'react';

import { Badge, Button, ConfirmDialog, FieldShell, Input, Select } from '@/components/ui';

import {
  useCreateSkill,
  useDeleteSkill,
  useReorderSkills,
  useSkills,
  useSkillSearch,
  useSuggestSkills,
  useUpdateSkill,
} from '../../api/cvQueries';
import { PROFICIENCY_LEVELS, SKILL_CATEGORIES, SKILLS_MIN_COUNT } from '../../constants';
import { useDebouncedValue } from '../../hooks/useDebouncedValue';
import { useReorder } from '../../hooks/useReorder';
import { toNullableDecimal } from '../../utils/payload';
import { SuggestionPanel } from '../ai/SuggestionPanel';
import { EmptyState, SectionShell } from '../SectionShell';

/*
 * Canonical flow (spec §5.2): the user searches SkillCanonical, and picking a
 * suggestion sends canonical_id so the backend fills name + category and marks
 * the skill verified. Free text is allowed but lands unverified.
 */
function SkillSearchInput({ onPick, onFreeText, disabled }) {
  const [term, setTerm] = useState('');
  const [open, setOpen] = useState(false);
  const debounced = useDebouncedValue(term, 300);
  const blurTimer = useRef(null);

  const { data: suggestions = [], isFetching } = useSkillSearch(debounced);

  const exactMatch = useMemo(
    () =>
      suggestions.find(
        (item) => item.canonical_name.toLowerCase() === term.trim().toLowerCase(),
      ),
    [suggestions, term],
  );

  const reset = () => {
    setTerm('');
    setOpen(false);
  };

  const pick = (canonical) => {
    onPick(canonical);
    reset();
  };

  const addFreeText = () => {
    const name = term.trim();
    if (!name) return;
    onFreeText(name);
    reset();
  };

  return (
    <div className="relative">
      <FieldShell
        id="skill_search"
        label="Add a skill"
        hint="Pick a suggestion to store the canonical spelling, or press Enter to add your own."
      >
        <Input
          id="skill_search"
          value={term}
          disabled={disabled}
          autoComplete="off"
          placeholder="Start typing — e.g. postgres"
          onChange={(event) => {
            setTerm(event.target.value);
            setOpen(true);
          }}
          onFocus={() => setOpen(true)}
          onBlur={() => {
            // Delay so a click on a suggestion registers before the list closes.
            blurTimer.current = setTimeout(() => setOpen(false), 150);
          }}
          onKeyDown={(event) => {
            if (event.key === 'Enter') {
              event.preventDefault();
              // Typing a canonical name in full and pressing Enter should still
              // store the verified canonical skill, not an unverified copy.
              if (exactMatch) {
                pick(exactMatch);
              } else {
                addFreeText();
              }
            }
            if (event.key === 'Escape') {
              reset();
            }
          }}
        />
      </FieldShell>

      {open && term.trim() ? (
        <div
          className="absolute z-20 mt-1 w-full overflow-hidden rounded-lg border border-slate-200 bg-white shadow-lg dark:border-slate-700 dark:bg-slate-900"
          onMouseDown={() => clearTimeout(blurTimer.current)}
        >
          {isFetching ? (
            <p className="px-3 py-2 text-sm text-slate-500 dark:text-slate-400">Searching…</p>
          ) : null}

          {!isFetching && suggestions.length === 0 ? (
            <p className="px-3 py-2 text-sm text-slate-500 dark:text-slate-400">
              No match. Press Enter to add “{term.trim()}” as a custom skill.
            </p>
          ) : null}

          <ul className="max-h-60 overflow-y-auto">
            {suggestions.map((canonical) => (
              <li key={canonical.id}>
                <button
                  type="button"
                  onClick={() => pick(canonical)}
                  className="flex w-full items-center justify-between gap-3 px-3 py-2 text-left text-sm text-slate-700 hover:bg-indigo-50 dark:text-slate-200 dark:hover:bg-slate-800"
                >
                  <span className="font-medium">{canonical.canonical_name}</span>
                  <span className="flex items-center gap-2">
                    {canonical.is_popular ? <Badge variant="brand">Popular</Badge> : null}
                    <span className="text-xs text-slate-500 dark:text-slate-400">
                      {canonical.category}
                    </span>
                  </span>
                </button>
              </li>
            ))}
          </ul>

          {!exactMatch && !isFetching && suggestions.length > 0 ? (
            <button
              type="button"
              onClick={addFreeText}
              className="w-full border-t border-slate-200 px-3 py-2 text-left text-sm text-slate-600 hover:bg-slate-50 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-800"
            >
              Add “{term.trim()}” as a custom skill
            </button>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}

function SkillRow({ skill, index, total, onMoveUp, onMoveDown, onDelete, onChange, reordering }) {
  return (
    <div className="flex flex-wrap items-center gap-3 rounded-xl border border-slate-200 p-3 dark:border-slate-800">
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-2">
          <span className="font-medium text-slate-900 dark:text-slate-100">{skill.name}</span>
          {skill.is_verified ? (
            <Badge variant="success">✓ Verified</Badge>
          ) : (
            <Badge variant="neutral">Custom</Badge>
          )}
          {skill.category ? <Badge variant="brand">{skill.category}</Badge> : null}
        </div>
      </div>

      <Select
        aria-label={`Proficiency for ${skill.name}`}
        className="w-40"
        placeholder="Proficiency"
        options={PROFICIENCY_LEVELS}
        value={skill.proficiency || ''}
        onChange={(event) => onChange({ proficiency: event.target.value })}
      />

      <Input
        aria-label={`Years of experience for ${skill.name}`}
        className="w-24"
        type="number"
        step="0.5"
        min="0"
        placeholder="Yrs"
        defaultValue={skill.years_of_exp ?? ''}
        onBlur={(event) => {
          const next = toNullableDecimal(event.target.value);
          if (next !== (skill.years_of_exp != null ? Number(skill.years_of_exp) : null)) {
            onChange({ years_of_exp: next });
          }
        }}
      />

      <div className="flex shrink-0 items-center gap-1">
        <Button
          variant="ghost"
          size="sm"
          className="px-2"
          aria-label="Move up"
          disabled={index === 0 || reordering}
          onClick={onMoveUp}
        >
          ↑
        </Button>
        <Button
          variant="ghost"
          size="sm"
          className="px-2"
          aria-label="Move down"
          disabled={index === total - 1 || reordering}
          onClick={onMoveDown}
        >
          ↓
        </Button>
        <Button
          variant="ghost"
          size="sm"
          className="text-red-600 hover:bg-red-50 dark:text-red-400 dark:hover:bg-red-950"
          onClick={onDelete}
        >
          Remove
        </Button>
      </div>
    </div>
  );
}

export function SkillsStep() {
  const [category, setCategory] = useState('');
  const [pendingDelete, setPendingDelete] = useState(null);

  const { data: skills = [], isLoading } = useSkills();
  const createMutation = useCreateSkill();
  const suggestMutation = useSuggestSkills();
  const updateMutation = useUpdateSkill();
  const deleteMutation = useDeleteSkill();
  const reorderMutation = useReorderSkills();

  const { moveUp, moveDown, isReordering } = useReorder(skills, reorderMutation);

  const remaining = Math.max(0, SKILLS_MIN_COUNT - skills.length);

  const addCanonical = (canonical) => {
    createMutation.mutate({ canonical_id: canonical.id, name: canonical.canonical_name });
  };

  const addFreeText = (name) => {
    createMutation.mutate({ name, category: category || '' });
  };

  /* Child resources have no PATCH, so an inline tweak sends the full object. */
  const patchSkill = (skill, changes) => {
    updateMutation.mutate({
      id: skill.id,
      payload: {
        name: skill.name,
        category: skill.category || '',
        proficiency: skill.proficiency || '',
        years_of_exp: skill.years_of_exp ?? null,
        is_featured: Boolean(skill.is_featured),
        ...changes,
      },
    });
  };

  const handleDelete = async () => {
    try {
      await deleteMutation.mutateAsync(pendingDelete.id);
    } catch {
      // toast handled by the mutation
    } finally {
      setPendingDelete(null);
    }
  };

  return (
    <SectionShell
      title="Skills"
      description="Matched against a canonical list so “React”, “ReactJS” and “React.js” count as one skill."
      isLoading={isLoading}
    >
      <div className="space-y-5">
        <div className="grid gap-4 sm:grid-cols-[1fr_200px]">
          <SkillSearchInput
            onPick={addCanonical}
            onFreeText={addFreeText}
            disabled={createMutation.isPending}
          />
          <FieldShell
            id="skill_category"
            label="Category for custom skills"
            hint="Ignored when you pick a suggestion."
          >
            <Select
              id="skill_category"
              placeholder="Uncategorised"
              options={SKILL_CATEGORIES}
              value={category}
              onChange={(event) => setCategory(event.target.value)}
            />
          </FieldShell>
        </div>

        {/* Two lists, and the distinction is the whole point: `evidenced` skills
            are demonstrated in text the user wrote and add in one click;
            role-suggested ones are not on the CV at all and are labelled as
            claims they will be asked to back up. */}
        <SuggestionPanel
          mutation={suggestMutation}
          label="Find skills in my CV"
          buildPayload={() => ({})}
          hasResult={(result) =>
            result.evidenced?.length > 0 || result.suggested_for_role?.length > 0
          }
          renderResult={(result) => (
            <div className="mt-3 space-y-4">
              {result.evidenced?.length ? (
                <div>
                  <p className="text-xs font-medium text-emerald-700 dark:text-emerald-300">
                    Found in your own experience and projects
                  </p>
                  <div className="mt-2 flex flex-wrap gap-2">
                    {result.evidenced.map((skill) => (
                      <button
                        key={skill.name}
                        type="button"
                        title={skill.evidence}
                        onClick={() =>
                          createMutation.mutate({
                            name: skill.name,
                            category: skill.category || '',
                            ...(skill.canonical_id ? { canonical_id: skill.canonical_id } : {}),
                          })
                        }
                        className="inline-flex items-center gap-1.5 rounded-full border border-emerald-300 bg-emerald-50 px-3 py-1 text-xs font-medium text-emerald-800 transition-colors hover:bg-emerald-100 dark:border-emerald-800 dark:bg-emerald-950 dark:text-emerald-200 dark:hover:bg-emerald-900"
                      >
                        + {skill.name}
                        {skill.is_verified ? <span aria-hidden="true">✓</span> : null}
                      </button>
                    ))}
                  </div>
                </div>
              ) : null}

              {result.suggested_for_role?.length ? (
                <div>
                  <p className="text-xs font-medium text-amber-700 dark:text-amber-300">
                    Common for your target role — not on your CV yet
                  </p>
                  <p className="mt-0.5 text-xs text-slate-500 dark:text-slate-400">
                    Only add these if you can talk about them in an interview.
                  </p>
                  <div className="mt-2 flex flex-wrap gap-2">
                    {result.suggested_for_role.map((skill) => (
                      <button
                        key={skill.name}
                        type="button"
                        onClick={() =>
                          createMutation.mutate({
                            name: skill.name,
                            category: skill.category || '',
                            ...(skill.canonical_id ? { canonical_id: skill.canonical_id } : {}),
                          })
                        }
                        className="inline-flex items-center gap-1.5 rounded-full border border-amber-300 bg-amber-50 px-3 py-1 text-xs font-medium text-amber-800 transition-colors hover:bg-amber-100 dark:border-amber-800 dark:bg-amber-950 dark:text-amber-200 dark:hover:bg-amber-900"
                      >
                        + {skill.name}
                      </button>
                    ))}
                  </div>
                </div>
              ) : null}
            </div>
          )}
        />

        {skills.length === 0 ? (
          <EmptyState
            message="No skills yet"
            hint={`Add ${SKILLS_MIN_COUNT} skills to earn the full 15 points.`}
          />
        ) : (
          <>
            {remaining > 0 ? (
              <p className="text-xs text-slate-500 dark:text-slate-400">
                {remaining} more {remaining === 1 ? 'skill' : 'skills'} to earn this section&apos;s
                points.
              </p>
            ) : null}

            <div className="space-y-2">
              {skills.map((skill, index) => (
                <SkillRow
                  key={skill.id}
                  skill={skill}
                  index={index}
                  total={skills.length}
                  reordering={isReordering}
                  onMoveUp={() => moveUp(index)}
                  onMoveDown={() => moveDown(index)}
                  onDelete={() => setPendingDelete(skill)}
                  onChange={(changes) => patchSkill(skill, changes)}
                />
              ))}
            </div>
          </>
        )}
      </div>

      <ConfirmDialog
        open={Boolean(pendingDelete)}
        onClose={() => setPendingDelete(null)}
        onConfirm={handleDelete}
        loading={deleteMutation.isPending}
        confirmLabel="Remove"
        title="Remove this skill?"
        description={pendingDelete ? `"${pendingDelete.name}" will be removed.` : undefined}
      />
    </SectionShell>
  );
}
