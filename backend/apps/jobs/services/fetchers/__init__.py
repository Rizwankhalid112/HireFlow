"""One fetcher per platform, resolved by the company's `platform` value."""

from apps.jobs.services.fetchers import ashby, greenhouse, lever, workable
from apps.jobs.services.fetchers.base import FetchError, pause

FETCHERS = {
    'greenhouse': greenhouse.fetch,
    'ashby': ashby.fetch,
    'lever': lever.fetch,
    'workable': workable.fetch,
}


def fetch_for(platform, slug):
    try:
        fetcher = FETCHERS[platform]
    except KeyError:
        raise FetchError(f'No fetcher for platform {platform!r}.')
    return fetcher(slug)


__all__ = ['FETCHERS', 'FetchError', 'fetch_for', 'pause']
