"""Proves the harness runs: settings load, the database is reachable, the cache
is the isolated one, and an authenticated request gets through."""

import pytest
from django.conf import settings
from django.core.cache import cache


def test_cache_is_isolated_from_the_dev_database():
    # Guards against the suite quietly writing into the running app's cache.
    if 'redis' in settings.CACHES['default']['BACKEND'].lower():
        assert settings.CACHES['default']['LOCATION'].endswith('/3')


def test_cache_round_trips():
    cache.set('smoke', 'ok', 30)
    assert cache.get('smoke') == 'ok'


@pytest.mark.django_db
def test_authenticated_request_reaches_the_cv_api(api):
    response = api.get('/api/cv/templates/')
    assert response.status_code == 200
    assert len(response.json()) == 6
