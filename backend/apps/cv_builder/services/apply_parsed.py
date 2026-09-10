"""Write a reviewed import onto the user's CV.

This is the only path by which parsed data reaches the database. Everything
before it — extraction, the AI call, normalisation — is read-only with respect
to the CV, which is what makes the overwrite protection in the spec real.

Three things govern the design:

- **Every write goes through the section's own serializer.** The import must not
  be able to store a value the manual form would reject; if the two ever
  disagree, the form is the definition and this follows it.
- **A bad row is skipped, not fatal.** One malformed role should not cost the
  user the other four. Each row runs in a savepoint, so a rejection rolls back
  that row alone. The outer transaction still wraps everything, so an
  *unexpected* failure cannot leave a half-imported CV.
- **A row missing a NOT NULL field does not import until it is answered.** The
  diff UI collects the answer; this refuses to invent one.
"""

import logging

from django.db import transaction

from apps.cv_builder.serializers.education import EducationSerializer
from apps.cv_builder.serializers.project import (
    CVCertificationSerializer,
    CVLanguageSerializer,
    CVProjectSerializer,
)
from apps.cv_builder.serializers.skill import CVSkillSerializer
from apps.cv_builder.serializers.work_experience import (
    WorkBulletSerializer,
    WorkExperienceSerializer,
)

logger = logging.getLogger(__name__)

KEEP = 'keep'
REPLACE = 'replace'
MERGE = 'merge'

LIST_SECTIONS = (
    'work_experience',
    'education',
    'skills',
    'projects',
    'certifications',
    'languages',
)

VALID_CHOICES = {KEEP, REPLACE, MERGE}

# Fields the parse can set on the profile. `email` is included but only ever
# fills a blank — see `_apply_personal`.
_PERSONAL_FIELDS = (
    'full_name', 'professional_title', 'email', 'phone', 'city', 'country',
    'linkedin_url', 'github_url', 'portfolio_url', 'summary',
)


class ApplyResult:
    """What happened, in enough detail for the UI to be honest about it."""

    def __init__(self):
        self.imported = 0
        self.skipped = []

    def skip(self, section, label, reason):
        self.skipped.append({'section': section, 'item': label, 'reason': reason})

    def as_dict(self):
        return {'imported': self.imported, 'skipped': self.skipped}


def _answers_for(answers, section, index):
    """User-supplied values for one row's missing required fields."""
    section_answers = (answers or {}).get(section) or {}
    # JSON object keys are strings even when the UI meant an index.
    return section_answers.get(str(index)) or section_answers.get(index) or {}


def _resolve_row(row, section, index, answers, result):
    """Merge in the answers, or report the row as blocked.

    Returns the completed row, or None if a required field is still missing.
    """
    row = dict(row)
    missing = row.pop('needs_attention', None) or []
    supplied = _answers_for(answers, section, index)

    still_missing = []
    for field in missing:
        value = supplied.get(field)
        if value in (None, '', 0):
            still_missing.append(field)
        else:
            row[field] = value

    if still_missing:
        result.skip(
            section,
            row.get('company_name') or row.get('institution') or row.get('name') or f'#{index + 1}',
            f'Missing required {", ".join(still_missing)}.',
        )
        return None

    return row


def _write(serializer_class, data, cv, section, label, result, save_kwargs=None):
    """One row, in its own savepoint.

    A serializer rejection is expected and survivable; it rolls back this row
    and is reported. Anything else propagates and takes the whole apply with it,
    which is correct — an unexpected error means we do not know what state the
    CV is in.

    `save_kwargs` defaults to `{'cv': cv}`, which is how every section attaches
    except bullets — those hang off their experience and have no `cv` field.
    """
    try:
        with transaction.atomic():
            serializer = serializer_class(data=data)
            if not serializer.is_valid():
                result.skip(section, label, _first_error(serializer.errors))
                return None
            return serializer.save(**(save_kwargs if save_kwargs is not None else {'cv': cv}))
    except Exception as exc:
        logger.exception('Row failed in %s for cv %s: %s', section, cv.id, exc)
        result.skip(section, label, 'Could not be saved.')
        return None


def _first_error(errors):
    for field, messages in errors.items():
        if isinstance(messages, list) and messages:
            return f'{field}: {messages[0]}'
    return 'Invalid data.'


def _apply_personal(profile, personal, choice):
    """Contact details and summary.

    `merge` fills only what is currently blank, which is the useful reading:
    the user has typed their name already and does not want it replaced, but
    does want the phone number the CV had.

    `email` never overwrites, on any choice. It is pre-filled from the account
    at profile creation and is how the CV is contacted — a stale address in an
    old CV file must not silently replace the live one.
    """
    if choice == KEEP:
        return 0

    changed = 0
    for field in _PERSONAL_FIELDS:
        value = (personal or {}).get(field)
        if not value:
            continue
        current = getattr(profile, field, '')
        if field == 'email' and current:
            continue
        if choice == MERGE and current:
            continue
        if current != value:
            setattr(profile, field, value)
            changed += 1

    if changed:
        profile.save()
    return changed


