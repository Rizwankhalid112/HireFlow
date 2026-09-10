"""The single Claude call.

One place builds a request, so caching, model choice, timeouts and error mapping
are decided once rather than per section.
"""

import logging

from django.conf import settings

logger = logging.getLogger(__name__)

# Suggestions are short. A generous ceiling still costs nothing unless used, but
# leaving it unbounded risks a runaway response on a malformed prompt. A whole-CV
# parse needs far more and passes its own — see settings.AI_PARSE_MAX_TOKENS.
MAX_TOKENS = 2000

# Used when a caller does not name its own. Deliberately suggestion-flavoured,
# because that was this module's only caller for its first life.
UNAVAILABLE_MESSAGE = (
    'The writing assistant is unavailable right now. Your text is unchanged.'
)


class SuggestionUnavailable(Exception):
    """The feature cannot run right now — no key, upstream down, timeout.

    Distinct from a bad request: the caller maps this to 503, so the frontend
    keeps the user's text and offers a retry rather than showing a validation
    error for something they did not do wrong.
    """


class Usage:
    """Token counts from one call, for the log and for cost attribution."""

    __slots__ = ('input_tokens', 'output_tokens', 'cached_tokens')

    def __init__(self, input_tokens=0, output_tokens=0, cached_tokens=0):
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens
        self.cached_tokens = cached_tokens


def _client(unavailable_message=UNAVAILABLE_MESSAGE):
    """`unavailable_message` is threaded through because these two failures
    happen *before* the try/except around the call, so without it a CV upload
    reports "AI suggestions are not configured" — wording from a feature the
    user was not using."""
    if not settings.ANTHROPIC_API_KEY:
        raise SuggestionUnavailable(unavailable_message)

    try:
        import anthropic
    except ImportError as exc:  # pragma: no cover - dependency is in requirements
        raise SuggestionUnavailable(unavailable_message) from exc

    return anthropic.Anthropic(
        api_key=settings.ANTHROPIC_API_KEY,
        timeout=settings.AI_TIMEOUT_SECONDS,
        max_retries=1,
    )


def complete(
    system_prompt,
    user_content,
    output_format,
    max_tokens=None,
    unavailable_message=UNAVAILABLE_MESSAGE,
):
    """Run one structured-output call and return `(parsed, Usage)`.

    `system_prompt` must be a module-level constant from prompts.py — it carries
    the cache breakpoint, and caching is a prefix match, so anything built
    per-request here would silently cost full input price on every call.

    `max_tokens` and `unavailable_message` exist for the CV parse, whose output
    is an order of magnitude longer than a suggestion and whose failure needs
    different words — "your text is unchanged" is meaningless when the user
    uploaded a file. Both default to the suggestion behaviour, so that path is
    unchanged.
    """
    client = _client(unavailable_message)

    try:
        response = client.messages.parse(
            model=settings.AI_MODEL,
            max_tokens=max_tokens or MAX_TOKENS,
            # The cache breakpoint sits at the end of the system prompt, so the
            # rules and examples are the shared prefix and the user's content —
            # which differs every call — falls after it.
            system=[{
                'type': 'text',
                'text': system_prompt,
                'cache_control': {'type': 'ephemeral'},
            }],
            messages=[{'role': 'user', 'content': user_content}],
            output_format=output_format,
            # Short-form generation: quality here is set by the guardrails, not
            # by thinking depth, so the default `high` is money for nothing.
            output_config={'effort': settings.AI_EFFORT},
        )
    except Exception as exc:
        # Deliberately broad. Every upstream failure — auth, rate limit, timeout,
        # connection, refusal — is the same thing from the user's point of view:
        # the suggestion did not arrive and their text is untouched.
        logger.exception('Claude call failed: %s', exc)
        raise SuggestionUnavailable(unavailable_message) from exc

    if response.parsed_output is None:
        # The common cause is stop_reason='max_tokens': a structured output cut
        # off mid-object cannot be parsed, and arrives here indistinguishable
        # from a refusal. Logging the reason is the only way to tell them apart.
        logger.error('Claude returned no parsed output (stop_reason=%s)', response.stop_reason)
        raise SuggestionUnavailable(unavailable_message)

    usage = Usage(
        input_tokens=getattr(response.usage, 'input_tokens', 0) or 0,
        output_tokens=getattr(response.usage, 'output_tokens', 0) or 0,
        cached_tokens=getattr(response.usage, 'cache_read_input_tokens', 0) or 0,
    )

    return response.parsed_output, usage
