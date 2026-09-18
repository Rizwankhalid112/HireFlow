"""The CV parse entry point.

One function, mirroring `suggest.py`: build the call, run it, normalise the
result. The Celery task above it deals with status and persistence; this deals
with getting structured data out of raw text.

Nothing here writes to the database. That is deliberate and is the whole of the
overwrite protection promised in the spec — parsed data reaches a CV only
through an explicit apply.
"""

import logging

from django.conf import settings

from apps.cv_builder.services.ai.client import complete
from apps.cv_builder.services.ai.prompts import PARSE
from apps.cv_builder.services.ai.schemas import ParsedCV

logger = logging.getLogger(__name__)

# "Your text is unchanged" is meaningless when the user uploaded a file. This
# says what is actually true and what to do about it.
UNAVAILABLE_MESSAGE = (
    'The CV reader is unavailable right now. Your file is saved — '
    'you can try again in a few minutes.'
)

# A parse that finds no roles and no education did not really understand the
# file. The user is told, rather than being shown a near-empty diff and left to
# wonder whether that is all their CV contained.
THIN_PARSE_SECTIONS = ('work_experience', 'education')


def parse_cv_text(text):
    """`(payload, usage, is_thin)` for the extracted text of one CV.

    `payload` is the normalised, JSON-serialisable dict — never a model
    instance and never a `ParsedCV`, because it is stored on the log and read
    back by the frontend.
    """
    # Imported here, not at module scope: parse_normalize reaches back into
    # ai.guardrails for the canonical-skill lookup, and importing it at the top
    # would make this package's __init__ import itself through that loop.
    from apps.cv_builder.services.parse_normalize import count_fields, normalize

    parsed, usage = complete(
        PARSE,
        # The only thing that varies per request, and it goes in `messages`, not
        # the system prompt — the prompt is the cached prefix.
        text,
        ParsedCV,
        max_tokens=settings.AI_PARSE_MAX_TOKENS,
        unavailable_message=UNAVAILABLE_MESSAGE,
    )

    payload = normalize(parsed)
    extracted, total = count_fields(payload)
    payload['fields_extracted'] = extracted
    payload['fields_total'] = total

    is_thin = not any(payload.get(section) for section in THIN_PARSE_SECTIONS)
    if is_thin:
        logger.info('Thin CV parse: no work experience and no education found')

    return payload, usage, is_thin