def _apply_work_experience(profile, rows, choice, answers, result):
    if choice == REPLACE:
        profile.work_experiences.all().delete()

    start_order = 0 if choice == REPLACE else profile.work_experiences.count()

    for index, raw in enumerate(rows):
        row = _resolve_row(raw, 'work_experience', index, answers, result)
        if row is None:
            continue

        bullets = row.pop('bullets', []) or []
        row['order'] = start_order + index
        label = f"{row.get('role_title')} at {row.get('company_name')}"

        experience = _write(
            WorkExperienceSerializer, row, profile, 'work_experience', label, result,
        )
        if experience is None:
            continue
        result.imported += 1

        for bullet_index, text in enumerate(bullets):
            _write(
                WorkBulletSerializer,
                {'text': text, 'order': bullet_index},
                profile,
                'work_experience',
                text[:60],
                result,
                save_kwargs={'experience': experience},
            )


def _apply_education(profile, rows, choice, answers, result):
    if choice == REPLACE:
        profile.education_entries.all().delete()

    start_order = 0 if choice == REPLACE else profile.education_entries.count()

    for index, raw in enumerate(rows):
        row = _resolve_row(raw, 'education', index, answers, result)
        if row is None:
            continue
        row['order'] = start_order + index
        if _write(
            EducationSerializer, row, profile, 'education', row.get('institution'), result,
        ):
            result.imported += 1


def _apply_skills(profile, rows, choice, result):
    """Skills, with `merge` meaning "add what is not already there".

    Case-insensitive on name, matching the bulk-add endpoint: a duplicate is
    skipped silently rather than reported, because a user merging two skill
    lists expects the overlap to disappear, not to be told about it.
    """
    if choice == REPLACE:
        profile.skills.all().delete()
        existing = set()
    else:
        existing = {name.casefold() for name in profile.skills.values_list('name', flat=True)}

    start_order = profile.skills.count()

    for index, row in enumerate(rows):
        name = (row.get('name') or '').strip()
        if not name or name.casefold() in existing:
            continue
        existing.add(name.casefold())

        payload = {
            'name': name,
            'category': row.get('category') or '',
            'proficiency': row.get('proficiency') or '',
            'order': start_order + index,
        }
        # The serializer already handles canonical_id: it sets the FK, takes the
        # canonical spelling and category, and marks the skill verified. Passing
        # it through means an imported skill is indistinguishable from one
        # picked out of the autocomplete, which is what it should be.
        if row.get('canonical_id'):
            payload['canonical_id'] = row['canonical_id']

        if _write(CVSkillSerializer, payload, profile, 'skills', name, result):
            result.imported += 1


def _apply_simple(profile, rows, choice, result, section, serializer_class, related, label_field):
    if choice == REPLACE:
        getattr(profile, related).all().delete()

    start_order = 0 if choice == REPLACE else getattr(profile, related).count()

    for index, row in enumerate(rows):
        payload = dict(row)
        payload['order'] = start_order + index
        if _write(
            serializer_class, payload, profile, section, payload.get(label_field), result,
        ):
            result.imported += 1


def apply_parsed_cv(profile, payload, choices, answers=None):
    """Apply a reviewed import. Returns an `ApplyResult`.

    The whole thing is one transaction: per-row savepoints absorb the expected
    failures, and anything they do not absorb rolls the import back entirely
    rather than leaving the CV in a state nobody chose.
    """
    result = ApplyResult()
    answers = answers or {}

    with transaction.atomic():
        result.imported += _apply_personal(
            profile, payload.get('personal'), choices.get('personal', KEEP),
        )

        if choices.get('work_experience', KEEP) != KEEP:
            _apply_work_experience(
                profile, payload.get('work_experience') or [],
                choices['work_experience'], answers, result,
            )

        if choices.get('education', KEEP) != KEEP:
            _apply_education(
                profile, payload.get('education') or [],
                choices['education'], answers, result,
            )

        if choices.get('skills', KEEP) != KEEP:
            _apply_skills(profile, payload.get('skills') or [], choices['skills'], result)

        if choices.get('projects', KEEP) != KEEP:
            _apply_simple(
                profile, payload.get('projects') or [], choices['projects'], result,
                'projects', CVProjectSerializer, 'projects', 'name',
            )

        if choices.get('certifications', KEEP) != KEEP:
            _apply_simple(
                profile, payload.get('certifications') or [], choices['certifications'],
                result, 'certifications', CVCertificationSerializer, 'certifications', 'name',
            )

        if choices.get('languages', KEEP) != KEEP:
            _apply_simple(
                profile, payload.get('languages') or [], choices['languages'], result,
                'languages', CVLanguageSerializer, 'languages', 'language_name',
            )

        # Completion score and the preview's content stamp both hang off a save.
        profile.save()

    return result
