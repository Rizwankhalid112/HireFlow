"""Clearing a CV, in whole or in part.

Exists because the alternative is the user deleting nine roles, twelve skills
and four projects one row at a time — which is what a bad import, or simply
starting over, used to cost them.

Two operations, and the difference is deliberate:

- **Reset** empties content but keeps the `CVProfile` row. The user keeps their
  chosen template, their account link, and their place in the app; they just
  have a blank CV. This is the one people actually want.
- **Delete** removes the profile entirely. Everything CASCADEs — sections,
  upload logs, AI suggestion logs. Recoverable only by starting again.

Both clear stored files as they go. `delete_stale_drafts` and
`delete_orphaned_files` would eventually collect them, but "eventually" is up to
a week, and a user who resets their CV has usually just decided they want the
photo gone now.
"""

import logging

from django.db import transaction

logger = logging.getLogger(__name__)

# Reverse accessor per section, in the order the builder presents them.
SECTIONS = {
    'work_experience': 'work_experiences',
    'education': 'education_entries',
    'skills': 'skills',
    'projects': 'projects',
    'certifications': 'certifications',
    'languages': 'languages',
}

# Cleared by `personal`. `email` is excluded on purpose: it is pre-filled from
# the account and is how the CV is contacted, so a reset should not blank it.
# `template_id` is excluded because it is a preference, not content.
PERSONAL_FIELDS = (
    'full_name', 'professional_title', 'phone', 'city', 'country',
    'linkedin_url', 'github_url', 'portfolio_url', 'summary',
)

ALL_SECTIONS = ('personal', 'photo', *SECTIONS)


def _delete_file(field, label, profile_id):
    if not field:
        return
    try:
        field.delete(save=False)
    except Exception as exc:
        # A missing file is not a reason to fail the reset — the row is what
        # the user asked to be rid of.
        logger.warning('Could not delete %s for CV %s: %s', label, profile_id, exc)


def reset_cv(profile, sections=None):
    """Clear `sections` (default: everything). Returns `{section: rows_cleared}`.

    Counts are returned rather than a bare success so the UI can say what
    actually happened — "cleared 9 roles and 12 skills" is a confirmation the
    user can check, where "done" is not.
    """
    requested = list(sections) if sections else list(ALL_SECTIONS)
    cleared = {}

    with transaction.atomic():
        for name in requested:
            if name in SECTIONS:
                queryset = getattr(profile, SECTIONS[name]).all()
                count = queryset.count()
                if count:
                    # Deleted through the queryset so post_delete signals fire
                    # and completion is recomputed.
                    queryset.delete()
                cleared[name] = count

            elif name == 'personal':
                changed = sum(1 for f in PERSONAL_FIELDS if getattr(profile, f, ''))
                for field in PERSONAL_FIELDS:
                    setattr(profile, field, '')
                cleared['personal'] = changed

            elif name == 'photo':
                had_photo = bool(profile.photo)
                _delete_file(profile.photo, 'photo', profile.id)
                profile.photo = None
                cleared['photo'] = 1 if had_photo else 0

        # The rendered PDF is now of a CV that no longer exists.
        _delete_file(profile.pdf_file, 'pdf', profile.id)
        profile.pdf_file = None
        profile.pdf_generated_at = None

        # A cleared draft should get the full 30 days again, and its reminder
        # should be able to fire a second time.
        profile.reminder_sent = False

        # save() recomputes completion; content_updated_at is auto_now, so the
        # preview cache and the retention clock both move with this.
        profile.save()

    return cleared


def delete_cv(profile):
    """Remove the profile and everything hanging off it."""
    _delete_file(profile.photo, 'photo', profile.id)
    _delete_file(profile.pdf_file, 'pdf', profile.id)
    profile.delete()
