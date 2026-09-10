"""Build the user-message payload for each section.

Everything user-specific lives here and nothing user-specific lives in
prompts.py — that split is what makes the cached system prefix shared across
every user of a section.

Each builder returns `(text, sources)`. `sources` is the flat list of strings the
suggestion is allowed to draw facts from; guardrails.py checks the model's output
against it, so it must contain everything the model was shown and nothing it
wasn't.
"""

import hashlib

from apps.cv_builder.services.cv_context import format_range

MAX_BULLETS_SHOWN = 8
MAX_SKILLS_SHOWN = 20
MAX_ROLES_IN_SUMMARY = 3


def _line(label, value):
    return f'{label}: {value}' if value else None


def _block(parts):
    return '\n'.join(part for part in parts if part)


def digest(text):
    """Stable identifier for a built context, used for the log and for spotting
    an identical re-request."""
    return hashlib.sha256(text.encode()).hexdigest()[:32]


def build_bullet_context(experience, note='', target_role=''):
    """One role, its existing bullets, and the user's rough note."""
    existing = [bullet.text for bullet in experience.bullets.all()[:MAX_BULLETS_SHOWN]]
    cv = experience.cv
    skills = [skill.name for skill in cv.skills.all()[:MAX_SKILLS_SHOWN]]

    date_range = format_range(
        experience.start_month, experience.start_year,
        experience.end_month, experience.end_year, experience.is_current,
    )

    text = _block([
        'Write bullet points for this role.',
        '',
        _line('Role', experience.role_title),
        _line('Company', experience.company_name),
        _line('Employment type', experience.get_employment_type_display()),
        _line('Dates', date_range),
        _line('Currently in this role', 'yes' if experience.is_current else 'no'),
        _line('Target role the CV is aimed at', target_role),
        '',
        # Shown so variants neither duplicate an existing point nor drift from
        # the register the user writes in.
        'Bullets already on this role (do not repeat these):',
        *([f'- {bullet}' for bullet in existing] or ['- (none yet)']),
        '',
        'Skills listed elsewhere on this CV: ' + (', '.join(skills) if skills else '(none)'),
        '',
        'What the user says they did:',
        note.strip() or '(nothing written yet — draw only on the role and company above)',
    ])

    # `existing` is deliberately absent. The other bullets on this role are
    # shown to the model so it does not repeat them and matches the user's
    # register — but they are not a licence to reuse their figures. A "40%" that
    # belongs to last year's caching work must not silently attach itself to a
    # new bullet about something else. Each bullet's facts come from the note,
    # the role, and the CV's own metadata.
    sources = [
        experience.role_title, experience.company_name, experience.location,
        experience.get_employment_type_display(), date_range, note, target_role,
        *skills,
    ]
    return text, [source for source in sources if source]


def build_summary_context(cv, target_role=''):
    """The whole CV. The summary is the one section that legitimately needs it."""
    experiences = list(cv.work_experiences.all()[:MAX_ROLES_IN_SUMMARY])
    skills = [skill.name for skill in cv.skills.all()[:MAX_SKILLS_SHOWN]]
    education = list(cv.education_entries.all()[:2])
    projects = list(cv.projects.all()[:3])

    role_lines, bullet_sources = [], []
    for experience in experiences:
        date_range = format_range(
            experience.start_month, experience.start_year,
            experience.end_month, experience.end_year, experience.is_current,
        )
        role_lines.append(f'- {experience.role_title} at {experience.company_name} ({date_range})')
        for bullet in experience.bullets.all()[:3]:
            role_lines.append(f'    · {bullet.text}')
            bullet_sources.append(bullet.text)

    education_lines = [
        f'- {entry.get_degree_type_display()} {entry.field_of_study}, {entry.institution}'.strip()
        for entry in education
    ]
    project_lines = [
        f'- {project.name}: {", ".join(project.tech_stack or []) or "no stack listed"}'
        for project in projects
    ]

    text = _block([
        'Write the professional summary for this CV.',
        '',
        _line('Name', cv.full_name),
        _line('Current title on the CV', cv.professional_title),
        _line('Target role', target_role),
        '',
        'Roles:',
        *(role_lines or ['- (none listed)']),
        '',
        'Education:',
        *(education_lines or ['- (none listed)']),
        '',
        'Projects:',
        *(project_lines or ['- (none listed)']),
        '',
        'Skills: ' + (', '.join(skills) if skills else '(none listed)'),
        '',
        'Existing summary (rewrite this if present):',
        cv.summary.strip() or '(none yet)',
    ])

    sources = [
        cv.full_name, cv.professional_title, cv.summary, target_role,
        *bullet_sources, *skills,
        *[experience.role_title for experience in experiences],
        *[experience.company_name for experience in experiences],
        *role_lines, *education_lines, *project_lines,
    ]
    return text, [source for source in sources if source]


