"""The single model call.

One place builds a request, so provider choice, caching, timeouts and error
mapping are decided once rather than per section.

Two providers are supported and nothing above this file can tell which one ran:
`complete()` takes a Pydantic class and returns an instance of it either way.
Everything that makes a suggestion good — the prompts, the schemas, the
anti-fabrication guardrails — lives above this boundary and is provider-neutral,
which is the only reason a swap is a file rather than a project.
"""

import json
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


def provider():
    """Which backend serves the AI features.

    Inferred from whichever key is present rather than demanding a third
    setting, so a deployment turns AI on by supplying one key and nothing else.
    `AI_PROVIDER` overrides the inference, which only matters when both keys are
    set and the choice is deliberate.
    """
    explicit = (getattr(settings, 'AI_PROVIDER', '') or '').strip().lower()
    if explicit:
        return explicit
    if settings.ANTHROPIC_API_KEY:
        return 'anthropic'
    if getattr(settings, 'GEMINI_API_KEY', ''):
        return 'gemini'
    return ''


def is_configured():
    """Whether the deployment can serve AI at all.

    Read by the credits endpoint, which the navigation uses to decide whether to
    offer AI features — so it answers a question about the deployment, not about
    the user or their allowance.
    """
    name = provider()
    if name == 'anthropic':
        return bool(settings.ANTHROPIC_API_KEY)
    if name == 'gemini':
        return bool(getattr(settings, 'GEMINI_API_KEY', ''))
    return False


def _require(key, unavailable_message):
    """`unavailable_message` is threaded through because a missing key and a
    missing dependency both fail *before* the try/except around the call, so
    without it a CV upload reports "AI suggestions are not configured" — wording
    from a feature the user was not using."""
    if not key:
        raise SuggestionUnavailable(unavailable_message)


