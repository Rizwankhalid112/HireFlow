import { useEffect, useRef } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';

import { extractApiError } from '@/utils/extractApiError';

import * as cvApi from './cvApi';

export const cvKeys = {
  all: ['cv'],
  profile: ['cv', 'profile'],
  completion: ['cv', 'completion'],
  experiences: ['cv', 'work-experience'],
  bullets: (experienceId) => ['cv', 'work-experience', experienceId, 'bullets'],
  education: ['cv', 'education'],
  skills: ['cv', 'skills'],
  skillSearch: (q) => ['cv', 'skills', 'search', q],
  projects: ['cv', 'projects'],
  certifications: ['cv', 'certifications'],
  languages: ['cv', 'languages'],
};

/* Any section write changes completion_score, so the profile and completion
   queries are refreshed alongside the section that actually changed. */
function useCvInvalidator() {
  const queryClient = useQueryClient();

  /* refetchType 'all' matters here: the default ('active') skips any observer
     that is disabled or unmounted, so the completion bar could keep showing a
     stale score after a write on a step whose query was briefly inactive. */
  return (...extraKeys) => {
    const refetch = (queryKey) =>
      queryClient.invalidateQueries({ queryKey, refetchType: 'all' });

    refetch(cvKeys.profile);
    refetch(cvKeys.completion);
    extraKeys.forEach(refetch);
  };
}

function onMutationError(error) {
  toast.error(extractApiError(error));
}

/* Wraps the create/update/delete/reorder trio for one section so every list
   endpoint behaves identically. */
function useSectionMutation({ mutationFn, invalidateKeys, successMessage }) {
  const invalidate = useCvInvalidator();

  return useMutation({
    mutationFn,
    onSuccess: () => {
      invalidate(...invalidateKeys);
      if (successMessage) {
        toast.success(successMessage);
      }
    },
    onError: onMutationError,
  });
}

// --- Profile -----------------------------------------------------------------

/* GET /cv/profile/ returns 404 until a shell exists, so the builder POSTs first
   (idempotent per the spec's server-first creation rule) and then reads. */
export function useEnsureProfile() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: () => cvApi.ensureProfile().then((response) => response.data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: cvKeys.profile });
    },
    onError: onMutationError,
  });
}

export function useCvProfile({ enabled = true } = {}) {
  return useQuery({
    queryKey: cvKeys.profile,
    queryFn: () => cvApi.getProfile().then((response) => response.data),
    enabled,
    retry: false,
  });
}

export function useCompletion({ enabled = true } = {}) {
  return useQuery({
    queryKey: cvKeys.completion,
    queryFn: () => cvApi.getCompletion().then((response) => response.data),
    enabled,
    retry: false,
  });
}

export function useUpdateProfile() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (payload) => cvApi.updateProfile(payload).then((response) => response.data),
    onSuccess: (data) => {
      queryClient.setQueryData(cvKeys.profile, data);
      queryClient.invalidateQueries({ queryKey: cvKeys.completion });
    },
    onError: onMutationError,
  });
}

/* Used by the autosave hook — deliberately silent on success. */
export function usePatchProfile() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (payload) => cvApi.patchProfile(payload).then((response) => response.data),
    onSuccess: (data) => {
      queryClient.setQueryData(cvKeys.profile, data);
      queryClient.invalidateQueries({ queryKey: cvKeys.completion });
    },
  });
}

// --- Work experience ---------------------------------------------------------

export function useExperiences({ enabled = true } = {}) {
  return useQuery({
    queryKey: cvKeys.experiences,
    queryFn: () => cvApi.listExperiences().then((response) => response.data),
    enabled,
  });
}

export const useCreateExperience = () =>
  useSectionMutation({
    mutationFn: (payload) => cvApi.createExperience(payload).then((r) => r.data),
    invalidateKeys: [cvKeys.experiences],
    successMessage: 'Experience added.',
  });