def build_skills_context(cv, target_role=''):
    """Every piece of text the user wrote, so extraction has real evidence."""
    evidence_lines, sources = [], []

    for experience in cv.work_experiences.all():
        for bullet in experience.bullets.all():
            evidence_lines.append(f'- {bullet.text}')
            sources.append(bullet.text)

    for project in cv.projects.all():
        stack = ', '.join(project.tech_stack or [])
        line = f'- {project.name}: {project.description}'.strip()
        evidence_lines.append(line)
        sources.append(line)
        if stack:
            evidence_lines.append(f'  stack: {stack}')
            sources.append(stack)

    existing = [skill.name for skill in cv.skills.all()]

    text = _block([
        'Identify the skills this CV demonstrates.',
        '',
        _line('Current title', cv.professional_title),
        _line('Target role', target_role),
        '',
        'Text the user wrote (this is the only valid evidence):',
        *(evidence_lines or ['- (nothing written yet)']),
        '',
        'Already on the CV — do not suggest these again:',
        ', '.join(existing) if existing else '(none)',
    ])

    sources.extend([cv.professional_title, target_role, *existing])
    return text, [source for source in sources if source]


def build_project_context(project, note='', target_role=''):
    stack = ', '.join(project.tech_stack or [])
    date_range = format_range(
        None, project.start_year, None, project.end_year, project.is_ongoing,
    )

    text = _block([
        'Write the description points for this project.',
        '',
        _line('Name', project.name),
        _line('Subtitle', project.subtitle),
        _line('Tech stack', stack),
        _line('Dates', date_range),
        _line('Professional (not personal) project', 'yes' if project.is_professional else 'no'),
        _line('Target role the CV is aimed at', target_role),
        '',
        'What the user says about it:',
        (note.strip() or project.description.strip() or '(nothing written yet)'),
    ])

    sources = [
        project.name, project.subtitle, project.description, stack, date_range,
        note, target_role, *(project.tech_stack or []),
    ]
    return text, [source for source in sources if source]


def build_title_context(cv, target_role=''):
    roles = [experience.role_title for experience in cv.work_experiences.all()[:4]]
    skills = [skill.name for skill in cv.skills.all()[:12]]

    text = _block([
        'Normalise the professional title on this CV.',
        '',
        _line('Current title', cv.professional_title or '(none set)'),
        _line('Target role', target_role),
        '',
        'Roles actually held: ' + (', '.join(roles) if roles else '(none listed)'),
        'Skills: ' + (', '.join(skills) if skills else '(none listed)'),
    ])

    sources = [cv.professional_title, target_role, *roles, *skills]
    return text, [source for source in sources if source]


def build_full_cv_text(cv):
    """The entire CV as plain text, for job matching.

    Deliberately **not** truncated, unlike `build_summary_context`. The other
    builders cap roles and bullets because a summary does not improve with the
    tenth bullet. Here, truncation would actively produce a wrong answer: a skill
    mentioned only in the fourth bullet of an older role would read as absent,
    and the feature would ask the user whether they have a skill their CV already
    lists. Cutting the input invents gaps.

    The only bound is the hard character cap in `job_match.py`, which exists to
    stop a runaway request rather than to shape the content.
    """
    lines = [
        _line('Name', cv.full_name),
        _line('Title', cv.professional_title),
        _line('Location', ', '.join(part for part in [cv.city, cv.country] if part)),
    ]

    if cv.summary:
        lines += ['', 'Summary:', cv.summary.strip()]

    experiences = list(cv.work_experiences.all())
    if experiences:
        lines += ['', 'Experience:']
        for experience in experiences:
            date_range = format_range(
                experience.start_month, experience.start_year,
                experience.end_month, experience.end_year, experience.is_current,
            )
            location = f' — {experience.location}' if experience.location else ''
            lines.append(
                f'- {experience.role_title} at {experience.company_name}'
                f' ({date_range}){location}'
            )
            for bullet in experience.bullets.all():
                lines.append(f'    · {bullet.text}')

    education = list(cv.education_entries.all())
    if education:
        lines += ['', 'Education:']
        for entry in education:
            degree = entry.get_degree_type_display() if entry.degree_type else ''
            years = f' ({entry.start_year}–{entry.end_year or "present"})' if entry.start_year else ''
            lines.append(
                f'- {" ".join(part for part in [degree, entry.field_of_study] if part)}'
                f', {entry.institution}{years}'.strip()
            )
            if entry.achievements:
                lines.append(f'    · {entry.achievements}')

    skills = list(cv.skills.all())
    if skills:
        lines += ['', 'Skills: ' + ', '.join(skill.name for skill in skills)]

    projects = list(cv.projects.all())
    if projects:
        lines += ['', 'Projects:']
        for project in projects:
            stack = ', '.join(project.tech_stack or [])
            lines.append(f'- {project.name}' + (f' ({stack})' if stack else ''))
            if project.description:
                lines.append(f'    {project.description}')

    certifications = list(cv.certifications.all())
    if certifications:
        lines += ['', 'Certifications:']
        for certification in certifications:
            issuer = f' — {certification.issuing_organization}' if certification.issuing_organization else ''
            lines.append(f'- {certification.name}{issuer}')

    languages = list(cv.languages.all())
    if languages:
        lines += [
            '',
            'Languages: ' + ', '.join(
                f'{language.language_name}'
                + (f' ({language.get_proficiency_display()})' if language.proficiency else '')
                for language in languages
            ),
        ]

    return _block(lines)
