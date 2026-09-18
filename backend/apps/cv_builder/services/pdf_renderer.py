"""The single render path.

Preview and download both call render_cv_pdf() and receive the same bytes, so
the on-screen preview cannot drift from the downloaded file — they are the same
artifact, differing only in Content-Disposition.

Because the live preview re-renders on every section save, three things guard
the two gunicorn workers from the load: a content-addressed cache, a
single-flight lock so duplicate concurrent requests share one render, and an
ETag so an unchanged CV costs a 304 instead of a render.
"""

import hashlib
import json
import logging
import time

from django.conf import settings
from django.core.cache import cache
from django.template.loader import render_to_string

from apps.cv_builder.services.cv_context import build_cv_context
from apps.cv_builder.templates_registry import resolve_template, resolve_template_id

logger = logging.getLogger(__name__)

CACHE_TTL = 60 * 60  # 1 hour

# The lock is a crash guard, not a queue: 30s is far longer than a render
# (~360ms) but short enough that a worker killed mid-render frees it quickly.
LOCK_TTL = 30
LOCK_WAIT_SECONDS = 2.0
LOCK_POLL_SECONDS = 0.05


class RenderError(Exception):
    """Raised when WeasyPrint cannot produce a document."""


class RenderPlan:
    """Everything needed to render, plus the digest identifying the result.

    Built without rendering, so a view can answer If-None-Match from the digest
    alone and skip WeasyPrint entirely.
    """

    __slots__ = ('template', 'template_id', 'context', 'digest', 'cache_key')

    def __init__(self, template, template_id, context, digest):
        self.template = template
        self.template_id = template_id
        self.context = context
        self.digest = digest
        self.cache_key = f'cv:pdf:{digest}'


def _content_digest(context, template_id):
    """Hash the built context, not a timestamp.

    content_updated_at is auto_now, so *any* save bumps it — including the
    template_id PATCH the picker fires — which busted the cache for every
    template on every click. Narrowing that field's meaning is not an option:
    two Celery retention tasks (the 23-day reminder and the 30-day draft
    deletion) read it, and a user browsing templates would start getting
    deletion reminders. Hashing the content instead leaves retention untouched
    and makes flipping between templates genuinely free.

    `template` is excluded from the payload because it is static per id and the
    id is hashed separately — so the digest reflects user content only.
    """
    payload = {key: value for key, value in context.items() if key != 'template'}
    raw = json.dumps(payload, sort_keys=True, default=str)
    return hashlib.sha256(f'{template_id}\x00{raw}'.encode()).hexdigest()[:32]


def build_render_plan(cv, template_id=None):
    """Resolve the template, build the context, derive the digest. No render.

    Costs a handful of queries (~5ms) to avoid a ~360ms render.
    """
    requested = template_id or cv.template_id
    resolved_id = resolve_template_id(requested)
    template = resolve_template(requested)
    context = build_cv_context(cv, template)

    return RenderPlan(
        template=template,
        template_id=resolved_id,
        context=context,
        digest=_content_digest(context, resolved_id),
    )


def _render(plan, cv):
    """WeasyPrint. The expensive part — everything else exists to avoid it."""
    html_string = render_to_string(plan.template['file'], plan.context)

    # Imported lazily: WeasyPrint pulls in Pango at import time, and keeping it
    # out of module scope means the rest of the app still boots if the system
    # libraries are missing.
    try:
        from weasyprint import HTML
    except OSError as exc:  # missing libpango et al.
        raise RenderError(
            'PDF rendering libraries are unavailable. Rebuild the backend image.'
        ) from exc

    try:
        # base_url lets WeasyPrint resolve the photo from disk rather than over
        # HTTP — no network call, no auth problem.
        document = HTML(string=html_string, base_url=str(settings.MEDIA_ROOT)).render()
        pdf_bytes = document.write_pdf()
    except Exception as exc:
        logger.exception('WeasyPrint failed for CV %s: %s', cv.id, exc)
        raise RenderError('Could not generate your CV PDF.') from exc

    return {'pdf': pdf_bytes, 'page_count': len(document.pages)}


def _render_single_flight(plan, cv):
    """Render under a lock so N identical concurrent requests cost one render.

    cache.add() is set-if-absent, which Redis implements atomically. Losers wait
    for the winner's cache entry rather than starting their own render — with
    only a handful of workers, three rapid saves must not become three renders.
    """
    lock_key = f'{plan.cache_key}:lock'
    acquired = cache.add(lock_key, 1, LOCK_TTL)

    if not acquired:
        deadline = time.monotonic() + LOCK_WAIT_SECONDS
        while time.monotonic() < deadline:
            time.sleep(LOCK_POLL_SECONDS)
            cached = cache.get(plan.cache_key)
            if cached:
                return cached
        # The holder died or is unusually slow. Render rather than deadlock —
        # a duplicate render is far better than a hung request.
        logger.warning('Preview lock wait timed out for CV %s', cv.id)

    try:
        result = _render(plan, cv)
        cache.set(plan.cache_key, result, CACHE_TTL)
        return result
    finally:
        if acquired:
            cache.delete(lock_key)


def render_from_plan(cv, plan, use_cache=True):
    """Render `plan`, or return the cached bytes for its digest."""
    if not use_cache:
        return _render(plan, cv)

    cached = cache.get(plan.cache_key)
    if cached:
        return cached

    return _render_single_flight(plan, cv)


def render_cv_pdf(cv, template_id=None, use_cache=True):
    """Render `cv` and return (pdf_bytes, page_count).

    page_count comes from the laid-out document, so overflow is measured rather
    than estimated.
    """
    plan = build_render_plan(cv, template_id)
    result = render_from_plan(cv, plan, use_cache=use_cache)
    return result['pdf'], result['page_count']


def render_cv_meta(cv, template_id=None):
    """Page count and overflow flag for the fit banner."""
    plan = build_render_plan(cv, template_id)
    result = render_from_plan(cv, plan)

    return {
        'page_count': result['page_count'],
        'max_pages': plan.template['max_pages'],
        'overflows': result['page_count'] > plan.template['max_pages'],
    }
