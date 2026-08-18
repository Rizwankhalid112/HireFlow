"""The single render path.

Preview and download both call render_cv_pdf() and receive the same bytes, so
the on-screen preview cannot drift from the downloaded file — they are the same
artifact, differing only in Content-Disposition.
"""

import hashlib
import logging

from django.conf import settings
from django.core.cache import cache
from django.template.loader import render_to_string

from apps.cv_builder.services.cv_context import build_cv_context
from apps.cv_builder.templates_registry import resolve_template

logger = logging.getLogger(__name__)

CACHE_TTL = 60 * 60  # 1 hour


class RenderError(Exception):
    """Raised when WeasyPrint cannot produce a document."""


def _cache_key(cv, template_id):
    """Rotates whenever content changes — the child-model signals bump
    content_updated_at, so edits invalidate this automatically."""
    stamp = cv.content_updated_at.timestamp() if cv.content_updated_at else 0
    photo = cv.photo.name if cv.photo else ''
    raw = f'{cv.id}:{template_id}:{stamp}:{photo}'
    digest = hashlib.sha256(raw.encode()).hexdigest()[:32]
    return f'cv:pdf:{digest}'


def render_cv_pdf(cv, template_id=None, use_cache=True):
    """Render `cv` and return (pdf_bytes, page_count).

    page_count comes from the laid-out document, so overflow is measured rather
    than estimated.
    """
    template = resolve_template(template_id or cv.template_id)
    key = _cache_key(cv, template_id or cv.template_id or '')

    if use_cache:
        cached = cache.get(key)
        if cached:
            return cached['pdf'], cached['page_count']

    context = build_cv_context(cv, template)
    html_string = render_to_string(template['file'], context)

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

    page_count = len(document.pages)

    if use_cache:
        cache.set(key, {'pdf': pdf_bytes, 'page_count': page_count}, CACHE_TTL)

    return pdf_bytes, page_count


def render_cv_meta(cv, template_id=None):
    """Page count and overflow flag for the fit banner."""
    template = resolve_template(template_id or cv.template_id)
    _, page_count = render_cv_pdf(cv, template_id)

    return {
        'page_count': page_count,
        'max_pages': template['max_pages'],
        'overflows': page_count > template['max_pages'],
    }
