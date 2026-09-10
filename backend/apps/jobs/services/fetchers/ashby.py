"""Ashby — cleanest of the four.

Descriptions come as plain text, `publishedAt` was verified against the job
page's published date and matched exactly, and `isRemote` is a real boolean.
Compensation exists but is a per-company opt-in: 97% populated on one board,
0% on another, which is why salary is display-only and never a filter.
"""

from apps.jobs.services import normalise
from apps.jobs.services.fetchers.base import get_json

ENDPOINT = 'https://api.ashbyhq.com/posting-api/job-board/{slug}?includeCompensation=true'
SOURCE = 'ashby'


def fetch(slug):
    payload = get_json(ENDPOINT.format(slug=slug))
    out = []
    for job in payload.get('jobs') or []:
        location = job.get('location') or ''
        workplace = (job.get('workplaceType') or '').lower()
        if job.get('isRemote'):
            remote = 'remote'
        elif workplace in ('hybrid', 'onsite'):
            remote = workplace
        else:
            remote = normalise.detect_remote(location)
        compensation = job.get('compensation') or {}
        out.append(normalise.normalised(
            source=SOURCE,
            external_id=str(job.get('id') or ''),
            company_name=payload.get('name') or slug,
            title=job.get('title') or '',
            description=job.get('descriptionPlain') or '',
            apply_url=job.get('applyUrl') or job.get('jobUrl') or '',
            location_raw=location,
            remote_type=remote,
            employment_type=job.get('employmentType') or '',
            department=job.get('department') or '',
            salary_text=compensation.get('compensationTierSummary') or '',
            posted_at=normalise.parse_date(job.get('publishedAt')),
        ))
    return out
