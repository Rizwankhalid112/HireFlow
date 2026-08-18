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

  return (...extraKeys) => {
    queryClient.invalidateQueries({ queryKey: cvKeys.profile });
    queryClient.invalidateQueries({ queryKey: cvKeys.completion });
    extraKeys.forEach((key) => queryClient.invalidateQueries({ queryKey: key }));
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
  });

export const useUpdateBullet = () =>
  useSectionMutation({
    mutationFn: ({ experienceId, bulletId, payload }) =>
      cvApi.updateBullet(experienceId, bulletId, payload).then((r) => r.data),
    invalidateKeys: [cvKeys.experiences],
  });

export const useDeleteBullet = () =>
  useSectionMutation({
    mutationFn: ({ experienceId, bulletId }) => cvApi.deleteBullet(experienceId, bulletId),
    invalidateKeys: [cvKeys.experiences],
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
  });

export const useUpdateSkill = () =>
  useSectionMutation({
    mutationFn: ({ id, payload }) => cvApi.updateSkill(id, payload).then((r) => r.data),
    invalidateKeys: [cvKeys.skills],
  });

export const useDeleteSkill = () =>
  useSectionMutation({
    mutationFn: (id) => cvApi.deleteSkill(id),
    invalidateKeys: [cvKeys.skills],
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