export const useUpdateExperience = () =>
  useSectionMutation({
    mutationFn: ({ id, payload }) => cvApi.updateExperience(id, payload).then((r) => r.data),
    invalidateKeys: [cvKeys.experiences],
    successMessage: 'Experience updated.',
  });

export const useDeleteExperience = () =>
  useSectionMutation({
    mutationFn: (id) => cvApi.deleteExperience(id),
    invalidateKeys: [cvKeys.experiences],
    successMessage: 'Experience removed.',
  });

export const useReorderExperiences = () =>
  useSectionMutation({
    mutationFn: (orderedIds) => cvApi.reorderExperiences(orderedIds).then((r) => r.data),
    invalidateKeys: [cvKeys.experiences],
  });

// --- Bullets -----------------------------------------------------------------
// Bullets come back nested on the experience list, so writes refresh that list.

export const useCreateBullet = () =>
  useSectionMutation({
    mutationFn: ({ experienceId, payload }) =>
      cvApi.createBullet(experienceId, payload).then((r) => r.data),
    invalidateKeys: [cvKeys.experiences],
    successMessage: 'Bullet added.',
  });

export const useUpdateBullet = () =>
  useSectionMutation({
    mutationFn: ({ experienceId, bulletId, payload }) =>
      cvApi.updateBullet(experienceId, bulletId, payload).then((r) => r.data),
    invalidateKeys: [cvKeys.experiences],
    successMessage: 'Bullet updated.',
  });

export const useDeleteBullet = () =>
  useSectionMutation({
    mutationFn: ({ experienceId, bulletId }) => cvApi.deleteBullet(experienceId, bulletId),
    invalidateKeys: [cvKeys.experiences],
    successMessage: 'Bullet removed.',
  });

export const useReorderBullets = () =>
  useSectionMutation({
    mutationFn: ({ experienceId, orderedIds }) =>
      cvApi.reorderBullets(experienceId, orderedIds).then((r) => r.data),
    invalidateKeys: [cvKeys.experiences],
  });

// --- Education ---------------------------------------------------------------

export function useEducation({ enabled = true } = {}) {
  return useQuery({
    queryKey: cvKeys.education,
    queryFn: () => cvApi.listEducation().then((response) => response.data),
    enabled,
  });
}

export const useCreateEducation = () =>
  useSectionMutation({
    mutationFn: (payload) => cvApi.createEducation(payload).then((r) => r.data),
    invalidateKeys: [cvKeys.education],
    successMessage: 'Education added.',
  });

export const useUpdateEducation = () =>
  useSectionMutation({
    mutationFn: ({ id, payload }) => cvApi.updateEducation(id, payload).then((r) => r.data),
    invalidateKeys: [cvKeys.education],
    successMessage: 'Education updated.',
  });

export const useDeleteEducation = () =>
  useSectionMutation({
    mutationFn: (id) => cvApi.deleteEducation(id),
    invalidateKeys: [cvKeys.education],
    successMessage: 'Education removed.',
  });

export const useReorderEducation = () =>
  useSectionMutation({
    mutationFn: (orderedIds) => cvApi.reorderEducation(orderedIds).then((r) => r.data),
    invalidateKeys: [cvKeys.education],
  });

// --- Skills ------------------------------------------------------------------

export function useSkills({ enabled = true } = {}) {
  return useQuery({
    queryKey: cvKeys.skills,
    queryFn: () => cvApi.listSkills().then((response) => response.data),
    enabled,
  });
}

/* Autocomplete. The caller debounces `q`; an empty query returns [] server-side. */
export function useSkillSearch(q) {
  const term = (q || '').trim();

  return useQuery({
    queryKey: cvKeys.skillSearch(term),
    queryFn: () => cvApi.searchCanonicalSkills(term).then((response) => response.data),
    enabled: term.length > 0,
    staleTime: 5 * 60 * 1000,
  });
}

export const useCreateSkill = () =>
  useSectionMutation({
    mutationFn: (payload) => cvApi.createSkill(payload).then((r) => r.data),
    invalidateKeys: [cvKeys.skills],
    successMessage: 'Skill added.',
  });

