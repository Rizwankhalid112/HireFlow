"""Score a CV against a job description, and write the cover letter.

One entry point, one model call. The call is combined deliberately: the letter
has to come from the same reading of the two documents that produced the keyword
analysis, and splitting it would mean sending both documents twice.

Nothing here writes to the CV. This module reads a CV and a job description and
returns an opinion — applying any of it is a separate, explicit action, exactly
as with the CV import.
"""

import logging

from django.conf import settings

from apps.cv_builder.services.ai.client import complete
from apps.cv_builder.services.ai.prompts import JOB_MATCH
from apps.cv_builder.services.ai.schemas import JobMatchResult

logger = logging.getLogger(__name__)

UNAVAILABLE_MESSAGE = (
    'The job matcher is unavailable right now. Nothing has been saved — '
    'try again in a few minutes.'
)

# A job description plus a whole CV in, and a cover letter plus keyword lists
# out. Far past the suggestion ceiling, and a truncated structured output comes
# back as nothing at all rather than as a partial answer.
DEFAULT_MAX_TOKENS = 6000

# Long enough to be a real posting, short enough that somebody has not pasted a
# whole careers site. Both ends produce a bad result rather than an error, which
# is why they are caught before the call rather than after it.
MIN_JD_CHARS = 120
MAX_JD_CHARS = 20_000

# The CV side is bounded too — an uploaded CV is already capped at extraction,
# but a built one has no such limit.
MAX_CV_CHARS = 20_000


class JobDescriptionTooShort(ValueError):
    pass


def build_user_content(cv_text, jd_text):
    """The only per-request content, and it goes in `messages`, never the system
    prompt — the prompt is the cached prefix and one interpolated value makes it
    unique per user, silently at full price."""
    return (
        '<cv>\n'
        f'{cv_text.strip()[:MAX_CV_CHARS]}\n'
        '</cv>\n\n'
        '<job_description>\n'
        f'{jd_text.strip()[:MAX_JD_CHARS]}\n'
        '</job_description>'
    )


def match_job(cv_text, jd_text):
    """`(JobMatchResult, Usage)`.

    Raises `JobDescriptionTooShort` for input that cannot produce a useful
    answer, and `SuggestionUnavailable` for anything upstream.
    """
    cv_text = (cv_text or '').strip()
    jd_text = (jd_text or '').strip()

    if len(jd_text) < MIN_JD_CHARS:
        raise JobDescriptionTooShort(
            'That job description is too short to work with. '
            'Paste the full posting, including the requirements.'
        )
    if len(cv_text) < MIN_JD_CHARS:
        raise JobDescriptionTooShort(
            'There is not enough in this CV to compare. '
            'Fill in a few sections first, or upload a completed CV.'
        )

    result, usage = complete(
        JOB_MATCH,
        build_user_content(cv_text, jd_text),
        JobMatchResult,
        max_tokens=getattr(settings, 'AI_JOB_MATCH_MAX_TOKENS', DEFAULT_MAX_TOKENS),
        unavailable_message=UNAVAILABLE_MESSAGE,
    )

    # The score is the model's judgement and the schema cannot bound an int, so
    # it is clamped here rather than trusted into a column the UI renders as a
    # percentage.
    result.match_score = max(0, min(100, result.match_score))

    logger.info(
        'Job match: score=%d matched=%d reworded=%d missing=%d',
        result.match_score, len(result.matched), len(result.reworded), len(result.missing),
    )
    return result, usage
