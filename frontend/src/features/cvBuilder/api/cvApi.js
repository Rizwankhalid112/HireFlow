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

/* Clearing the CV. `resetCv()` empties content but keeps the profile, the
   template choice and the account email; `deleteCv()` removes it entirely and
   the user starts again with ensureProfile(). Pass `sections` to clear only
   part of it — the usual case after an import brought in the wrong roles. */
export const resetCv = (sections) =>
  api.post('/cv/profile/reset/', sections ? { sections } : {});

export const deleteCv = () => api.delete('/cv/profile/');

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

// --- Templates, preview, photo -----------------------------------------------
export const listTemplates = () => api.get('/cv/templates/');

/* arraybuffer, not blob: PdfCanvas hands the bytes straight to pdf.js.

   `signal` is React Query's AbortSignal. The preview refetches on every save,
   so a superseded request must be cancelled rather than left to occupy a
   worker producing a render nobody will see. */
export const getPreviewPdf = (templateId, signal) =>
  api.get('/cv/preview/', {
    params: templateId ? { template: templateId } : undefined,
    responseType: 'arraybuffer',
    signal,
  });

export const getPreviewMeta = (templateId) =>
  api.get('/cv/preview/meta/', {
    params: templateId ? { template: templateId } : undefined,
  });

export const uploadPhoto = (file) => {
  const form = new FormData();
  form.append('photo', file);
  // Let the browser set the multipart boundary.
  return api.post('/cv/photo/', form, { headers: { 'Content-Type': undefined } });
};

export const deletePhoto = () => api.delete('/cv/photo/');

// --- CV upload & AI parse ----------------------------------------------------
/* The upload returns immediately with a log id; everything after it is polled.
   Nothing on this path writes to the CV until applyImport is called. */
export const uploadCv = (file, onProgress) => {
  const form = new FormData();
  form.append('file', file);
  return api.post('/cv/upload/', form, {
    // Let the browser set the multipart boundary.
    headers: { 'Content-Type': undefined },
    onUploadProgress: onProgress
      ? (event) => onProgress(event.total ? Math.round((event.loaded * 100) / event.total) : 0)
      : undefined,
  });
};

export const getUploadStatus = (logId) => api.get(`/cv/upload/${logId}/status/`);

/* Re-runs the AI stage on text we already extracted, so a transient upstream
   failure does not cost the user another upload. */
export const retryUploadParse = (logId) => api.post(`/cv/upload/${logId}/retry/`);

/* `choices` is one of keep | replace | merge per section. `answers` supplies
   the required fields the CV did not state, keyed by section then row index. */
export const applyImport = (logId, choices, answers) =>
  api.post(`/cv/upload/${logId}/apply/`, { choices, answers });

// --- AI writing suggestions --------------------------------------------------
/* The only metered endpoints in the app. Every response carries the remaining
   credit allowance so the UI never has to guess. */
export const getSuggestionCredits = () => api.get('/cv/suggest/credits/');

export const suggestBullets = (payload) => api.post('/cv/suggest/bullets/', payload);
export const suggestSummary = (payload) => api.post('/cv/suggest/summary/', payload);
export const suggestSkills = (payload) => api.post('/cv/suggest/skills/', payload);
export const suggestProjectPoints = (payload) => api.post('/cv/suggest/projects/', payload);
export const suggestTitle = (payload) => api.post('/cv/suggest/title/', payload);

/* Records which variant was taken. Accept rate per section is the only honest
   measure of whether this feature works, and it cannot be reconstructed later. */
export const acceptSuggestion = (logId, index) =>
  api.post(`/cv/suggest/${logId}/accept/`, { index });

/* Public URL for a template's sample thumbnail. Rendered from fixed demo data
   with no auth, so it can be used directly as an <img src> — a Bearer token
   cannot be attached to an image request. */
export const templateSampleUrl = (templateId) => {
  const base = import.meta.env.VITE_API_URL || 'http://localhost/api';
  return `${base.replace(/\/$/, '')}/cv/templates/${templateId}/sample/`;
};

// --- Module 1: job match -----------------------------------------------------
/* One call returns keyword analysis and a cover letter together — they come from
   the same reading of the CV and the posting, so splitting them would mean
   sending both documents twice. */
export const listCvSources = () => api.get('/cv/job-match/sources/');

export const runJobMatch = (payload) => api.post('/cv/job-match/', payload);

export const listJobMatches = () => api.get('/cv/job-match/');

export const getJobMatch = (id) => api.get(`/cv/job-match/${id}/`);

export const deleteJobMatch = (id) => api.delete(`/cv/job-match/${id}/`);
