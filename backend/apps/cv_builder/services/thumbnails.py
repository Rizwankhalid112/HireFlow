"""Gallery thumbnails: each template rendered with the demo CV, as a PNG.

Goes through the same WeasyPrint path as the real export, so a thumbnail is a
faithful picture of what that template produces — the gallery cannot drift from
the output the way a hand-drawn mockup would.

The sample data is fixed, so a rendered thumbnail is valid until the template
itself changes; it is cached aggressively and contains no user data.
"""

import io
import logging

from django.core.cache import cache
from django.template.loader import render_to_string

from apps.cv_builder.services.sample_cv import sample_context
from apps.cv_builder.templates_registry import get_template

logger = logging.getLogger(__name__)

CACHE_TTL = 60 * 60 * 24 * 7  # a week; sample data never changes
THUMBNAIL_SCALE = 1.4  # ~1100px wide from A4, sharp on retina cards


class ThumbnailError(Exception):
    """Raised when a thumbnail cannot be produced."""


def _cache_key(template_id):
    return f'cv:thumb:{template_id}:{THUMBNAIL_SCALE}'


def render_template_thumbnail(template_id, use_cache=True):
    """PNG bytes of `template_id` rendered with the demo CV."""
    template = get_template(template_id)
    if not template:
        raise ThumbnailError(f'Unknown template: {template_id}')

    key = _cache_key(template_id)
    if use_cache:
        cached = cache.get(key)
        if cached:
            return cached

    html_string = render_to_string(template['file'], sample_context(template))

    try:
        from weasyprint import HTML
    except OSError as exc:
        raise ThumbnailError('PDF rendering libraries are unavailable.') from exc

    try:
        import pypdfium2 as pdfium

        pdf_bytes = HTML(string=html_string).write_pdf()

        # Only the first page — a gallery card shows one page.
        # Close explicitly: pypdfium2 holds native handles, and leaving them to
        # the GC leaks in a long-lived gunicorn worker.
        document = pdfium.PdfDocument(pdf_bytes)
        try:
            page = document[0]
            try:
                image = page.render(scale=THUMBNAIL_SCALE).to_pil()
            finally:
                page.close()
        finally:
            document.close()

        buffer = io.BytesIO()
        image.save(buffer, format='PNG', optimize=True)
        png_bytes = buffer.getvalue()
    except Exception as exc:
        logger.exception('Thumbnail failed for template %s: %s', template_id, exc)
        raise ThumbnailError('Could not render the template preview.') from exc

    if use_cache:
        cache.set(key, png_bytes, CACHE_TTL)

    return png_bytes
