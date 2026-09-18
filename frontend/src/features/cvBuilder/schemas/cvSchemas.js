import { z } from 'zod';

import { MAX_TECH_STACK } from '../constants';

/* Mirrors backend validation so the user sees errors before a round trip.
   The backend stays authoritative — these only catch the common cases. */

const CURRENT_YEAR = new Date().getFullYear();
const MIN_YEAR = 1950;
const MAX_YEAR = CURRENT_YEAR + 10;

const optionalText = z.string().trim().optional().or(z.literal(''));

const yearRequired = z
  .string()
  .min(1, 'Year is required')
  .refine((value) => {
    const year = Number(value);
    return Number.isInteger(year) && year >= MIN_YEAR && year <= MAX_YEAR;
  }, `Enter a year between ${MIN_YEAR} and ${MAX_YEAR}`);

const yearOptional = z
  .string()
  .optional()
  .or(z.literal(''))
  .refine((value) => {
    if (!value) return true;
    const year = Number(value);
    return Number.isInteger(year) && year >= MIN_YEAR && year <= MAX_YEAR;
  }, `Enter a year between ${MIN_YEAR} and ${MAX_YEAR}`);

const urlOptional = z
  .string()
  .trim()
  .optional()
  .or(z.literal(''))
  .refine(
    (value) => !value || /^([a-z]+:\/\/|\/\/)?[\w-]+(\.[\w-]+)+/i.test(value),
    'Enter a valid URL',
  );

export const profileSchema = z.object({
  full_name: z.string().trim().max(100, 'Maximum 100 characters').optional().or(z.literal('')),
  professional_title: z
    .string()
    .trim()
    .max(150, 'Maximum 150 characters')
    .optional()
    .or(z.literal('')),
  email: z
    .string()
    .trim()
    .optional()
    .or(z.literal(''))
    .refine((value) => !value || z.string().email().safeParse(value).success, 'Enter a valid email'),
  phone: z.string().trim().max(30, 'Maximum 30 characters').optional().or(z.literal('')),
  city: z.string().trim().max(100, 'Maximum 100 characters').optional().or(z.literal('')),
  country: z.string().trim().max(100, 'Maximum 100 characters').optional().or(z.literal('')),
  // Matches CVProfileWriteSerializer.validate_linkedin_url.
  linkedin_url: urlOptional.refine(
    (value) => !value || value.toLowerCase().includes('linkedin.com'),
    'Must be a LinkedIn URL',
  ),
  github_url: urlOptional,
  portfolio_url: urlOptional,
  summary: optionalText,
});

export const experienceSchema = z
  .object({
    company_name: z.string().trim().min(1, 'Company name is required').max(200),
    role_title: z.string().trim().min(1, 'Role title is required').max(200),
    employment_type: optionalText,
    location: optionalText,
    location_type: optionalText,
    start_month: optionalText,
    start_year: yearRequired,
    end_month: optionalText,
    end_year: yearOptional,
    is_current: z.boolean().default(false),
  })
  .refine(
    (data) => {
      if (data.is_current || !data.end_year || !data.start_year) return true;
      return Number(data.end_year) >= Number(data.start_year);
    },
    { message: 'End year cannot be before start year', path: ['end_year'] },
  );

// Matches WorkBulletSerializer.validate_text.
export const bulletSchema = z.object({
  text: z.string().trim().min(10, 'Bullet must be at least 10 characters'),
});

export const educationSchema = z
  .object({
    institution: z.string().trim().min(1, 'Institution is required').max(300),
    degree_type: optionalText,
    field_of_study: optionalText,
    cgpa: z
      .string()
      .optional()
      .or(z.literal(''))
      .refine((value) => !value || !Number.isNaN(Number(value)), 'Enter a number')
      // Education.cgpa is DecimalField(max_digits=3, decimal_places=2).
      .refine((value) => !value || Number(value) < 10, 'CGPA must be below 10'),
    cgpa_scale: z
      .string()
      .optional()
      .or(z.literal(''))
      .refine((value) => !value || !Number.isNaN(Number(value)), 'Enter a number'),
    start_year: yearRequired,
    end_year: yearOptional,
    is_current: z.boolean().default(false),
    thesis_title: optionalText,
    achievements: optionalText,
  })
  .refine(
    (data) => {
      if (!data.cgpa) return true;
      const scale = Number(data.cgpa_scale || 4.0);
      return Number(data.cgpa) <= scale;
    },
    { message: 'CGPA cannot exceed the scale value', path: ['cgpa'] },
  )
  .refine(
    (data) => {
      if (data.is_current || !data.end_year || !data.start_year) return true;
      return Number(data.end_year) >= Number(data.start_year);
    },
    { message: 'End year cannot be before start year', path: ['end_year'] },
  );

export const skillSchema = z.object({
  name: z.string().trim().min(1, 'Skill name is required').max(100),
  category: optionalText,
  proficiency: optionalText,
  years_of_exp: z
    .string()
    .optional()
    .or(z.literal(''))
    .refine((value) => !value || !Number.isNaN(Number(value)), 'Enter a number'),
  is_featured: z.boolean().default(false),
});

export const projectSchema = z
  .object({
    name: z.string().trim().min(1, 'Project name is required').max(200),
    subtitle: optionalText,
    description: optionalText,
    tech_stack: optionalText,
    project_url: urlOptional,
    start_year: yearOptional,
    end_year: yearOptional,
    is_ongoing: z.boolean().default(false),
    is_professional: z.boolean().default(false),
  })
  .refine(
    (data) => {
      const count = String(data.tech_stack || '')
        .split(',')
        .map((item) => item.trim())
        .filter(Boolean).length;
      return count <= MAX_TECH_STACK;
    },
    { message: `Maximum ${MAX_TECH_STACK} technologies per project`, path: ['tech_stack'] },
  );

export const certificationSchema = z.object({
  name: z.string().trim().min(1, 'Certification name is required').max(200),
  issuing_organization: optionalText,
  issue_month: optionalText,
  issue_year: yearOptional,
  expiry_year: yearOptional,
  credential_url: urlOptional,
});

export const languageSchema = z.object({
  language_name: z.string().trim().min(1, 'Language is required').max(100),
  proficiency: optionalText,
});
