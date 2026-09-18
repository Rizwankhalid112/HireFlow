"""Completion scoring.

Scoring is all-or-nothing per section, and the weights below are mirrored in
`frontend/src/features/cvBuilder/constants.js` so the navigator can explain an
apparently stalled score.

Every check here is one query at most. That matters more than it looks:
`CVProfile.save()` recomputes the score, and a `post_save` signal on all seven
child models calls it — so this runs on *every write to a CV*, not just when
someone loads the dashboard.
"""

from django.db.models import Count

COMPLETE_THRESHOLD = 75
SUMMARY_MIN_LENGTH = 80
SKILLS_MIN_COUNT = 5
EXPERIENCE_MIN_BULLETS = 2

# Mirrored in frontend/src/features/cvBuilder/constants.js (STEPS[].points).
# Change one, change the other, or the navigator explains a score it cannot
# produce.
SECTION_WEIGHTS = {
    'contact': 25,
    'summary': 10,
    'experience': 25,
    'education': 15,
    'skills': 15,
    'projects': 10,
}


def _has_contact_info(cv_profile):
    return all([
        cv_profile.full_name.strip(),
        cv_profile.email.strip(),
        cv_profile.phone.strip(),
        cv_profile.city.strip(),
    ])


def _has_summary(cv_profile):
    return len(cv_profile.summary.strip()) >= SUMMARY_MIN_LENGTH


def _has_work_experience(cv_profile):
    """At least one role carrying at least two bullets.

    Counted in the database rather than by looping and calling `.count()` per
    role: that was one query per experience on a path that runs on every single
    write to the CV.
    """
    if not cv_profile.pk:
        return False

    return (
        cv_profile.work_experiences
        .annotate(bullet_count=Count('bullets'))
        .filter(bullet_count__gte=EXPERIENCE_MIN_BULLETS)
        .exists()
    )


def _has_education(cv_profile):
    return cv_profile.pk and cv_profile.education_entries.exists()


def _has_skills(cv_profile):
    # `count()` rather than slicing: the threshold is the whole question.
    return cv_profile.pk and cv_profile.skills.count() >= SKILLS_MIN_COUNT


def _has_projects(cv_profile):
    return cv_profile.pk and cv_profile.projects.exists()


def calculate_section_completion(cv_profile):
    return {
        'contact': _has_contact_info(cv_profile),
        'summary': _has_summary(cv_profile),
        'experience': _has_work_experience(cv_profile),
        'education': _has_education(cv_profile),
        'skills': _has_skills(cv_profile),
        'projects': _has_projects(cv_profile),
    }


def score_sections(sections):
    """`(score, is_complete)` from an already-computed section dict.

    Split out because the completion endpoint needs the sections *and* the
    score, and calling `compute_completion` alongside
    `calculate_section_completion` ran every section query twice.
    """
    score = min(sum(weight for key, weight in SECTION_WEIGHTS.items() if sections[key]), 100)
    return score, score >= COMPLETE_THRESHOLD


def compute_completion(cv_profile):
    """`(score, is_complete)` for a profile. Used by `CVProfile.save()`."""
    return score_sections(calculate_section_completion(cv_profile))
