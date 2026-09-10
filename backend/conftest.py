"""Shared fixtures.

This is the repo's first test suite, so three things here are load-bearing:

- The cache is pointed at its own Redis database and flushed between tests. The
  preview cache and the single-flight lock both live in Redis, so without this
  the suite would both pollute the dev cache and leak state from one test into
  the next — and the single-flight test would pass for the wrong reason.
- The sample CV is deliberately small. Every render is ~360ms, so a fat fixture
  makes the suite slow enough that people stop running it.
- MEDIA_ROOT is redirected per test. Uploads and photos are real file writes, and
  without this they land in `backend/media/` and outlive the test.
"""

import re

import pytest
from django.contrib.auth import get_user_model
from django.core.cache import cache
from rest_framework.test import APIClient

from apps.cv_builder.models import (
    CVProfile,
    SkillCanonical,
    CVProject,
    CVSkill,
    Education,
    WorkBullet,
    WorkExperience,
)


def pytest_configure(config):
    """Isolate the test cache from the dev cache.

    Django swaps the database name for tests automatically; it does not do the
    same for Redis, so db 3 is claimed here (0 broker, 1 results, 2 app cache).

    The database number is swapped on whatever server is configured rather than
    hard-coding the Compose hostname, so the suite also runs against a Redis
    reachable some other way. A non-Redis cache is left alone.
    """
    from django.conf import settings

    cache = settings.CACHES['default']
    if 'redis' in cache['BACKEND'].lower():
        location = re.sub(r'/\d+$', '', cache.get('LOCATION', '') or '')
        cache['LOCATION'] = f'{location}/3'


@pytest.fixture(autouse=True)
def _clear_cache():
    """Every test starts with an empty cache, on both sides of the test.

    Clearing afterwards too keeps a failure from poisoning the next test.
    """
    cache.clear()
    yield
    cache.clear()


@pytest.fixture(autouse=True)
def _isolated_media(settings, tmp_path):
    """Every test gets its own MEDIA_ROOT.

    Uploads and photos would otherwise be written into `backend/media/`, which
    leaves litter behind, lets one test see another's files, and fails outright
    where that directory is a root-owned Docker volume.
    """
    settings.MEDIA_ROOT = tmp_path / 'media'
    settings.MEDIA_ROOT.mkdir(parents=True, exist_ok=True)
    return settings.MEDIA_ROOT


@pytest.fixture
def user(db):
    return get_user_model().objects.create_user(
        email='cv-tester@example.com',
        full_name='CV Tester',
        password='not-a-real-password',
        is_email_verified=True,
    )


@pytest.fixture
def other_user(db):
    return get_user_model().objects.create_user(
        email='someone-else@example.com',
        full_name='Someone Else',
        password='not-a-real-password',
        is_email_verified=True,
    )


@pytest.fixture
def api(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.fixture
def empty_cv(user):
    """A freshly created shell, the state a brand new user is in."""
    return CVProfile.objects.create(user=user, email=user.email)


@pytest.fixture
def sample_cv(user):
    """A realistic but minimal CV: one role with two bullets, one degree,
    five skills, one project. Enough to exercise every template section
    without paying for a three-page render on every test."""
    cv = CVProfile.objects.create(
        user=user,
        full_name='Ada Lovelace',
        professional_title='Backend Engineer',
        email=user.email,
        phone='+44 20 7946 0000',
        city='London',
        country='United Kingdom',
        summary=(
            'Backend engineer with six years building payment systems in Python. '
            'Owns services end to end, from schema design through on-call.'
        ),
        template_id='minimal',
    )

    experience = WorkExperience.objects.create(
        cv=cv,
        company_name='Analytical Engines Ltd',
        role_title='Senior Backend Engineer',
        employment_type='full_time',
        location='London',
        location_type='hybrid',
        start_month=3,
        start_year=2021,
        is_current=True,
    )
    WorkBullet.objects.create(
        experience=experience,
        text='Cut checkout latency by 40% by replacing synchronous fraud checks.',
        order=0,
    )
    WorkBullet.objects.create(
        experience=experience,
        text='Raised service test coverage from 54% to 93% over two quarters.',
        order=1,
    )

    Education.objects.create(
        cv=cv,
        institution='University of London',
        degree_type='bs',
        field_of_study='Computer Science',
        start_year=2013,
        end_year=2017,
    )

    for index, name in enumerate(['Python', 'Django', 'PostgreSQL', 'Redis', 'Docker']):
        CVSkill.objects.create(cv=cv, name=name, category='Tools', order=index)

    CVProject.objects.create(
        cv=cv,
        name='Ledger',
        description='Double-entry ledger service handling 2M transactions a day.',
        tech_stack=['Python', 'PostgreSQL'],
        start_year=2022,
    )

    cv.refresh_from_db()
    return cv


@pytest.fixture
def canonical_skills(db):
    """A handful of real canonical rows.

    Includes the Java / JavaScript pair on purpose: the alias lookup is an
    `icontains` query, so that pair is the case where a naive resolver silently
    relabels one skill as the other.
    """
    rows = [
        ('Python', ['py', 'python3'], 'Languages'),
        ('JavaScript', ['js', 'ecmascript'], 'Languages'),
        ('Java', ['java se'], 'Languages'),
        ('PostgreSQL', ['postgres', 'psql'], 'Databases'),
        ('Redis', [], 'Databases'),
        ('Django', ['django rest framework'], 'Frameworks'),
    ]
    return [
        SkillCanonical.objects.create(
            canonical_name=name, aliases=aliases, category=category, is_popular=True,
        )
        for name, aliases, category in rows
    ]


@pytest.fixture
def ai_enabled(settings):
    """A key-shaped value so the client builds. No call is ever made — every AI
    test patches `complete`, because a test suite must never spend money."""
    settings.ANTHROPIC_API_KEY = 'test-key-not-a-real-credential'
    settings.AI_MONTHLY_CREDITS = 60
    return settings
