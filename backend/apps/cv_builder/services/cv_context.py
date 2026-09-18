"""Flatten a CVProfile into the one dict every template consumes.

Templates never touch the ORM. Adding a template is HTML + CSS + a registry
entry — no Python. Keep this the only place that knows about model internals.
"""

from pathlib import Path

MONTH_NAMES = [
    '', 'January', 'February', 'March', 'April', 'May', 'June',
    'July', 'August', 'September', 'October', 'November', 'December',
]


def _month(value):
    if not value or not (1 <= int(value) <= 12):
        return ''
    return MONTH_NAMES[int(value)]


def format_range(start_month, start_year, end_month, end_year, is_current):
    """'March 2023 — Present' / '2019 — 2023' / '2021'."""
    if not start_year:
        return ''
    start = ' '.join(part for part in (_month(start_month), str(start_year)) if part)
    if is_current:
        return f'{start} — Present'
    if not end_year:
        return start
    end = ' '.join(part for part in (_month(end_month), str(end_year)) if part)
    return f'{start} — {end}'


def _contact_lines(cv):
    """Contact items in display order, blanks dropped."""
    location = ', '.join(part for part in (cv.city, cv.country) if part)
    return [item for item in (cv.email, cv.phone, location) if item]


def _links(cv):
    labels = (
        ('LinkedIn', cv.linkedin_url),
        ('GitHub', cv.github_url),
        ('Portfolio', cv.portfolio_url),
    )
    return [{'label': label, 'url': url} for label, url in labels if url]


def build_cv_context(cv, template=None):
    """Build the render context. `template` is a registry entry."""
    template = template or {}

    experiences = []
    for experience in cv.work_experiences.all().prefetch_related('bullets'):
        experiences.append({
            'company_name': experience.company_name,
            'role_title': experience.role_title,
            'employment_type': experience.get_employment_type_display(),
            'location': experience.location,
            'location_type': experience.get_location_type_display(),
            'date_range': format_range(
                experience.start_month, experience.start_year,
                experience.end_month, experience.end_year, experience.is_current,
            ),
            'bullets': [bullet.text for bullet in experience.bullets.all()],
        })

    education = []
    for entry in cv.education_entries.all():
        degree = ' in '.join(
            part for part in (entry.get_degree_type_display(), entry.field_of_study) if part
        )
        education.append({
            'institution': entry.institution,
            'degree': degree or 'Education',
            'date_range': format_range(
                None, entry.start_year, None, entry.end_year, entry.is_current,
            ),
            'cgpa': f'{entry.cgpa}/{entry.cgpa_scale or "4.0"}' if entry.cgpa else '',
            'thesis_title': entry.thesis_title,
            'achievements': entry.achievements,
        })

    # Grouped for templates that print skills by category; `skills` stays flat
    # for the ones that print a single inline run.
    skills = list(cv.skills.all().select_related('canonical'))
    grouped = {}
    for skill in skills:
        grouped.setdefault(skill.category or 'Other', []).append(skill.name)

    projects = [{
        'name': project.name,
        'subtitle': project.subtitle,
        'description': project.description,
        'tech_stack': project.tech_stack or [],
        'url': project.project_url,
        'date_range': format_range(
            None, project.start_year, None, project.end_year, project.is_ongoing,
        ),
    } for project in cv.projects.all()]

    certifications = [{
        'name': certification.name,
        'issuer': certification.issuing_organization,
        'date': ' '.join(part for part in (
            _month(certification.issue_month),
            str(certification.issue_year) if certification.issue_year else '',
        ) if part),
        'url': certification.credential_url,
    } for certification in cv.certifications.all()]

    languages = [{
        'name': language.language_name,
        'proficiency': language.get_proficiency_display(),
    } for language in cv.languages.all()]

    # Only templates that declare a photo slot get one, so an uploaded image
    # never leaks into a text-only layout.
    #
    # A file:// URI, not photo.url: MEDIA_URL gives '/media/...', and a
    # leading-slash path resolves against the filesystem root rather than
    # base_url, so WeasyPrint silently renders no image at all.
    photo_url = ''
    if template.get('photo') and cv.photo:
        try:
            photo_path = Path(cv.photo.path)
            if photo_path.is_file():
                photo_url = photo_path.as_uri()
        except (ValueError, NotImplementedError):
            # Non-filesystem storage backend — fall back to the URL.
            photo_url = cv.photo.url

    return {
        'full_name': cv.full_name,
        'professional_title': cv.professional_title,
        'summary': cv.summary,
        'contact_lines': _contact_lines(cv),
        'links': _links(cv),
        'photo_url': photo_url,
        'experiences': experiences,
        'education': education,
        'skills': [skill.name for skill in skills],
        'skills_grouped': [
            {'category': category, 'items': items} for category, items in grouped.items()
        ],
        'projects': projects,
        'certifications': certifications,
        'languages': languages,
        'template': template,
    }
