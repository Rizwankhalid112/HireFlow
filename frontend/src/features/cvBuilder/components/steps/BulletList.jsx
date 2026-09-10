import { useState } from 'react';

import { Badge, Button, ConfirmDialog, Textarea } from '@/components/ui';

import {
  useCreateBullet,
  useDeleteBullet,
  useReorderBullets,
  useSuggestBullets,
  useUpdateBullet,
} from '../../api/cvQueries';
import { useReorder } from '../../hooks/useReorder';
import { SuggestionPanel } from '../ai/SuggestionPanel';

const MIN_LENGTH = 10;

function BulletComposer({ value, onChange, onSubmit, onCancel, loading, submitLabel }) {
  const tooShort = value.trim().length > 0 && value.trim().length < MIN_LENGTH;

  return (
    <div className="space-y-2">
      <Textarea
        rows={3}
        value={value}
        error={tooShort}
        onChange={(event) => onChange(event.target.value)}
        placeholder="Built a CI pipeline that cut deploy time by 40% across 12 services."
      />
      <div className="flex items-center justify-between gap-3">
        <p className="text-xs text-slate-500 dark:text-slate-400">
          {tooShort
            ? `At least ${MIN_LENGTH} characters.`
            : 'Include a number where you can — metrics are detected automatically.'}
        </p>
        <div className="flex gap-2">
          {onCancel ? (
            <Button variant="ghost" size="sm" onClick={onCancel} disabled={loading}>
              Cancel
            </Button>
          ) : null}
          <Button
            size="sm"
            onClick={onSubmit}
            loading={loading}
            disabled={value.trim().length < MIN_LENGTH}
          >
            {submitLabel}
          </Button>
        </div>
      </div>
    </div>
  );
}

export function BulletList({ experienceId, bullets = [] }) {
  const [draft, setDraft] = useState('');
  const [adding, setAdding] = useState(false);
  const [editingId, setEditingId] = useState(null);
  const [editingText, setEditingText] = useState('');
  const [pendingDelete, setPendingDelete] = useState(null);

  const createMutation = useCreateBullet();
  const updateMutation = useUpdateBullet();
  const deleteMutation = useDeleteBullet();
  const reorderMutation = useReorderBullets();
  const suggestMutation = useSuggestBullets();

  const { moveUp, moveDown, isReordering } = useReorder(bullets, reorderMutation, (orderedIds) => ({
    experienceId,
    orderedIds,
  }));

  const handleAdd = async () => {
    try {
      await createMutation.mutateAsync({ experienceId, payload: { text: draft.trim() } });
      setDraft('');
      setAdding(false);
    } catch {
      // toast handled by the mutation
    }
  };

  const handleUpdate = async () => {
    try {
      await updateMutation.mutateAsync({
        experienceId,
        bulletId: editingId,
        payload: { text: editingText.trim() },
      });
      setEditingId(null);
      setEditingText('');
    } catch {
      // toast handled by the mutation
    }
  };

  const handleDelete = async () => {
    try {
      await deleteMutation.mutateAsync({ experienceId, bulletId: pendingDelete.id });
      setPendingDelete(null);
    } catch {
      setPendingDelete(null);
    }
  };

  return (
    <div className="space-y-3 border-t border-slate-200 pt-3 dark:border-slate-800">
      {bullets.length === 0 && !adding ? (
        <p className="text-sm text-slate-500 dark:text-slate-400">
          No bullets yet. Two or more bullets on at least one role earns the experience points.
        </p>
      ) : null}

      <ul className="space-y-2">
        {bullets.map((bullet, index) => (
          <li key={bullet.id} className="rounded-lg bg-slate-50 p-3 dark:bg-slate-800/50">
            {editingId === bullet.id ? (
              <BulletComposer
                value={editingText}
                onChange={setEditingText}
                onSubmit={handleUpdate}
                onCancel={() => setEditingId(null)}
                loading={updateMutation.isPending}
                submitLabel="Save"
              />
            ) : (
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0 flex-1">
                  <p className="text-sm text-slate-700 dark:text-slate-200">{bullet.text}</p>

                  {/* impact_metric and skills_demonstrated are derived server-side. */}
                  {bullet.impact_metric || bullet.skills_demonstrated?.length ? (
                    <div className="mt-2 flex flex-wrap gap-1.5">
                      {bullet.impact_metric ? (
                        <Badge variant="success">📈 {bullet.impact_metric}</Badge>
                      ) : null}
                      {(bullet.skills_demonstrated ?? []).map((skill) => (
                        <Badge key={skill} variant="brand">
                          {skill}
                        </Badge>
                      ))}
                    </div>
                  ) : null}
                </div>

                <div className="flex shrink-0 items-center gap-1">
                  <Button
                    variant="ghost"
                    size="sm"
                    className="px-2"
                    aria-label="Move bullet up"
                    disabled={index === 0 || isReordering}
                    onClick={() => moveUp(index)}
                  >
                    ↑
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="px-2"
                    aria-label="Move bullet down"
                    disabled={index === bullets.length - 1 || isReordering}
                    onClick={() => moveDown(index)}
                  >
                    ↓
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => {
                      setEditingId(bullet.id);
                      setEditingText(bullet.text);
                    }}
                  >
                    Edit
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="text-red-600 hover:bg-red-50 dark:text-red-400 dark:hover:bg-red-950"
                    onClick={() => setPendingDelete(bullet)}
                  >
                    Delete
                  </Button>
                </div>
              </div>
            )}
          </li>
        ))}
      </ul>

      {adding ? (
        <BulletComposer
          value={draft}
          onChange={setDraft}
          onSubmit={handleAdd}
          onCancel={() => {
            setAdding(false);
            setDraft('');
          }}
          loading={createMutation.isPending}
          submitLabel="Add bullet"
        />
      ) : (
        <Button variant="secondary" size="sm" onClick={() => setAdding(true)}>
          + Add bullet
        </Button>
      )}

      {/* `needsNote` is always on here: a bullet generated from a job title
          alone has no facts to work from but the ones it invents. */}
      <SuggestionPanel
        mutation={suggestMutation}
        label="Suggest bullets"
        emptyLabel="Draft from a note"
        needsNote
        notePlaceholder="What did you actually do? e.g. 'added redis caching to the api'"
        buildPayload={({ note }) => ({ experience_id: experienceId, note })}
        onApply={(text) => createMutation.mutate({ experienceId, payload: { text } })}
        onApplyAndEdit={(text) => {
          setDraft(text);
          setAdding(true);
        }}
      />

      <ConfirmDialog
        open={Boolean(pendingDelete)}
        onClose={() => setPendingDelete(null)}
        onConfirm={handleDelete}
        loading={deleteMutation.isPending}
        title="Delete this bullet?"
        description="This cannot be undone."
      />
    </div>
  );
}
