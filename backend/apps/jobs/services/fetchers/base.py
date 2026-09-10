"""Shared HTTP behaviour for every fetcher.

One place decides how we behave as a client of someone else's service: a real
User-Agent that identifies us, a timeout, a bounded retry, and a pause between
requests. No platform we tested publishes a rate limit, but undocumented is not
the same as absent.
"""

import logging
import time

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

USER_AGENT = getattr(
    settings, 'JOBS_USER_AGENT',
    'HireFlow/1.0 (job aggregator; +https://hireflow.com)',
)
TIMEOUT = getattr(settings, 'JOBS_FETCH_TIMEOUT', 45)
PAUSE_SECONDS = getattr(settings, 'JOBS_FETCH_PAUSE', 1.0)
MAX_RETRIES = 2


class FetchError(Exception):
    """The source could not be read. Carries a message worth storing on the row."""


_session = None


def session():
    global _session
    if _session is None:
        _session = requests.Session()
        _session.headers['User-Agent'] = USER_AGENT
        _session.headers['Accept'] = 'application/json, text/plain, */*'
    return _session


def get_json(url, timeout=None):
    """One GET returning parsed JSON, with a short bounded retry.

    Retries only transient failures. A 404 is a wrong slug and will never
    succeed, so it fails immediately rather than three times slowly.
    """
    last = None
    for attempt in range(MAX_RETRIES + 1):
        try:
            response = session().get(url, timeout=timeout or TIMEOUT)
            if response.status_code == 404:
                raise FetchError('Not found — check the company slug.')
            if response.status_code == 429:
                raise FetchError('Rate limited by the source.')
            response.raise_for_status()
            return response.json()
        except FetchError:
            raise
        except ValueError as exc:
            raise FetchError(f'Source did not return JSON: {exc}') from exc
        except requests.RequestException as exc:
            last = exc
            if attempt < MAX_RETRIES:
                # Linear backoff is enough here: these are slow-but-healthy
                # services, not contended ones.
                time.sleep(1.5 * (attempt + 1))
    raise FetchError(f'Could not reach the source: {last}')


def pause():
    """Politeness gap between companies. Cheap insurance against a limit we
    cannot see."""
    time.sleep(PAUSE_SECONDS)