export const useUpdateSkill = () =>
  useSectionMutation({
    mutationFn: ({ id, payload }) => cvApi.updateSkill(id, payload).then((r) => r.data),
    invalidateKeys: [cvKeys.skills],
    successMessage: 'Skill updated.',
  });

export const useDeleteSkill = () =>
  useSectionMutation({
    mutationFn: (id) => cvApi.deleteSkill(id),
    invalidateKeys: [cvKeys.skills],
    successMessage: 'Skill removed.',
  });

export const useReorderSkills = () =>
  useSectionMutation({
    mutationFn: (orderedIds) => cvApi.reorderSkills(orderedIds).then((r) => r.data),
    invalidateKeys: [cvKeys.skills],
  });

export const useBulkAddSkills = () =>
  useSectionMutation({
    mutationFn: (skills) => cvApi.bulkAddSkills(skills).then((r) => r.data),
    invalidateKeys: [cvKeys.skills],
  });

// --- Projects ----------------------------------------------------------------

export function useProjects({ enabled = true } = {}) {
  return useQuery({
    queryKey: cvKeys.projects,
    queryFn: () => cvApi.listProjects().then((response) => response.data),
    enabled,
  });
}

export const useCreateProject = () =>
  useSectionMutation({
    mutationFn: (payload) => cvApi.createProject(payload).then((r) => r.data),
    invalidateKeys: [cvKeys.projects],
    successMessage: 'Project added.',
  });

export const useUpdateProject = () =>
  useSectionMutation({
    mutationFn: ({ id, payload }) => cvApi.updateProject(id, payload).then((r) => r.data),
    invalidateKeys: [cvKeys.projects],
    successMessage: 'Project updated.',
  });

export const useDeleteProject = () =>
  useSectionMutation({
    mutationFn: (id) => cvApi.deleteProject(id),
    invalidateKeys: [cvKeys.projects],
    successMessage: 'Project removed.',
  });

export const useReorderProjects = () =>
  useSectionMutation({
    mutationFn: (orderedIds) => cvApi.reorderProjects(orderedIds).then((r) => r.data),
    invalidateKeys: [cvKeys.projects],
  });

// --- Certifications ----------------------------------------------------------

export function useCertifications({ enabled = true } = {}) {
  return useQuery({
    queryKey: cvKeys.certifications,
    queryFn: () => cvApi.listCertifications().then((response) => response.data),
    enabled,
  });
}

export const useCreateCertification = () =>
  useSectionMutation({
    mutationFn: (payload) => cvApi.createCertification(payload).then((r) => r.data),
    invalidateKeys: [cvKeys.certifications],
    successMessage: 'Certification added.',
  });

export const useUpdateCertification = () =>
  useSectionMutation({
    mutationFn: ({ id, payload }) => cvApi.updateCertification(id, payload).then((r) => r.data),
    invalidateKeys: [cvKeys.certifications],
    successMessage: 'Certification updated.',
  });

export const useDeleteCertification = () =>
  useSectionMutation({
    mutationFn: (id) => cvApi.deleteCertification(id),
    invalidateKeys: [cvKeys.certifications],
    successMessage: 'Certification removed.',
  });

export const useReorderCertifications = () =>
  useSectionMutation({
    mutationFn: (orderedIds) => cvApi.reorderCertifications(orderedIds).then((r) => r.data),
    invalidateKeys: [cvKeys.certifications],
  });

// --- Languages ---------------------------------------------------------------

export function useLanguages({ enabled = true } = {}) {
  return useQuery({
    queryKey: cvKeys.languages,
    queryFn: () => cvApi.listLanguages().then((response) => response.data),
    enabled,
  });
}

export const useCreateLanguage = () =>
  useSectionMutation({
    mutationFn: (payload) => cvApi.createLanguage(payload).then((r) => r.data),
    invalidateKeys: [cvKeys.languages],
    successMessage: 'Language added.',
  });

