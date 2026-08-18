/* Option values must match the TextChoices in backend/apps/cv_builder/models/. */

export const EMPLOYMENT_TYPES = [
  { value: 'full_time', label: 'Full-time' },
  { value: 'part_time', label: 'Part-time' },
  { value: 'internship', label: 'Internship' },
  { value: 'contract', label: 'Contract' },
  { value: 'freelance', label: 'Freelance' },
];

export const LOCATION_TYPES = [
  { value: 'onsite', label: 'Onsite' },
  { value: 'remote', label: 'Remote' },
  { value: 'hybrid', label: 'Hybrid' },
];

export const DEGREE_TYPES = [
  { value: 'bs', label: 'BS' },
  { value: 'ms', label: 'MS' },
  { value: 'phd', label: 'PhD' },
  { value: 'diploma', label: 'Diploma' },
  { value: 'certificate', label: 'Certificate' },
  { value: 'other', label: 'Other' },
];

export const PROFICIENCY_LEVELS = [
  { value: 'beginner', label: 'Beginner' },
  { value: 'intermediate', label: 'Intermediate' },
  { value: 'advanced', label: 'Advanced' },
  { value: 'expert', label: 'Expert' },
];

export const LANGUAGE_PROFICIENCY = [
  { value: 'native', label: 'Native' },
  { value: 'fluent', label: 'Fluent' },
  { value: 'professional', label: 'Professional' },
  { value: 'basic', label: 'Basic' },
];

export const SKILL_CATEGORIES = [
  { value: 'Languages', label: 'Languages' },
  { value: 'Frameworks', label: 'Frameworks' },
  { value: 'Databases', label: 'Databases' },
  { value: 'Tools', label: 'Tools' },
  { value: 'Concepts', label: 'Concepts' },
  { value: 'Cloud', label: 'Cloud' },
  { value: 'Soft Skills', label: 'Soft Skills' },
];

export const MONTHS = [
  { value: '1', label: 'January' },
  { value: '2', label: 'February' },
  { value: '3', label: 'March' },
  { value: '4', label: 'April' },
  { value: '5', label: 'May' },
  { value: '6', label: 'June' },
  { value: '7', label: 'July' },
  { value: '8', label: 'August' },
  { value: '9', label: 'September' },
  { value: '10', label: 'October' },
  { value: '11', label: 'November' },
  { value: '12', label: 'December' },
];

/* Scoring weights come from backend/apps/cv_builder/services/completion.py.
   Kept here only to explain the score to the user — the backend stays authoritative. */
export const SECTION_WEIGHTS = {
  contact: 25,
  experience: 25,
  education: 15,
  skills: 15,
  summary: 10,
  projects: 10,
};

export const COMPLETE_THRESHOLD = 75;
export const SUMMARY_MIN_LENGTH = 80;
export const SKILLS_MIN_COUNT = 5;
export const MAX_TECH_STACK = 10;

export const STEPS = [
  { key: 'contact', label: 'Contact & Summary', sections: ['contact', 'summary'] },
  { key: 'experience', label: 'Work Experience', sections: ['experience'] },
  { key: 'education', label: 'Education', sections: ['education'] },
  { key: 'skills', label: 'Skills', sections: ['skills'] },
  { key: 'projects', label: 'Projects', sections: ['projects'] },
  { key: 'extras', label: 'Certifications & Languages', sections: [] },
];

export function monthLabel(value) {
  return MONTHS.find((month) => Number(month.value) === Number(value))?.label ?? '';
}

export function formatDateRange({ startMonth, startYear, endMonth, endYear, isCurrent }) {
  if (!startYear) {
    return '';
  }
  const start = [monthLabel(startMonth), startYear].filter(Boolean).join(' ');
  if (isCurrent) {
    return `${start} — Present`;
  }
  if (!endYear) {
    return start;
  }
  const end = [monthLabel(endMonth), endYear].filter(Boolean).join(' ');
  return `${start} — ${end}`;
}
