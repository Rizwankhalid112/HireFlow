"""Greenhouse — the largest single source.

`?content=true` returns every job with its full description in one request; a
616-job board came back in 4.6 MB and 1.3 seconds. There is no pagination.

Two quirks handled here:

- The description is **HTML that has been entity-encoded**, so it arrives as
  `&lt;h2&gt;`. `clean_description` unescapes before stripping.
- **There is no remote/onsite field at all.** It is inferred from the location
  and description, and left blank when the wording does not support a guess.

`first_published` is used for `posted_at`. It is exact for the large majority and
too old for reposted requisitions — an error that only ever makes a job look
older than it is, which is the safe direction.
"""

from apps.jobs.services import normalise
from apps.jobs.services.fetchers.base import get_json

ENDPOINT = 'https://boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=true'
SOURCE = 'greenhouse'


def fetch(slug):
    payload = get_json(ENDPOINT.format(slug=slug))
    out = []
    for job in payload.get('jobs') or []:
        location = (job.get('location') or {}).get('name') or ''
        description = normalise.clean_description(job.get('content'), is_html=True)
        departments = job.get('departments') or []
        out.append(normalise.normalised(
            source=SOURCE,
            external_id=str(job.get('id') or ''),
            company_name=job.get('company_name') or '',
            title=job.get('title') or '',
            description=description,
            apply_url=job.get('absolute_url') or '',
            location_raw=location,
            remote_type=normalise.detect_remote(location, description[:600]),
            department=(departments[0].get('name') if departments else ''),
            posted_at=normalise.parse_date(job.get('first_published')),
        ))
    return out