export const useUpdateLanguage = () =>
  useSectionMutation({
    mutationFn: ({ id, payload }) => cvApi.updateLanguage(id, payload).then((r) => r.data),
    invalidateKeys: [cvKeys.languages],
    successMessage: 'Language updated.',
  });

export const useDeleteLanguage = () =>
  useSectionMutation({
    mutationFn: (id) => cvApi.deleteLanguage(id),
    invalidateKeys: [cvKeys.languages],
    successMessage: 'Language removed.',
  });

export const useReorderLanguages = () =>
  useSectionMutation({
    mutationFn: (orderedIds) => cvApi.reorderLanguages(orderedIds).then((r) => r.data),
    invalidateKeys: [cvKeys.languages],
  });

// --- Templates, preview, photo -----------------------------------------------

cvKeys.templates = ['cv', 'templates'];
cvKeys.preview = (templateId) => ['cv', 'preview', templateId ?? 'saved'];
cvKeys.previewMeta = (templateId) => ['cv', 'preview', 'meta', templateId ?? 'saved'];

export function useTemplates() {
  return useQuery({
    queryKey: cvKeys.templates,
    queryFn: () => cvApi.listTemplates().then((response) => response.data),
    staleTime: Infinity, // static registry
  });
}

/* Keyed by template AND content stamp so switching templates or editing the CV
   fetches a fresh render, while flipping back to a seen template is instant. */
export function usePreviewPdf(templateId, contentStamp, { enabled = true } = {}) {
  return useQuery({
    queryKey: [...cvKeys.preview(templateId), contentStamp],
    queryFn: () => cvApi.getPreviewPdf(templateId).then((response) => response.data),
    enabled,
    retry: false,
    staleTime: 5 * 60 * 1000,
  });
}

/* Currently unused, and deliberately so: the preview pane gets its page count
   from pdf.js once it has parsed the document it already downloaded, and
   compares it against `max_pages` from the template registry. Calling this
   would mean a second server round-trip per refresh for a number we hold.
   Kept because cvApi mirrors urls.py 1:1 and the endpoint is still live. */
export function usePreviewMeta(templateId, contentStamp, { enabled = true } = {}) {
  return useQuery({
    queryKey: [...cvKeys.previewMeta(templateId), contentStamp],
    queryFn: () => cvApi.getPreviewMeta(templateId).then((response) => response.data),
    enabled,
    retry: false,
  });
}

// --- AI writing suggestions --------------------------------------------------

cvKeys.aiCredits = ['cv', 'ai', 'credits'];

export function useSuggestionCredits() {
  return useQuery({
    queryKey: cvKeys.aiCredits,
    queryFn: () => cvApi.getSuggestionCredits().then((response) => response.data),
    staleTime: 60 * 1000,
    retry: false,
  });
}

/* One hook per section, all sharing the same shape so SuggestionPanel does not
   need to know which section it is rendering.

   Deliberately silent on success — the suggestions are the feedback, and a
   toast on top of three cards appearing is noise. Errors still toast, except
   for 429 and 503 which the panel renders inline because they are states the
   user can act on rather than failures. */
function useSuggestionMutation(mutationFn) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn,
    onSuccess: (data) => {
      if (data?.credits) {
        queryClient.setQueryData(cvKeys.aiCredits, (previous) => ({
          ...(previous ?? {}),
          ...data.credits,
          enabled: previous?.enabled ?? true,
        }));
      }
    },
    onError: (error) => {
      const status = error?.response?.status;
      if (status !== 429 && status !== 503) {
        toast.error(extractApiError(error));
      }
      if (status === 429) {
        queryClient.invalidateQueries({ queryKey: cvKeys.aiCredits });
      }
    },
  });
}

export const useSuggestBullets = () =>
  useSuggestionMutation((payload) => cvApi.suggestBullets(payload).then((r) => r.data));

export const useSuggestSummary = () =>
  useSuggestionMutation((payload) => cvApi.suggestSummary(payload ?? {}).then((r) => r.data));

