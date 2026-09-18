import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { toast } from 'sonner';

import {
  forgotPassword,
  getProfile,
  googleLogin,
  login,
  logout,
  register,
  resetPassword,
  verifyEmail,
} from '@/features/auth/api/authApi';
import { useAppDispatch, useAppSelector } from '@/hooks/useAppSelector';
import { setCredentials, logout as logoutAction } from '@/store/slices/authSlice';
import { extractApiError } from '@/utils/extractApiError';

const FORGOT_PASSWORD_MESSAGE = "If that email is registered, you'll receive a link.";

export function useLogin() {
  const dispatch = useAppDispatch();
  const navigate = useNavigate();

  return useMutation({
    mutationFn: login,
    onSuccess: ({ data }) => {
      dispatch(setCredentials(data.access));
      toast.success('Welcome back!');
      navigate('/home');
    },
    onError: (error) => {
      toast.error(extractApiError(error));
    },
  });
}

export function useRegister() {
  const navigate = useNavigate();

  return useMutation({
    mutationFn: register,
    onSuccess: ({ data }) => {
      toast.success(data.message || 'Check your email to verify your account.');
      navigate('/login');
    },
    onError: (error) => {
      toast.error(extractApiError(error));
    },
  });
}

export function useLogout() {
  const dispatch = useAppDispatch();
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: logout,
    onSettled: () => {
      dispatch(logoutAction());
      queryClient.clear();
      navigate('/login');
    },
  });
}

export function useForgotPassword() {
  return useMutation({
    mutationFn: forgotPassword,
    onSuccess: () => {
      toast.success(FORGOT_PASSWORD_MESSAGE);
    },
    onError: (error) => {
      toast.error(extractApiError(error));
    },
  });
}

export function useResetPassword() {
  const navigate = useNavigate();

  return useMutation({
    mutationFn: resetPassword,
    onSuccess: ({ data }) => {
      toast.success(data.message || 'Password reset successfully.');
      navigate('/login');
    },
    onError: (error) => {
      toast.error(extractApiError(error));
    },
  });
}

export function useVerifyEmail() {
  const dispatch = useAppDispatch();
  const navigate = useNavigate();

  return useMutation({
    mutationFn: verifyEmail,
    onSuccess: ({ data }) => {
      dispatch(setCredentials(data.access));
      toast.success('Email verified successfully.');
      navigate('/home');
    },
    onError: (error) => {
      toast.error(extractApiError(error));
    },
  });
}

export function useGoogleLogin() {
  const dispatch = useAppDispatch();
  const navigate = useNavigate();

  return useMutation({
    mutationFn: googleLogin,
    onSuccess: ({ data }) => {
      dispatch(setCredentials(data.access));
      toast.success('Signed in with Google.');
      navigate('/home');
    },
    onError: (error) => {
      toast.error(extractApiError(error));
    },
  });
}

export function useProfile() {
  const isAuthenticated = useAppSelector((state) => state.auth.isAuthenticated);

  return useQuery({
    queryKey: ['profile'],
    queryFn: async () => {
      const { data } = await getProfile();
      return data;
    },
    enabled: isAuthenticated,
  });
}
