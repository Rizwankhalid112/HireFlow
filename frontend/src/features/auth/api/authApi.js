import api from '@/lib/axios';

export function register(payload) {
  return api.post('/auth/register/', payload);
}

export function login(payload) {
  return api.post('/auth/login/', payload);
}

export function logout() {
  return api.post('/auth/logout/');
}

export function forgotPassword(payload) {
  return api.post('/auth/forgot-password/', payload);
}

export function resetPassword(payload) {
  return api.post('/auth/reset-password/', payload);
}

export function verifyEmail(token) {
  return api.get(`/auth/verify-email/${token}/`);
}

export function getProfile() {
  return api.get('/users/profile/');
}

export function googleLogin(payload) {
  return api.post('/auth/google/', payload);
}
