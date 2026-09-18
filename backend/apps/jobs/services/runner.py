"""Run the daily gather across every tracked company.

One company failing must never stop the run — a wrong slug, an outage or a
change of shape at one employer is normal and expected. Each company is fetched,
recorded and reported independently, and its outcome is written back to
`TrackedCompany` so a board that quietly stopped returning jobs is visible
rather than silently absent.

Companies are fetched **concurrently across platforms** because Lever is 5-20
seconds per request while the others are around one; a serial run would spend
most of its time waiting on Lever alone.
"""

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

from django.conf import settings
from django.core.cache import cache
from django.utils import timezone

from apps.jobs.constants import JOB_STATS_CACHE_KEY
from apps.jobs.models import TrackedCompany
from apps.jobs.services.fetchers import FetchError, fetch_for, pause
from apps.jobs.services.ingest import purge_stale, upsert_jobs

logger = logging.getLogger(__name__)

# Modest: these are someone else's servers and the work is IO-bound. Enough to
# stop Lever dominating the wall time, not so many that we look like a flood.
MAX_WORKERS = getattr(settings, 'JOBS_FETCH_WORKERS', 4)

# After this many consecutive failures a company stops being fetched. Almost
# always a slug that was wrong from the start; retrying it nightly forever is
# noise in the logs and wasted requests.
FAILURE_LIMIT = 5


def fetch_company(company):
    """Fetch and store one company. Returns a result dict; never raises."""
    result = {'company': company.name, 'platform': company.platform, 'written': 0, 'error': None}
    try:
        rows = fetch_for(company.platform, company.slug)
        written, skipped = upsert_jobs(rows, company=company)
        result.update(written=written, skipped=skipped, fetched=len(rows))

        company.last_fetched_at = timezone.now()
        company.last_fetch_status = f'ok — {written} jobs'
        company.last_job_count = written
        company.consecutive_failures = 0
    except FetchError as exc:
        result['error'] = str(exc)
        company.last_fetched_at = timezone.now()
        company.last_fetch_status = f'error — {exc}'[:200]
        company.consecutive_failures += 1
    except Exception as exc:
        # Deliberately broad: an unexpected shape from one employer must not end
        # the run for the other 499.
        logger.exception('Unexpected failure fetching %s', company)
        result['error'] = f'{type(exc).__name__}: {exc}'
        company.last_fetched_at = timezone.now()
        company.last_fetch_status = f'error — {type(exc).__name__}'[:200]
        company.consecutive_failures += 1

    if company.consecutive_failures >= FAILURE_LIMIT:
        company.is_active = False
        company.last_fetch_status = f'disabled after {FAILURE_LIMIT} failures'
        logger.warning('Disabled %s after %d consecutive failures', company, FAILURE_LIMIT)

    company.save(update_fields=[
        'last_fetched_at', 'last_fetch_status', 'last_job_count',
        'consecutive_failures', 'is_active',
    ])
    return result


def run_gather(companies=None, purge_days=None, workers=MAX_WORKERS):
    """The whole daily job. Returns a summary dict."""
    queryset = companies if companies is not None else TrackedCompany.objects.filter(is_active=True)
    companies = list(queryset)
    started = timezone.now()
    results = []

    if workers <= 1:
        # Serial, in this thread. Used by tests and by `--workers 1` when
        # debugging: a worker thread gets its own database connection, which
        # cannot see data written by an open transaction in the caller.
        results = [_fetch_with_pause(c) for c in companies]
    else:
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = {pool.submit(_fetch_with_pause, c): c for c in companies}
            for future in as_completed(futures):
                results.append(future.result())

    purge_days = purge_days if purge_days is not None else getattr(settings, 'JOBS_RETENTION_DAYS', 45)
    purged = purge_stale(purge_days)

    # The stats endpoint caches a whole-table count. This run is the only thing
    # that changes it, so drop the entry rather than making every reader wait
    # out the TTL to see tonight's jobs.
    cache.delete(JOB_STATS_CACHE_KEY)

    summary = {
        'companies': len(companies),
        'succeeded': sum(1 for r in results if not r['error']),
        'failed': sum(1 for r in results if r['error']),
        'jobs_written': sum(r['written'] for r in results),
        'purged': purged,
        'seconds': round((timezone.now() - started).total_seconds(), 1),
        'errors': [(r['company'], r['error']) for r in results if r['error']],
    }
    logger.info('Job gather finished: %s', summary)
    return summary


def _fetch_with_pause(company):
    result = fetch_company(company)
    # Politeness gap held inside the worker, so concurrency does not multiply
    # into a burst against one host.
    pause()
    return result