export const useSuggestSkills = () =>
  useSuggestionMutation((payload) => cvApi.suggestSkills(payload ?? {}).then((r) => r.data));

export const useSuggestProjectPoints = () =>
  useSuggestionMutation((payload) => cvApi.suggestProjectPoints(payload).then((r) => r.data));

export const useSuggestTitle = () =>
  useSuggestionMutation((payload) => cvApi.suggestTitle(payload ?? {}).then((r) => r.data));

/* Fire-and-forget: a failed accept-log must never block the user from using the
   suggestion they just picked. */
export function useAcceptSuggestion() {
  return useMutation({
    mutationFn: ({ logId, index }) => cvApi.acceptSuggestion(logId, index),
    onError: () => {},
  });
}

export function useUploadPhoto() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (file) => cvApi.uploadPhoto(file).then((r) => r.data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: cvKeys.profile });
      queryClient.invalidateQueries({ queryKey: ['cv', 'preview'] });
      toast.success('Photo updated.');
    },
    onError: onMutationError,
  });
}

export function useDeletePhoto() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: () => cvApi.deletePhoto(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: cvKeys.profile });
      queryClient.invalidateQueries({ queryKey: ['cv', 'preview'] });
      toast.success('Photo removed.');
    },
    onError: onMutationError,
  });
}

// --- CV upload & AI parse ----------------------------------------------------

cvKeys.uploadStatus = (logId) => ['cv', 'upload', logId, 'status'];

/* Terminal in the backend's sense: no further work happens without the user
   acting, so polling stops here. */
export const TERMINAL_UPLOAD_STATUSES = ['success', 'partial', 'failed', 'scanned'];

/* Give up after this long even if the status never goes terminal. The backend's
   stuck-upload sweeper should always beat this, but a client that polls forever
   because a sweep did not run is a worse failure than one that says so. */
const POLL_CEILING_MS = 3 * 60 * 1000;
const POLL_INTERVAL_MS = 2000;

export function useUploadCv() {
  return useMutation({
    mutationFn: ({ file, onProgress }) => cvApi.uploadCv(file, onProgress).then((r) => r.data),
    onError: (error) => {
      // 429 is the monthly cap and is rendered inline by the dropzone — it is a
      // state the user can act on next month, not a failure of this upload.
      if (error?.response?.status !== 429) {
        toast.error(extractApiError(error));
      }
    },
  });
}

/* Polls one upload until it reaches a terminal status.

   `enabled` is what stops a mounted-but-idle builder polling forever; the
   interval returns false once terminal so React Query stops on its own. */
export function useUploadStatus(logId, { enabled = true } = {}) {
  const startedAt = useRef(null);

  useEffect(() => {
    startedAt.current = logId ? Date.now() : null;
  }, [logId]);

  return useQuery({
    queryKey: cvKeys.uploadStatus(logId),
    queryFn: () => cvApi.getUploadStatus(logId).then((response) => response.data),
    enabled: Boolean(logId) && enabled,
    refetchInterval: (query) => {
      const data = query.state.data;
      if (data?.is_terminal) {
        return false;
      }
      if (startedAt.current && Date.now() - startedAt.current > POLL_CEILING_MS) {
        return false;
      }
      return POLL_INTERVAL_MS;
    },
    // The status is the point; a cached one is never useful.
    staleTime: 0,
    retry: false,
  });
}

export function useRetryUploadParse() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (logId) => cvApi.retryUploadParse(logId).then((r) => r.data),
    onSuccess: (data) => {
      // Put the row back into a non-terminal state immediately so polling
      // resumes without waiting for the next interval.
      queryClient.setQueryData(cvKeys.uploadStatus(data.log_id), (previous) => ({
        ...(previous ?? {}),
        status: 'parsing',
        is_terminal: false,
        error_message: null,
      }));
    },
    onError: onMutationError,
  });
}

/* Applying is the only thing on this path that touches the CV, so it
   invalidates everything — including the preview, which repaints itself with
   the imported content. */
