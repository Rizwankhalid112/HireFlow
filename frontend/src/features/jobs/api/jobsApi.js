import api from '@/lib/axios';

/* Mirrors backend/apps/jobs/urls.py.
   The list is always paginated — the table is expected to hold millions of rows,
   so there is no endpoint that returns everything. */
export const listJobs = (params) => api.get('/jobs/', { params });

export const getJob = (id) => api.get(`/jobs/${id}/`);

export const deleteJob = (id) => api.delete(`/jobs/${id}/`);

export const getJobStats = () => api.get('/jobs/stats/');
