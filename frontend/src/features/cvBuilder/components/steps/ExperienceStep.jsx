import { useState } from 'react';

import { Button, ConfirmDialog } from '@/components/ui';

import {
  useCreateExperience,
  useDeleteExperience,
  useExperiences,
  useReorderExperiences,
  useUpdateExperience,
} from '../../api/cvQueries';
import { EMPLOYMENT_TYPES, formatDateRange, LOCATION_TYPES } from '../../constants';
import { useReorder } from '../../hooks/useReorder';
import { EntryCard } from '../EntryCard';
import { EmptyState, SectionShell } from '../SectionShell';
import { BulletList } from './BulletList';
import { ExperienceForm } from './ExperienceForm';

function labelFor(options, value) {
  return options.find((option) => option.value === value)?.label ?? '';
}

export function ExperienceStep() {
  const [formOpen, setFormOpen] = useState(false);
  const [editing, setEditing] = useState(null);
  const [pendingDelete, setPendingDelete] = useState(null);

  const { data: experiences = [], isLoading } = useExperiences();
  const createMutation = useCreateExperience();
  const updateMutation = useUpdateExperience();
  const deleteMutation = useDeleteExperience();
  const reorderMutation = useReorderExperiences();

  const { moveUp, moveDown, isReordering } = useReorder(experiences, reorderMutation);

  const openCreate = () => {
    setEditing(null);
    setFormOpen(true);
  };

  const openEdit = (experience) => {
    setEditing(experience);
    setFormOpen(true);
  };

  const handleSubmit = async (payload) => {
    try {
      if (editing) {
        await updateMutation.mutateAsync({ id: editing.id, payload });
      } else {
        await createMutation.mutateAsync(payload);
      }
      setFormOpen(false);
      setEditing(null);
    } catch {
      // toast handled by the mutation
    }
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
      title="Work Experience"
      description="Each bullet is stored separately so the AI can rewrite individual achievements per application."
      isLoading={isLoading}
      action={
        <Button size="sm" onClick={openCreate}>
          + Add experience
        </Button>
      }
    >
      {experiences.length === 0 ? (
        <EmptyState
          message="No work experience yet"
          hint="Add one role with at least two bullets to earn the full 25 points."
        />
      ) : (
        <div className="space-y-3">
          {experiences.map((experience, index) => {
            const details = [
              labelFor(EMPLOYMENT_TYPES, experience.employment_type),
              experience.location,
              labelFor(LOCATION_TYPES, experience.location_type),
            ]
              .filter(Boolean)
              .join(' · ');

            const dates = formatDateRange({
              startMonth: experience.start_month,
              startYear: experience.start_year,
              endMonth: experience.end_month,
              endYear: experience.end_year,
              isCurrent: experience.is_current,
            });

            return (
              <EntryCard
                key={experience.id}
                title={experience.role_title}
                subtitle={experience.company_name}
                meta={[dates, details].filter(Boolean).join('  •  ')}
                onEdit={() => openEdit(experience)}
                onDelete={() => setPendingDelete(experience)}
                onMoveUp={() => moveUp(index)}
                onMoveDown={() => moveDown(index)}
                canMoveUp={index > 0}
                canMoveDown={index < experiences.length - 1}
                reordering={isReordering}
              >
                <BulletList experienceId={experience.id} bullets={experience.bullets ?? []} />
              </EntryCard>
            );
          })}
        </div>
      )}

      <ExperienceForm
        open={formOpen}
        experience={editing}
        onClose={() => {
          setFormOpen(false);
          setEditing(null);
        }}
        onSubmit={handleSubmit}
        loading={createMutation.isPending || updateMutation.isPending}
      />

      <ConfirmDialog
        open={Boolean(pendingDelete)}
        onClose={() => setPendingDelete(null)}
        onConfirm={handleDelete}
        loading={deleteMutation.isPending}
        title="Delete this experience?"
        description={
          pendingDelete
            ? `"${pendingDelete.role_title}" and all of its bullets will be permanently removed.`
            : undefined
        }
      />
    </SectionShell>
  );
}
