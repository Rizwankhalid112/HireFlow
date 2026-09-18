"""Lever — accurate but slow.

The response is a bare array, not an object. `createdAt` is epoch milliseconds
and was verified against the job page's published date: they match exactly. Some
listings are genuinely years old — one tested board publishes a live role as
posted in 2009 — which is a fact about the employer, not a defect in the feed.

Measured at 5–20 seconds per company, consistently. It is the slowest source by
a wide margin and the reason the daily run fetches platforms concurrently.
"""

from apps.jobs.services import normalise
from apps.jobs.services.fetchers.base import get_json

ENDPOINT = 'https://api.lever.co/v0/postings/{slug}?mode=json'
SOURCE = 'lever'
TIMEOUT = 60


def fetch(slug):
    payload = get_json(ENDPOINT.format(slug=slug), timeout=TIMEOUT)
    if not isinstance(payload, list):
        return []
    out = []
    for job in payload:
        categories = job.get('categories') or {}
        location = categories.get('location') or ''
        workplace = (job.get('workplaceType') or '').lower()
        remote = workplace if workplace in ('remote', 'hybrid', 'onsite') else \
            normalise.detect_remote(location, categories.get('commitment'))
        out.append(normalise.normalised(
            source=SOURCE,
            external_id=str(job.get('id') or ''),
            company_name=slug,
            title=job.get('text') or '',
            description=job.get('descriptionPlain') or '',
            apply_url=job.get('hostedUrl') or job.get('applyUrl') or '',
            location_raw=location,
            remote_type=remote,
            employment_type=categories.get('commitment') or '',
            department=categories.get('department') or '',
            posted_at=normalise.parse_date(job.get('createdAt')),
        ))
    return out
