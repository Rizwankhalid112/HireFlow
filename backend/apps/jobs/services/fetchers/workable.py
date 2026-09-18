"""Workable — flat fields, raw HTML descriptions.

The `details=true` response differs from the published documentation: location
is not a nested object but flat `city` / `country` / `state` keys, with
`telecommuting` as the remote flag. Written against the real response.
"""

from apps.jobs.services import normalise
from apps.jobs.services.fetchers.base import get_json

ENDPOINT = 'https://apply.workable.com/api/v1/widget/accounts/{slug}?details=true'
SOURCE = 'workable'


def fetch(slug):
    payload = get_json(ENDPOINT.format(slug=slug))
    company = payload.get('name') or slug
    out = []
    for job in payload.get('jobs') or []:
        location = ', '.join(
            part for part in [job.get('city'), job.get('country')] if part
        )
        out.append(normalise.normalised(
            source=SOURCE,
            external_id=str(job.get('shortcode') or job.get('id') or ''),
            company_name=company,
            title=job.get('title') or '',
            description=normalise.clean_description(job.get('description'), is_html=True),
            apply_url=job.get('url') or job.get('application_url') or '',
            location_raw=location,
            remote_type='remote' if job.get('telecommuting') else normalise.detect_remote(location),
            employment_type=job.get('employment_type') or '',
            department=job.get('department') or '',
            posted_at=normalise.parse_date(job.get('published_on') or job.get('created_at')),
        ))
    return out
