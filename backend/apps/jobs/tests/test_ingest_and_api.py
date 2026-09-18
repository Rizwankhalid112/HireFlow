"""Ingest behaviour and the API, including the things that matter at scale."""

from unittest.mock import patch

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.jobs.models import ATSPlatform, Job, TrackedCompany
from apps.jobs.services.ingest import purge_stale, upsert_jobs
from apps.jobs.services.normalise import normalised
from apps.jobs.services.runner import fetch_company, run_gather


def row(**over):
    base = dict(
        source='greenhouse', external_id='1', company_name='Acme',
        title='Backend Engineer', description='We build payment systems in Python.',
        apply_url='https://example.com/jobs/1', location_raw='Dublin, Ireland',
        posted_at=timezone.now() - timezone.timedelta(days=10),
    )
    return normalised(**{**base, **over})


@pytest.fixture
def company(db):
    return TrackedCompany.objects.create(
        name='Acme', platform=ATSPlatform.GREENHOUSE, slug='acme',
    )


@pytest.mark.django_db
class TestUpsert:
    def test_jobs_are_written(self, company):
        written, skipped = upsert_jobs([row(external_id='1'), row(external_id='2')], company)
        assert (written, skipped) == (2, 0)
        assert Job.objects.count() == 2

    def test_rerunning_updates_instead_of_duplicating(self, company):
        """The whole point of the unique constraint: a nightly run must not
        double the table."""
        upsert_jobs([row(external_id='1', title='Old title')], company)
        upsert_jobs([row(external_id='1', title='New title')], company)

        assert Job.objects.count() == 1
        assert Job.objects.get().title == 'New title'

    def test_first_seen_survives_a_refetch(self, company):
        """It records when we first saw the job and must never be overwritten."""
        upsert_jobs([row(external_id='1')], company)
        original = Job.objects.get().first_seen_at

        upsert_jobs([row(external_id='1', title='Changed')], company)

        assert Job.objects.get().first_seen_at == original

    def test_last_seen_moves_on_every_run(self, company):
        """This is what retention reads."""
        upsert_jobs([row(external_id='1')], company)
        Job.objects.update(last_seen_at=timezone.now() - timezone.timedelta(days=10))

        upsert_jobs([row(external_id='1')], company)

        assert (timezone.now() - Job.objects.get().last_seen_at).days == 0

    def test_the_same_id_twice_in_one_batch_does_not_break_it(self, company):
        """A feed occasionally repeats an id; the unique constraint would
        otherwise reject the entire batch."""
        written, skipped = upsert_jobs([row(external_id='1'), row(external_id='1')], company)
        assert written == 1 and skipped == 1

    def test_rows_missing_essentials_are_skipped_not_stored(self, company):
        written, skipped = upsert_jobs([
            row(external_id=''), row(title=''), row(apply_url=''),
        ], company)
        assert written == 0 and skipped == 3

    def test_the_same_external_id_on_two_platforms_is_two_jobs(self, company):
        """Uniqueness is (source, external_id), not external_id alone."""
        upsert_jobs([row(source='greenhouse', external_id='42')], company)
        upsert_jobs([row(source='lever', external_id='42')], company)
        assert Job.objects.count() == 2


@pytest.mark.django_db
class TestRetention:
    def test_jobs_unseen_for_too_long_are_deleted(self, company):
        upsert_jobs([row(external_id='1')], company)
        Job.objects.update(last_seen_at=timezone.now() - timezone.timedelta(days=60))

        assert purge_stale(45) == 1
        assert Job.objects.count() == 0

    def test_a_zero_window_does_not_wipe_the_table(self, company):
        """`--no-purge` passes 0. Read literally that means "delete everything
        older than now", which is the whole table. It must mean "do not purge"."""
        upsert_jobs([row(external_id='1')], company)

        assert purge_stale(0) == 0
        assert Job.objects.count() == 1

    def test_an_old_posting_still_in_the_feed_is_kept(self, company):
        """The critical one. Live listings exist that were published in 2009 —
        purging on posting age would delete jobs that are genuinely open."""
        upsert_jobs([row(
            external_id='1', posted_at=timezone.now() - timezone.timedelta(days=4000),
        )], company)

        assert purge_stale(45) == 0
        assert Job.objects.count() == 1


