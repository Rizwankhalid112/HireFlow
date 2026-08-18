import { z } from 'zod';

export const loginSchema = z.object({
  email: z.string().min(1, 'Email is required').email('Enter a valid email'),
  password: z.string().min(1, 'Password is required'),
});

export const registerSchema = z
  .object({
    email: z.string().min(1, 'Email is required').email('Enter a valid email'),
    full_name: z.string().min(1, 'Full name is required').max(150, 'Name is too long'),
    password: z.string().min(8, 'Password must be at least 8 characters'),
    password2: z.string().min(8, 'Please confirm your password'),
  })
  .refine((data) => data.password === data.password2, {
    message: 'Passwords do not match',
    path: ['password2'],
  });

export const forgotPasswordSchema = z.object({
  email: z.string().min(1, 'Email is required').email('Enter a valid email'),
});

export const resetPasswordSchema = z
  .object({
    new_password: z.string().min(8, 'Password must be at least 8 characters'),
    new_password2: z.string().min(8, 'Please confirm your password'),
  })
  .refine((data) => data.new_password === data.new_password2, {
    message: 'Passwords do not match',
    path: ['new_password2'],
  });
