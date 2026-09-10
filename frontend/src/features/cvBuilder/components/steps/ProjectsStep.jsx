import { useEffect, useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';

import {
  Badge,
  Button,
  Checkbox,
  ConfirmDialog,
  FormField,
  Modal,
  TextareaField,
} from '@/components/ui';

import {
  useCreateProject,
  useDeleteProject,
  useProjects,
  useReorderProjects,
  useSuggestProjectPoints,
  useUpdateProject,
} from '../../api/cvQueries';
import { MAX_TECH_STACK } from '../../constants';
import { useReorder } from '../../hooks/useReorder';
import { projectSchema } from '../../schemas/cvSchemas';
import { parseTechStack, toAbsoluteUrl, toNullableInt } from '../../utils/payload';
import { EntryCard } from '../EntryCard';
import { SuggestionPanel } from '../ai/SuggestionPanel';
import { EmptyState, SectionShell } from '../SectionShell';

const EMPTY = {
  name: '',
  subtitle: '',
  description: '',
  tech_stack: '',
  project_url: '',
  start_year: '',
  end_year: '',
  is_ongoing: false,
  is_professional: false,
};

function toFormValues(project) {
  if (!project) return EMPTY;

  return {
    name: project.name ?? '',
    subtitle: project.subtitle ?? '',
    description: project.description ?? '',
    // tech_stack is a JSON list server-side, edited as a comma-separated string.
    tech_stack: (project.tech_stack ?? []).join(', '),
    project_url: project.project_url ?? '',
    start_year: project.start_year != null ? String(project.start_year) : '',
    end_year: project.end_year != null ? String(project.end_year) : '',
    is_ongoing: Boolean(project.is_ongoing),
    is_professional: Boolean(project.is_professional),
  };
}

function ProjectFormModal({ open, onClose, project, onSubmit, loading }) {
  const {
    register,
    handleSubmit,
    reset,
    watch,
    formState: { errors },
  } = useForm({
    resolver: zodResolver(projectSchema),
    defaultValues: toFormValues(project),
  });

  useEffect(() => {
    if (open) {
      reset(toFormValues(project));
    }
  }, [open, project, reset]);

  const isOngoing = watch('is_ongoing');
  const techCount = parseTechStack(watch('tech_stack')).length;

  const submit = handleSubmit((values) => {
    onSubmit({
      name: values.name.trim(),
      subtitle: values.subtitle || '',
      description: values.description || '',
      tech_stack: parseTechStack(values.tech_stack, MAX_TECH_STACK),
      project_url: toAbsoluteUrl(values.project_url),
      start_year: toNullableInt(values.start_year),
      end_year: values.is_ongoing ? null : toNullableInt(values.end_year),
      is_ongoing: values.is_ongoing,
      is_professional: values.is_professional,
    });
  });

  return (
    <Modal
      open={open}
      onClose={onClose}
      title={project ? 'Edit project' : 'Add project'}
      size="lg"
      footer={
        <>
          <Button variant="ghost" size="sm" onClick={onClose} disabled={loading}>
            Cancel
          </Button>
          <Button size="sm" onClick={submit} loading={loading}>
            {project ? 'Save changes' : 'Add project'}
          </Button>
        </>
      }
    >
      <form onSubmit={submit} noValidate className="space-y-4">
        <FormField
          id="project_name"
          label="Project name"
          placeholder="HireFlow"
          error={errors.name}
          registration={register('name')}
        />
        <FormField
          id="project_subtitle"
          label="Subtitle"
          placeholder="AI-assisted job application tracker"
          error={errors.subtitle}
          registration={register('subtitle')}
        />
        <TextareaField
          id="project_description"
          label="Description"
          rows={3}
          placeholder="What it does and what you built."
          error={errors.description}
          registration={register('description')}
        />
        <FormField
          id="tech_stack"
          label="Tech stack"
          placeholder="Django, React, PostgreSQL, Celery"
          hint={`Comma separated · ${techCount}/${MAX_TECH_STACK} used`}
          error={errors.tech_stack}
          registration={register('tech_stack')}
        />
        <FormField
          id="project_url"
          label="Project URL"
          placeholder="github.com/you/project"
          error={errors.project_url}
          registration={register('project_url')}
        />

        <div className="grid gap-4 sm:grid-cols-2">
          <FormField
            id="project_start_year"
            label="Start year"
            type="number"
            placeholder="2025"
            error={errors.start_year}
            registration={register('start_year')}
          />
          {!isOngoing ? (
            <FormField
              id="project_end_year"
              label="End year"
              type="number"
              placeholder="2026"
              error={errors.end_year}
              registration={register('end_year')}
            />
          ) : null}
        </div>

        <div className="flex flex-wrap gap-5">
          <Checkbox id="is_ongoing" label="Still working on it" {...register('is_ongoing')} />
          <Checkbox
            id="is_professional"
            label="Work project (not personal)"
            {...register('is_professional')}
          />
        </div>
      </form>
    </Modal>
  );
}

export function ProjectsStep() {
  const [formOpen, setFormOpen] = useState(false);
  const [editing, setEditing] = useState(null);
  const [pendingDelete, setPendingDelete] = useState(null);

  const { data: projects = [], isLoading } = useProjects();
  const createMutation = useCreateProject();
  const updateMutation = useUpdateProject();
  const deleteMutation = useDeleteProject();
  const reorderMutation = useReorderProjects();

  /* One mutation shared across the list, so only the card the user is working
     on shows a result — two open panels would race for the same response. */
  const suggestMutation = useSuggestProjectPoints();
  const [suggestingId, setSuggestingId] = useState(null);

  /* Child resources expose no PATCH, so appending a point sends the whole
     object back, exactly as the edit form does. */
  const appendPoint = (project, text) => {
    const description = project.description ? `${project.description}\n${text}` : text;
    updateMutation.mutate({
      id: project.id,
      payload: {
        name: project.name,
        subtitle: project.subtitle || '',
        description,
        tech_stack: project.tech_stack || [],
        project_url: project.project_url || '',
        start_year: project.start_year ?? null,
        end_year: project.end_year ?? null,
        is_ongoing: Boolean(project.is_ongoing),
        is_professional: Boolean(project.is_professional),
      },
    });
  };

  const { moveUp, moveDown, isReordering } = useReorder(projects, reorderMutation);

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
      title="Projects"
      description="Optional, but worth 10 points and useful evidence for roles you have not held yet."
      isLoading={isLoading}
      action={
        <Button
          size="sm"
          onClick={() => {
            setEditing(null);
            setFormOpen(true);
          }}
        >
          + Add project
        </Button>
      }
    >
      {projects.length === 0 ? (
        <EmptyState message="No projects yet" hint="One project earns the full 10 points." />
      ) : (
        <div className="space-y-3">
          {projects.map((project, index) => {
            const years = project.is_ongoing
              ? [project.start_year, 'Ongoing'].filter(Boolean).join(' — ')
              : [project.start_year, project.end_year].filter(Boolean).join(' — ');

            return (
              <EntryCard
                key={project.id}
                title={project.name}
                subtitle={project.subtitle}
                meta={[years, project.is_professional ? 'Work project' : 'Personal']
                  .filter(Boolean)
                  .join('  •  ')}
                onEdit={() => {
                  setEditing(project);
                  setFormOpen(true);
                }}
                onDelete={() => setPendingDelete(project)}
                onMoveUp={() => moveUp(index)}
                onMoveDown={() => moveDown(index)}
                canMoveUp={index > 0}
                canMoveDown={index < projects.length - 1}
                reordering={isReordering}
              >
                {project.description ? (
                  <p className="text-sm text-slate-600 dark:text-slate-400">
                    {project.description}
                  </p>
                ) : null}
                {project.tech_stack?.length ? (
                  <div className="mt-2 flex flex-wrap gap-1.5">
                    {project.tech_stack.map((tech) => (
                      <Badge key={tech} variant="brand">
                        {tech}
                      </Badge>
                    ))}
                  </div>
                ) : null}

                {/* Points are appended one at a time rather than replacing the
                    description — a project usually needs several, and the
                    user's own wording is worth keeping. */}
                <SuggestionPanel
                  key={project.id}
                  mutation={suggestMutation}
                  active={suggestingId === project.id}
                  label="Suggest key points"
                  emptyLabel="Draft from a note"
                  needsNote={!project.description}
                  notePlaceholder="What does it do, and what did you decide along the way?"
                  resultKey="points"
                  buildPayload={({ note }) => {
                    setSuggestingId(project.id);
                    return { project_id: project.id, note };
                  }}
                  onApply={(text) => appendPoint(project, text)}
                />
              </EntryCard>
            );
          })}
        </div>
      )}

      <ProjectFormModal
        open={formOpen}
        project={editing}
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
        title="Delete this project?"
        description={pendingDelete ? `"${pendingDelete.name}" will be removed.` : undefined}
      />
    </SectionShell>
  );
}