export function useApplyImport() {
  const invalidate = useCvInvalidator();

  return useMutation({
    mutationFn: ({ logId, choices, answers }) =>
      cvApi.applyImport(logId, choices, answers).then((r) => r.data),
    onSuccess: (data) => {
      invalidate(
        cvKeys.experiences,
        cvKeys.education,
        cvKeys.skills,
        cvKeys.projects,
        cvKeys.certifications,
        cvKeys.languages,
      );

      const skipped = data?.skipped?.length ?? 0;
      if (skipped) {
        toast.warning(
          `Imported ${data.imported} item${data.imported === 1 ? '' : 's'}. ` +
            `${skipped} need${skipped === 1 ? 's' : ''} your attention.`,
        );
      } else {
        toast.success(`Imported ${data.imported} item${data.imported === 1 ? '' : 's'} from your CV.`);
      }
    },
    onError: onMutationError,
  });
}

// --- Clearing the CV ---------------------------------------------------------

/* Both wipe most of what the builder shows, so they invalidate everything
   rather than trying to be surgical — including the preview, which must not
   keep displaying a CV that no longer exists. */
function useClearingMutation(mutationFn, onDone) {
  const invalidate = useCvInvalidator();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn,
    onSuccess: (data) => {
      invalidate(
        cvKeys.experiences,
        cvKeys.education,
        cvKeys.skills,
        cvKeys.projects,
        cvKeys.certifications,
        cvKeys.languages,
      );
      queryClient.invalidateQueries({ queryKey: cvKeys.all, refetchType: 'all' });
      onDone?.(data);
    },
    onError: onMutationError,
  });
}

export function useResetCv() {
  return useClearingMutation(
    (sections) => cvApi.resetCv(sections).then((r) => r.data),
    (data) => {
      const total = data?.total_cleared ?? 0;
      // Says what actually happened rather than "done", so the user can check
      // it against what they expected to lose.
      toast.success(
        total > 0
          ? `Cleared ${total} item${total === 1 ? '' : 's'}.`
          : 'Nothing to clear — your CV was already empty.',
      );
    },
  );
}

export function useDeleteCv() {
  return useClearingMutation(
    () => cvApi.deleteCv().then((r) => r.data),
    () => toast.success('Your CV has been deleted.'),
  );
}

// --- Module 1: job match -----------------------------------------------------

cvKeys.cvSources = ['cv', 'job-match', 'sources'];
cvKeys.jobMatches = ['cv', 'job-match'];
cvKeys.jobMatch = (id) => ['cv', 'job-match', id];

export function useCvSources() {
  return useQuery({
    queryKey: cvKeys.cvSources,
    queryFn: () => cvApi.listCvSources().then((r) => r.data),
    staleTime: 30 * 1000,
    retry: false,
  });
}

export function useJobMatches() {
  return useQuery({
    queryKey: cvKeys.jobMatches,
    queryFn: () => cvApi.listJobMatches().then((r) => r.data),
    retry: false,
  });
}

export function useJobMatch(id) {
  return useQuery({
    queryKey: cvKeys.jobMatch(id),
    queryFn: () => cvApi.getJobMatch(id).then((r) => r.data),
    enabled: Boolean(id),
    retry: false,
  });
}

/* The most expensive call in the app, so the UI must never fire it twice for one
   click and must show the remaining allowance honestly. 429 and 503 are rendered
   inline rather than toasted — both are states the user can act on. */
export function useRunJobMatch() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (payload) => cvApi.runJobMatch(payload).then((r) => r.data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: cvKeys.jobMatches });
      queryClient.invalidateQueries({ queryKey: cvKeys.cvSources });
    },
    onError: (error) => {
      const status = error?.response?.status;
      if (status !== 429 && status !== 503 && status !== 400) {
        toast.error(extractApiError(error));
      }
    },
  });
}

export function useDeleteJobMatch() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id) => cvApi.deleteJobMatch(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: cvKeys.jobMatches });
      toast.success('Removed.');
    },
    onError: onMutationError,
  });
}