def _complete_anthropic(system_prompt, user_content, output_format, max_tokens, unavailable_message):
    _require(settings.ANTHROPIC_API_KEY, unavailable_message)

    try:
        import anthropic
    except ImportError as exc:  # pragma: no cover - dependency is in requirements
        raise SuggestionUnavailable(unavailable_message) from exc

    client = anthropic.Anthropic(
        api_key=settings.ANTHROPIC_API_KEY,
        timeout=settings.AI_TIMEOUT_SECONDS,
        max_retries=1,
    )

    response = client.messages.parse(
        model=settings.AI_MODEL,
        max_tokens=max_tokens,
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


def _complete_gemini(system_prompt, user_content, output_format, max_tokens, unavailable_message):
    """The same call against Google's API, for deployments running on its free tier.

    Two differences from the Anthropic path are worth stating rather than
    leaving to be discovered:

    There is no cache breakpoint to place. Gemini caches long shared prefixes
    implicitly, so the saving the `cache_control` marker buys above is either
    automatic here or absent — nothing to configure either way.

    Thinking tokens are drawn from the same budget as the answer, so a model
    left to think freely on a long schema can spend the whole allowance before
    the object is finished and return no parsed output at all. That is why the
    level is set rather than defaulted — measured on gemini-3.6-flash, one
    summary call left to itself spent 572 thinking tokens on a 130-token answer.
    """
    key = getattr(settings, 'GEMINI_API_KEY', '')
    _require(key, unavailable_message)

    try:
        from google import genai
        from google.genai import types
    except ImportError as exc:  # pragma: no cover - dependency is in requirements
        raise SuggestionUnavailable(unavailable_message) from exc

    client = genai.Client(
        api_key=key,
        http_options=types.HttpOptions(
            # Milliseconds here, unlike every other timeout in this project.
            timeout=settings.AI_TIMEOUT_SECONDS * 1000,
            # The SDK would otherwise try five times with a backoff reaching a
            # minute, which outlives the worker that is waiting on it. Bounded
            # here so the whole call fits inside one request -- see the note in
            # settings.
            retry_options=types.HttpRetryOptions(
                attempts=getattr(settings, 'AI_RETRY_ATTEMPTS', 2),
                initial_delay=1.0,
                max_delay=4.0,
            ),
        ),
    )

    config = {
        'system_instruction': system_prompt,
        'response_mime_type': 'application/json',
        # The converted schema rather than the Pydantic class, because the
        # blanks above have to be rewritten after conversion. The cost is that
        # the SDK no longer validates for us — see below.
        'response_schema': types.Schema.from_json_schema(
            json_schema=types.JSONSchema(**_hide_enum_blanks(output_format.model_json_schema())),
        ),
        'max_output_tokens': max_tokens,
        # Nothing here passes tools, and leaving this on makes the SDK warn on
        # every call about a feature we do not use.
        'automatic_function_calling': types.AutomaticFunctionCallingConfig(disable=True),
    }

    level = (getattr(settings, 'GEMINI_THINKING_LEVEL', '') or '').strip()
    if level:
        config['thinking_config'] = types.ThinkingConfig(thinking_level=level)

    # Falling through the preference order on the two failures that are about
    # capacity rather than the request: a daily quota that is spent (429) and a
    # model that is momentarily full (503). Anything else is our bug or theirs,
    # and retrying it on a second model would only hide it.
    models = [m.strip() for m in settings.GEMINI_MODEL.split(',') if m.strip()]
    response = None
    for index, name in enumerate(models):
        try:
            response = client.models.generate_content(
                model=name,
                contents=user_content,
                config=types.GenerateContentConfig(**config),
            )
            break
        except Exception as exc:
            if getattr(exc, 'code', None) not in (429, 503) or index == len(models) - 1:
                raise
            logger.warning('Gemini model %s unavailable (%s) — falling through to %s',
                           name, getattr(exc, 'code', '?'), models[index + 1])

    text = response.text
    if not text:
        # Same class of failure as the Anthropic branch, and the same need to
        # record why: MAX_TOKENS is a truncated object, SAFETY is a refusal, and
        # they are indistinguishable to the caller.
        candidates = response.candidates or []
        reason = getattr(candidates[0], 'finish_reason', None) if candidates else None
        logger.error('Gemini returned no output (finish_reason=%s)', reason)
        raise SuggestionUnavailable(unavailable_message)

    try:
        # Validation is ours because we passed a schema rather than the model.
        # ValueError covers both halves: JSONDecodeError for a truncated object
        # and pydantic's ValidationError for a well-formed but wrong one.
        parsed = output_format.model_validate(_restore_blanks(json.loads(text)))
    except ValueError as exc:
        logger.error('Gemini output did not validate against %s: %s',
                     output_format.__name__, exc)
        raise SuggestionUnavailable(unavailable_message) from exc

    meta = response.usage_metadata
    usage = Usage(
        input_tokens=getattr(meta, 'prompt_token_count', 0) or 0,
        # Thinking is billed as output, so it belongs in the output count even
        # though the user never sees those tokens.
        output_tokens=(getattr(meta, 'candidates_token_count', 0) or 0)
        + (getattr(meta, 'thoughts_token_count', 0) or 0),
        cached_tokens=getattr(meta, 'cached_content_token_count', 0) or 0,
    )
    return parsed, usage


# Gemini rejects an empty string as an enum member. Six fields on the CV-parse
# schema use one to mean "the document did not say" — and that value *is* the
# anti-invention mechanism: without it the model has to pick an employment type
# for a role that never stated one. So it crosses the wire as a sentinel and is
# restored on the way back, rather than dropped.
#
# The sentinel is deliberately unpronounceable: restoration rewrites any string
# equal to it, and a plain word like "unspecified" could legitimately appear in
# a summary the model wrote.
_ABSENT = '__absent__'


def _hide_enum_blanks(node):
    """Rewrite '' to the sentinel anywhere an enum admits it."""
    if isinstance(node, dict):
        enum = node.get('enum')
        if isinstance(enum, list) and '' in enum:
            node['enum'] = [_ABSENT if v == '' else v for v in enum]
        for value in node.values():
            _hide_enum_blanks(value)
    elif isinstance(node, list):
        for value in node:
            _hide_enum_blanks(value)
    return node


def _restore_blanks(node):
    """And back, so nothing above this file ever sees the sentinel."""
    if isinstance(node, dict):
        return {k: _restore_blanks(v) for k, v in node.items()}
    if isinstance(node, list):
        return [_restore_blanks(v) for v in node]
    return '' if node == _ABSENT else node


_PROVIDERS = {'anthropic': _complete_anthropic, 'gemini': _complete_gemini}


def complete(
    system_prompt,
    user_content,
    output_format,
    max_tokens=None,
    unavailable_message=UNAVAILABLE_MESSAGE,
):
    """Run one structured-output call and return `(parsed, Usage)`.

    `system_prompt` must be a module-level constant from prompts.py — on the
    Anthropic path it carries the cache breakpoint, and caching is a prefix
    match, so anything built per-request here would silently cost full input
    price on every call.

    `max_tokens` and `unavailable_message` exist for the CV parse, whose output
    is an order of magnitude longer than a suggestion and whose failure needs
    different words — "your text is unchanged" is meaningless when the user
    uploaded a file. Both default to the suggestion behaviour, so that path is
    unchanged.
    """
    run = _PROVIDERS.get(provider())
    if run is None:
        # No key, or a name nobody implements. Either way the feature is off.
        raise SuggestionUnavailable(unavailable_message)

    try:
        return run(
            system_prompt,
            user_content,
            output_format,
            max_tokens or MAX_TOKENS,
            unavailable_message,
        )
    except SuggestionUnavailable:
        # Already mapped, already logged — re-raising through the broad catch
        # below would bury the reason under a second, vaguer one.
        raise
    except Exception as exc:
        # Deliberately broad. Every upstream failure — auth, rate limit, timeout,
        # connection, refusal — is the same thing from the user's point of view:
        # the suggestion did not arrive and their text is untouched.
        logger.exception('%s call failed: %s', provider(), exc)
        raise SuggestionUnavailable(unavailable_message) from exc
