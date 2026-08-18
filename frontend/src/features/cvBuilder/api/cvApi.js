import api from '@/lib/axios';

/*
 * Mirrors backend/apps/cv_builder/urls.py exactly.
 * Child resources expose PUT and DELETE only — there is no per-item GET and no
 * PATCH, so edit forms must send the complete object.
 */

// --- Profile -----------------------------------------------------------------
// POST is idempotent: 201 when created, 200 when it already existed.
export const ensureProfile = () => api.post('/cv/profile/');
export const getProfile = () => api.get('/cv/profile/');
export const updateProfile = (payload) => api.put('/cv/profile/', payload);
export const patchProfile = (payload) => api.patch('/cv/profile/', payload);
export const getCompletion = () => api.get('/cv/profile/completion/');

// --- Work experience ---------------------------------------------------------
export const listExperiences = () => api.get('/cv/work-experience/');
export const createExperience = (payload) => api.post('/cv/work-experience/', payload);
export const updateExperience = (id, payload) => api.put(`/cv/work-experience/${id}/`, payload);
export const deleteExperience = (id) => api.delete(`/cv/work-experience/${id}/`);
export const reorderExperiences = (orderedIds) =>
  api.patch('/cv/work-experience/reorder/', { ordered_ids: orderedIds });

// --- Bullets (nested under one experience) -----------------------------------
export const listBullets = (experienceId) =>
  api.get(`/cv/work-experience/${experienceId}/bullets/`);
export const createBullet = (experienceId, payload) =>
  api.post(`/cv/work-experience/${experienceId}/bullets/`, payload);
export const updateBullet = (experienceId, bulletId, payload) =>
  api.put(`/cv/work-experience/${experienceId}/bullets/${bulletId}/`, payload);
export const deleteBullet = (experienceId, bulletId) =>
  api.delete(`/cv/work-experience/${experienceId}/bullets/${bulletId}/`);
export const reorderBullets = (experienceId, orderedIds) =>
  api.patch(`/cv/work-experience/${experienceId}/bullets/reorder/`, { ordered_ids: orderedIds });

// --- Education ---------------------------------------------------------------
export const listEducation = () => api.get('/cv/education/');
export const createEducation = (payload) => api.post('/cv/education/', payload);
export const updateEducation = (id, payload) => api.put(`/cv/education/${id}/`, payload);
export const deleteEducation = (id) => api.delete(`/cv/education/${id}/`);
export const reorderEducation = (orderedIds) =>
  api.patch('/cv/education/reorder/', { ordered_ids: orderedIds });

// --- Skills ------------------------------------------------------------------
export const searchCanonicalSkills = (q) =>
  api.get('/cv/skills/search/', { params: { q } });
export const listSkills = () => api.get('/cv/skills/');
export const createSkill = (payload) => api.post('/cv/skills/', payload);
export const updateSkill = (id, payload) => api.put(`/cv/skills/${id}/`, payload);
export const deleteSkill = (id) => api.delete(`/cv/skills/${id}/`);
export const bulkAddSkills = (skills) => api.post('/cv/skills/bulk-add/', { skills });
export const reorderSkills = (orderedIds) =>
  api.patch('/cv/skills/reorder/', { ordered_ids: orderedIds });

// --- Projects ----------------------------------------------------------------
export const listProjects = () => api.get('/cv/projects/');
export const createProject = (payload) => api.post('/cv/projects/', payload);
export const updateProject = (id, payload) => api.put(`/cv/projects/${id}/`, payload);
export const deleteProject = (id) => api.delete(`/cv/projects/${id}/`);
export const reorderProjects = (orderedIds) =>
  api.patch('/cv/projects/reorder/', { ordered_ids: orderedIds });

// --- Certifications ----------------------------------------------------------
export const listCertifications = () => api.get('/cv/certifications/');
export const createCertification = (payload) => api.post('/cv/certifications/', payload);
export const updateCertification = (id, payload) => api.put(`/cv/certifications/${id}/`, payload);
export const deleteCertification = (id) => api.delete(`/cv/certifications/${id}/`);
export const reorderCertifications = (orderedIds) =>
  api.patch('/cv/certifications/reorder/', { ordered_ids: orderedIds });

// --- Languages ---------------------------------------------------------------
export const listLanguages = () => api.get('/cv/languages/');
export const createLanguage = (payload) => api.post('/cv/languages/', payload);
export const updateLanguage = (id, payload) => api.put(`/cv/languages/${id}/`, payload);
export const deleteLanguage = (id) => api.delete(`/cv/languages/${id}/`);
export const reorderLanguages = (orderedIds) =>
  api.patch('/cv/languages/reorder/', { ordered_ids: orderedIds });