@pytest.mark.django_db
class TestRunner:
    def test_one_company_failing_does_not_stop_the_run(self, company):
        """A wrong slug or an outage at one employer is normal."""
        from apps.jobs.services.fetchers import FetchError

        other = TrackedCompany.objects.create(
            name='Good', platform=ATSPlatform.ASHBY, slug='good',
        )

        def fake(platform, slug):
            if slug == 'acme':
                raise FetchError('Not found — check the company slug.')
            return [row(source='ashby', external_id='9', company_name='Good')]

        # workers=1 keeps the run in this thread: a pool worker gets its own
        # connection and cannot see the rows this test has not committed.
        with patch('apps.jobs.services.runner.fetch_for', side_effect=fake):
            summary = run_gather(
                companies=TrackedCompany.objects.all(), purge_days=0, workers=1,
            )

        assert summary['succeeded'] == 1
        assert summary['failed'] == 1
        assert Job.objects.count() == 1

    def test_a_failure_is_recorded_on_the_company(self, company):
        """A board that silently stopped returning jobs must be visible."""
        from apps.jobs.services.fetchers import FetchError

        with patch('apps.jobs.services.runner.fetch_for', side_effect=FetchError('boom')):
            fetch_company(company)

        company.refresh_from_db()
        assert company.consecutive_failures == 1
        assert 'boom' in company.last_fetch_status

    def test_a_company_is_disabled_after_repeated_failures(self, company):
        """Retrying a permanently wrong slug every night is wasted requests."""
        from apps.jobs.services.fetchers import FetchError

        with patch('apps.jobs.services.runner.fetch_for', side_effect=FetchError('gone')):
            for _ in range(5):
                fetch_company(company)

        company.refresh_from_db()
        assert company.is_active is False

    def test_a_success_clears_the_failure_count(self, company):
        from apps.jobs.services.fetchers import FetchError

        with patch('apps.jobs.services.runner.fetch_for', side_effect=FetchError('x')):
            fetch_company(company)
        with patch('apps.jobs.services.runner.fetch_for', return_value=[row()]):
            fetch_company(company)

        company.refresh_from_db()
        assert company.consecutive_failures == 0


@pytest.mark.django_db
class TestApi:
    @pytest.fixture(autouse=True)
    def _jobs(self, company):
        upsert_jobs([
            row(external_id='1', title='Senior Python Engineer', location_raw='Dublin, Ireland'),
            row(external_id='2', title='Frontend Developer', location_raw='Karachi, Pakistan'),
            row(external_id='3', title='Data Scientist', company_name='Globex',
                location_raw='Remote, United States'),
        ], company)

    def test_listing_is_paginated(self, api):
        """An unbounded list is the query guaranteed to break as the table grows."""
        response = api.get(reverse('job-list'))
        assert response.status_code == 200
        assert set(response.data) >= {'count', 'results'}
        assert response.data['count'] == 3

    def test_the_list_omits_the_long_description(self, api):
        """Several thousand characters times 25 rows would dominate the payload."""
        response = api.get(reverse('job-list'))
        assert 'description' not in response.data['results'][0]

    def test_the_detail_includes_it(self, api):
        job = Job.objects.first()
        response = api.get(reverse('job-detail', args=[job.id]))
        assert response.data['description']

    def test_source_and_date_are_exposed(self, api):
        """Both matter to the reader and are shown on the card."""
        item = api.get(reverse('job-list')).data['results'][0]
        assert item['source'] and item['source_label']
        assert item['posted_at'] and item['age_days'] is not None

    def test_full_text_search_covers_the_description(self, api):
        """Descriptions are indexed too. Excluding them made the feature wrong:
        over 2,700 real engineering jobs, searching "python" matched exactly one,
        because listings name the language in the body, not the title."""
        response = api.get(reverse('job-list'), {'search': 'python'})
        # All three fixtures mention Python in the description.
        assert response.data['count'] == 3

    def test_a_title_match_outranks_a_description_match(self, api):
        """Weighting is A-D, so the job actually titled for the term comes
        first rather than being buried among incidental mentions."""
        response = api.get(reverse('job-list'), {'search': 'python'})
        assert response.data['results'][0]['title'] == 'Senior Python Engineer'

    def test_search_matches_the_company_name(self, api):
        response = api.get(reverse('job-list'), {'search': 'Globex'})
        assert [r['title'] for r in response.data['results']] == ['Data Scientist']

    def test_location_filter(self, api):
        response = api.get(reverse('job-list'), {'location': 'Pakistan'})
        assert [r['title'] for r in response.data['results']] == ['Frontend Developer']

    def test_source_filter(self, api):
        assert api.get(reverse('job-list'), {'source': 'lever'}).data['count'] == 0
        assert api.get(reverse('job-list'), {'source': 'greenhouse'}).data['count'] == 3

    def test_a_user_can_delete_a_job(self, api):
        job = Job.objects.first()
        assert api.delete(reverse('job-detail', args=[job.id])).status_code == 204
        assert not Job.objects.filter(pk=job.pk).exists()

    def test_authentication_is_required(self):
        from rest_framework.test import APIClient
        assert APIClient().get(reverse('job-list')).status_code in (401, 403)

    def test_long_running_is_flagged_not_shown_as_a_day_count(self, api):
        """One tested board publishes a live role as posted in 2009."""
        Job.objects.filter(external_id='1').update(
            posted_at=timezone.now() - timezone.timedelta(days=4000),
        )
        item = next(r for r in api.get(reverse('job-list')).data['results'] if r['id'] == str(
            Job.objects.get(external_id='1').id))
        assert item['is_long_running'] is True

    def test_stats(self, api):
        response = api.get(reverse('job-stats'))
        assert response.data['total_jobs'] == 3
        assert response.data['by_source'][0]['source'] == 'greenhouse'
