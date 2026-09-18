"""Ranking jobs against the skills on a user's CV.

Deterministic skill overlap, not an AI call — so these tests assert real
behaviour rather than mocking a model.
"""

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.cv_builder.models import CVSkill
from apps.jobs.models import ATSPlatform, TrackedCompany
from apps.jobs.services.cv_ranking import (
    NotEnoughSkills,
    cv_skill_terms,
    matched_skills_for,
    rank_by_cv,
)
from apps.jobs.services.ingest import upsert_jobs
from apps.jobs.services.normalise import normalised


def row(**over):
    base = dict(
        source='greenhouse', external_id='1', company_name='Acme',
        title='Engineer', description='A job.', apply_url='https://e.com/1',
        location_raw='Dublin, Ireland',
        posted_at=timezone.now() - timezone.timedelta(days=5),
    )
    return normalised(**{**base, **over})


@pytest.fixture
def company(db):
    return TrackedCompany.objects.create(
        name='Acme', platform=ATSPlatform.GREENHOUSE, slug='acme',
    )


@pytest.fixture
def jobs(company):
    upsert_jobs([
        row(external_id='1', title='Backend Engineer',
            description='We use Python, Django and PostgreSQL every day.'),
        row(external_id='2', title='Python Platform Engineer',
            description='Deep Python work on our platform.'),
        row(external_id='3', title='Sales Executive',
            description='Selling enterprise software to large accounts.'),
    ], company)


@pytest.mark.django_db
class TestSkillTerms:
    def test_an_alias_resolves_to_the_canonical_name_too(self, sample_cv, canonical_skills):
        """A CV saying "postgres" should match a job advertising "PostgreSQL"."""
        sample_cv.skills.all().delete()
        CVSkill.objects.create(cv=sample_cv, name='postgres', order=0)

        terms = [t.casefold() for t in cv_skill_terms(sample_cv)]
        assert 'postgres' in terms and 'postgresql' in terms

    def test_an_unknown_skill_is_still_used(self, sample_cv):
        sample_cv.skills.all().delete()
        CVSkill.objects.create(cv=sample_cv, name='Internal Tooling', order=0)
        assert 'Internal Tooling' in cv_skill_terms(sample_cv)


@pytest.mark.django_db
class TestRanking:
    def test_a_thin_cv_is_refused_rather_than_ranked_meaninglessly(self, empty_cv, jobs):
        """Better to say "add some skills" than to show an arbitrary order."""
        from apps.jobs.models import Job

        with pytest.raises(NotEnoughSkills):
            rank_by_cv(Job.objects.all(), empty_cv)

    def test_jobs_matching_the_cv_come_first(self, sample_cv, jobs):
        from apps.jobs.models import Job

        queryset, terms = rank_by_cv(Job.objects.all(), sample_cv)
        titles = [j.title for j in queryset]

        assert 'Sales Executive' not in titles
        assert set(titles) == {'Backend Engineer', 'Python Platform Engineer'}

    def test_a_title_match_ranks_above_a_body_mention(self, sample_cv, jobs):
        from apps.jobs.models import Job

        queryset, _ = rank_by_cv(Job.objects.all(), sample_cv)
        assert queryset.first().title == 'Python Platform Engineer'


class TestMatchedSkills:
    def test_it_reports_the_skills_actually_mentioned(self):
        """The point of this over a score: the user can check it."""
        matched = matched_skills_for(
            'Backend Engineer. We use Python and PostgreSQL.',
            ['Python', 'PostgreSQL', 'Kubernetes'],
        )
        assert matched == ['Python', 'PostgreSQL']

    def test_matching_is_case_insensitive(self):
        assert matched_skills_for('we use PYTHON', ['python']) == ['python']


@pytest.mark.django_db
class TestTheEndpoint:
    def test_match_cv_ranks_and_reports_what_it_matched_on(self, api, sample_cv, jobs):
        response = api.get(reverse('job-list'), {'match': 'cv'})

        assert response.status_code == 200
        assert response.data['count'] == 2
        assert response.data['matched_against']
        assert response.data['results'][0]['matched_skills']

    def test_without_the_flag_nothing_changes(self, api, sample_cv, jobs):
        response = api.get(reverse('job-list'))
        assert response.data['count'] == 3
        assert 'matched_against' not in response.data

    def test_a_thin_cv_gets_an_actionable_400(self, api, empty_cv, jobs):
        response = api.get(reverse('job-list'), {'match': 'cv'})
        assert response.status_code == 400
        assert 'skills' in response.data['detail'].lower()

    def test_no_cv_at_all_gets_an_actionable_400(self, api, user, jobs):
        response = api.get(reverse('job-list'), {'match': 'cv'})
        assert response.status_code == 400
        assert 'CV' in response.data['detail']

    def test_cv_ranking_combines_with_other_filters(self, api, sample_cv, jobs):
        response = api.get(reverse('job-list'), {'match': 'cv', 'source': 'lever'})
        assert response.data['count'] == 0
