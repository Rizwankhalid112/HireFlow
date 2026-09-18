"""Builders for `ParsedCV` pieces.

The schema is closed and fully required — every field must be present — which is
correct for the model and miserable to write out in each test. These supply
empty defaults so a test states only the field it is about.
"""

from apps.cv_builder.services.ai.schemas import (
    ParsedCertification,
    ParsedCV,
    ParsedEducation,
    ParsedExperience,
    ParsedLanguage,
    ParsedPersonal,
    ParsedProject,
    ParsedSkill,
    UnmappedSection,
)


def personal(**overrides):
    defaults = {
        'full_name': '', 'professional_title': '', 'email': '', 'phone': '',
        'city': '', 'country': '', 'linkedin_url': '', 'github_url': '',
        'portfolio_url': '', 'summary': '',
    }
    return ParsedPersonal(**{**defaults, **overrides})


def experience(**overrides):
    defaults = {
        'company_name': 'Acme Corp', 'role_title': 'Engineer', 'employment_type': '',
        'location': '', 'location_type': '', 'start_month': 0, 'start_year': 2020,
        'end_month': 0, 'end_year': 0, 'is_current': False, 'bullets': [],
    }
    return ParsedExperience(**{**defaults, **overrides})


def education(**overrides):
    defaults = {
        'institution': 'MIT', 'degree_type': '', 'field_of_study': '', 'cgpa': '',
        'start_year': 2015, 'end_year': 0, 'is_current': False,
        'thesis_title': '', 'achievements': '',
    }
    return ParsedEducation(**{**defaults, **overrides})


def skill(**overrides):
    defaults = {'name': 'Python', 'category': '', 'proficiency': ''}
    return ParsedSkill(**{**defaults, **overrides})


def project(**overrides):
    defaults = {
        'name': 'Ledger', 'subtitle': '', 'description': '', 'tech_stack': [],
        'project_url': '', 'start_year': 0, 'end_year': 0,
        'is_ongoing': False, 'is_professional': False,
    }
    return ParsedProject(**{**defaults, **overrides})


def certification(**overrides):
    defaults = {
        'name': 'AWS Solutions Architect', 'issuing_organization': '',
        'issue_month': 0, 'issue_year': 0, 'expiry_year': 0, 'credential_url': '',
    }
    return ParsedCertification(**{**defaults, **overrides})


def language(**overrides):
    defaults = {'language_name': 'English', 'proficiency': ''}
    return ParsedLanguage(**{**defaults, **overrides})


def unmapped(**overrides):
    defaults = {'heading': 'Publications', 'content': 'A paper.'}
    return UnmappedSection(**{**defaults, **overrides})


def parsed_cv(**overrides):
    defaults = {
        'personal': personal(),
        'work_experience': [],
        'education': [],
        'skills': [],
        'projects': [],
        'certifications': [],
        'languages': [],
        'unmapped_sections': [],
    }
    return ParsedCV(**{**defaults, **overrides})
