"""Module 1 — job match: keywords and a cover letter.

`complete` is patched throughout; the suite never spends money. What is asserted
is the contract around the call, not the model's judgement.

The load-bearing tests here are the ones about **not writing to the CV** and
**not truncating the CV** — the first is the same promise the import makes, and
the second is subtle: a shortened CV makes real skills look missing, and the
feature then asks the user whether they have something their own CV lists.
"""

from unittest.mock import patch

import pytest
from django.urls import reverse

from apps.cv_builder.models import CVUploadLog, JobMatch
from apps.cv_builder.services.ai.client import SuggestionUnavailable, Usage
from apps.cv_builder.services.ai.schemas import (
    JobMatchResult,
    KeywordGap,
    KeywordMatch,
    KeywordRewrite,
)

JD = (
    'Backend Engineer at Globex. We are looking for someone with strong Python, '
    'Django and PostgreSQL experience to own our payments platform. You will '
    'design APIs, mentor engineers, and work with Kubernetes in production. '
    'Required: Python, Django, PostgreSQL. Preferred: Kubernetes, Terraform.'
)


def result(**overrides):
    base = {
        'job_title': 'Backend Engineer',
        'company': 'Globex',
        'match_score': 72,
        'summary': 'Strong on the core stack, no infrastructure evidence.',
        'matched': [KeywordMatch(keyword='Python', evidence='six years building payment systems in Python')],
        'reworded': [KeywordRewrite(keyword='PostgreSQL', current_wording='Postgres', where='Skills')],
        'missing': [KeywordGap(keyword='Kubernetes', importance='preferred', question='Have you used Kubernetes?')],
        'cover_letter': 'Dear hiring team, ...',
    }
    return JobMatchResult(**{**base, **overrides})


def fake_complete(value):
    return lambda *args, **kwargs: (value, Usage(2000, 1200, 0))


@pytest.fixture
def enabled(ai_enabled, settings):
    settings.AI_JOB_MATCH_MONTHLY_LIMIT = 20
    settings.REST_FRAMEWORK = {
        **settings.REST_FRAMEWORK,
        'DEFAULT_THROTTLE_RATES': {
            'ai_suggest': '1000/min', 'cv_upload': '1000/min', 'job_match': '1000/min',
        },
    }
    return settings


@pytest.mark.django_db
class TestTheService:
    def test_both_documents_go_in_messages_not_the_system_prompt(self, sample_cv, enabled):
        """Prompt caching is a prefix match. A CV in the cached prefix means
        every request pays full input price, silently."""
        from apps.cv_builder.services.ai import job_match

        with patch(
            'apps.cv_builder.services.ai.job_match.complete',
            side_effect=fake_complete(result()),
        ) as mock:
            job_match.match_job('A CV with plenty of text in it. ' * 10, JD)

        system_prompt, user_content = mock.call_args[0][0], mock.call_args[0][1]
        assert 'Globex' not in system_prompt
        assert 'Globex' in user_content
        assert '<cv>' in user_content and '<job_description>' in user_content

    def test_a_short_job_description_is_refused_before_the_call(self, sample_cv, enabled):
        from apps.cv_builder.services.ai import job_match

        with patch('apps.cv_builder.services.ai.job_match.complete') as mock:
            with pytest.raises(job_match.JobDescriptionTooShort):
                job_match.match_job('A CV with plenty of text. ' * 10, 'Backend dev needed')
        mock.assert_not_called()

    def test_an_empty_cv_is_refused_before_the_call(self, sample_cv, enabled):
        from apps.cv_builder.services.ai import job_match

        with patch('apps.cv_builder.services.ai.job_match.complete') as mock:
            with pytest.raises(job_match.JobDescriptionTooShort):
                job_match.match_job('', JD)
        mock.assert_not_called()

    def test_the_score_is_clamped(self, sample_cv, enabled):
        """The schema cannot bound an int, and the UI renders it as a percentage."""
        from apps.cv_builder.services.ai import job_match

        with patch(
            'apps.cv_builder.services.ai.job_match.complete',
            side_effect=fake_complete(result(match_score=180)),
        ):
            value, _ = job_match.match_job('A CV with plenty of text. ' * 10, JD)
        assert value.match_score == 100

    def test_it_asks_for_a_bigger_ceiling_than_a_suggestion(self, sample_cv, enabled):
        from apps.cv_builder.services.ai import job_match

        with patch(
            'apps.cv_builder.services.ai.job_match.complete',
            side_effect=fake_complete(result()),
        ) as mock:
            job_match.match_job('A CV with plenty of text. ' * 10, JD)
        assert mock.call_args.kwargs['max_tokens'] >= 4000


@pytest.mark.django_db
class TestTheCvTextIsComplete:
    def test_every_role_and_every_bullet_is_included(self, sample_cv, enabled):
        """Truncation would invent gaps: a skill mentioned only in a later bullet
        would read as missing, and we would ask the user about a skill their own
        CV lists."""
        from apps.cv_builder.services.ai.context import build_full_cv_text

        text = build_full_cv_text(sample_cv)

        assert 'Analytical Engines Ltd' in text
        assert 'Cut checkout latency' in text
        assert 'Raised service test coverage' in text  # the second bullet
        assert 'PostgreSQL' in text                    # a skill
        assert 'Ledger' in text                        # a project
        assert 'University of London' in text          # education


@pytest.mark.django_db
class TestTheEndpoint:
    def test_a_match_is_saved_and_returned(self, api, sample_cv, enabled):
        with patch(
            'apps.cv_builder.services.ai.job_match.complete',
            side_effect=fake_complete(result()),
        ):
            response = api.post(reverse('cv-job-match'), {'jd_text': JD}, format='json')

        assert response.status_code == 201
        assert response.data['match_score'] == 72
        assert response.data['company'] == 'Globex'
        assert response.data['cover_letter']
        assert JobMatch.objects.filter(cv=sample_cv).count() == 1

    def test_the_three_keyword_buckets_come_back_separately(self, api, sample_cv, enabled):
        """The whole ethical design: have it / have it by another name / do not
        have it. Collapsing them is what turns this into a lying machine."""
        with patch(
            'apps.cv_builder.services.ai.job_match.complete',
            side_effect=fake_complete(result()),
        ):
            response = api.post(reverse('cv-job-match'), {'jd_text': JD}, format='json')

        assert response.data['matched'][0]['keyword'] == 'Python'
        assert response.data['reworded'][0]['current_wording'] == 'Postgres'
        assert response.data['missing'][0]['question']

    def test_nothing_is_written_to_the_cv(self, api, sample_cv, enabled):
        before = {
            'skills': sample_cv.skills.count(),
            'experiences': sample_cv.work_experiences.count(),
            'summary': sample_cv.summary,
        }

        with patch(
            'apps.cv_builder.services.ai.job_match.complete',
            side_effect=fake_complete(result()),
        ):
            api.post(reverse('cv-job-match'), {'jd_text': JD}, format='json')

        sample_cv.refresh_from_db()
        assert sample_cv.skills.count() == before['skills']
        assert sample_cv.work_experiences.count() == before['experiences']
        assert sample_cv.summary == before['summary']

    def test_a_short_posting_is_a_400_and_saves_nothing(self, api, sample_cv, enabled):
        response = api.post(reverse('cv-job-match'), {'jd_text': 'dev needed'}, format='json')

        assert response.status_code == 400
        assert JobMatch.objects.count() == 0

    def test_an_upstream_outage_is_503_and_saves_nothing(self, api, sample_cv, enabled):
        with patch(
            'apps.cv_builder.services.ai.job_match.complete',
            side_effect=SuggestionUnavailable('The job matcher is unavailable right now.'),
        ):
            response = api.post(reverse('cv-job-match'), {'jd_text': JD}, format='json')

        assert response.status_code == 503
        assert JobMatch.objects.count() == 0

    def test_the_monthly_cap_is_enforced(self, api, sample_cv, enabled, settings):
        settings.AI_JOB_MATCH_MONTHLY_LIMIT = 1
        with patch(
            'apps.cv_builder.services.ai.job_match.complete',
            side_effect=fake_complete(result()),
        ):
            first = api.post(reverse('cv-job-match'), {'jd_text': JD}, format='json')
            second = api.post(reverse('cv-job-match'), {'jd_text': JD}, format='json')

        assert first.status_code == 201
        assert second.status_code == 429
        assert JobMatch.objects.count() == 1

    def test_deleting_does_not_refund_the_allowance(self, api, sample_cv, enabled, settings):
        """The allowance is counted from rows, so a hard delete would make
        "delete it and run again" an unlimited-usage bypass."""
        settings.AI_JOB_MATCH_MONTHLY_LIMIT = 1
        with patch(
            'apps.cv_builder.services.ai.job_match.complete',
            side_effect=fake_complete(result()),
        ):
            created = api.post(reverse('cv-job-match'), {'jd_text': JD}, format='json')
            api.delete(reverse('cv-job-match-detail', args=[created.data['id']]))
            again = api.post(reverse('cv-job-match'), {'jd_text': JD}, format='json')

        assert again.status_code == 429

    def test_a_deleted_match_disappears_from_the_list(self, api, sample_cv, enabled):
        with patch(
            'apps.cv_builder.services.ai.job_match.complete',
            side_effect=fake_complete(result()),
        ):
            created = api.post(reverse('cv-job-match'), {'jd_text': JD}, format='json')

        api.delete(reverse('cv-job-match-detail', args=[created.data['id']]))

        assert api.get(reverse('cv-job-match')).data == []
        assert api.get(reverse('cv-job-match-detail', args=[created.data['id']])).status_code == 404


@pytest.mark.django_db
class TestChoosingWhichCv:
    def test_the_built_cv_is_the_default(self, api, sample_cv, enabled):
        with patch(
            'apps.cv_builder.services.ai.job_match.complete',
            side_effect=fake_complete(result()),
        ) as mock:
            api.post(reverse('cv-job-match'), {'jd_text': JD}, format='json')

        assert 'Ada Lovelace' in mock.call_args[0][1]

    def test_an_uploaded_cv_can_be_used_instead(self, api, sample_cv, enabled):
        upload = CVUploadLog.objects.create(
            cv=sample_cv, original_filename='old-cv.pdf', file_type='pdf', file_path='x',
            raw_extracted_text='Grace Hopper, Rear Admiral. Wrote the first compiler.' * 5,
            parse_status=CVUploadLog.ParseStatus.SUCCESS,
        )

        with patch(
            'apps.cv_builder.services.ai.job_match.complete',
            side_effect=fake_complete(result()),
        ) as mock:
            response = api.post(
                reverse('cv-job-match'),
                {'jd_text': JD, 'source_type': 'upload', 'upload_id': str(upload.id)},
                format='json',
            )

        assert response.status_code == 201
        assert 'Grace Hopper' in mock.call_args[0][1]
        assert 'Ada Lovelace' not in mock.call_args[0][1]
        assert response.data['source_label'] == 'old-cv.pdf'

    def test_another_users_upload_cannot_be_used(self, api, sample_cv, other_user, enabled):
        """The id is re-fetched scoped to the caller, never trusted."""
        from apps.cv_builder.models import CVProfile

        other_profile = CVProfile.objects.create(user=other_user, email=other_user.email)
        theirs = CVUploadLog.objects.create(
            cv=other_profile, original_filename='theirs.pdf', file_type='pdf',
            file_path='x', raw_extracted_text='Secret CV content.' * 20,
        )

        response = api.post(
            reverse('cv-job-match'),
            {'jd_text': JD, 'source_type': 'upload', 'upload_id': str(theirs.id)},
            format='json',
        )
        assert response.status_code == 400

    def test_upload_without_an_id_is_rejected(self, api, sample_cv, enabled):
        response = api.post(
            reverse('cv-job-match'), {'jd_text': JD, 'source_type': 'upload'}, format='json',
        )
        assert response.status_code == 400

    def test_the_sources_list_shows_both(self, api, sample_cv, enabled):
        CVUploadLog.objects.create(
            cv=sample_cv, original_filename='old-cv.pdf', file_type='pdf', file_path='x',
            raw_extracted_text='some text', parse_status=CVUploadLog.ParseStatus.SUCCESS,
        )
        response = api.get(reverse('cv-job-match-sources'))

        assert response.status_code == 200
        types = [source['type'] for source in response.data['sources']]
        assert types == ['profile', 'upload']

    def test_an_upload_with_no_text_is_not_offered(self, api, sample_cv, enabled):
        """A scanned CV has a row but nothing to match against."""
        CVUploadLog.objects.create(
            cv=sample_cv, original_filename='scan.pdf', file_type='pdf', file_path='x',
            raw_extracted_text='', parse_status=CVUploadLog.ParseStatus.SCANNED,
        )
        response = api.get(reverse('cv-job-match-sources'))
        assert len(response.data['sources']) == 1


@pytest.mark.django_db
class TestHistory:
    def test_past_matches_are_listed_without_the_long_text(self, api, sample_cv, enabled):
        with patch(
            'apps.cv_builder.services.ai.job_match.complete',
            side_effect=fake_complete(result()),
        ):
            api.post(reverse('cv-job-match'), {'jd_text': JD}, format='json')

        response = api.get(reverse('cv-job-match'))
        assert response.status_code == 200
        assert 'cover_letter' not in response.data[0]

    def test_one_match_can_be_read_back_in_full(self, api, sample_cv, enabled):
        """The letter written on Monday is wanted on Thursday, and reading it
        back must not cost anything."""
        with patch(
            'apps.cv_builder.services.ai.job_match.complete',
            side_effect=fake_complete(result()),
        ):
            created = api.post(reverse('cv-job-match'), {'jd_text': JD}, format='json')

        response = api.get(reverse('cv-job-match-detail', args=[created.data['id']]))
        assert response.data['cover_letter'] == 'Dear hiring team, ...'

    def test_another_users_match_is_404(self, api, sample_cv, other_user, enabled):
        from apps.cv_builder.models import CVProfile

        other_profile = CVProfile.objects.create(user=other_user, email=other_user.email)
        theirs = JobMatch.objects.create(cv=other_profile, jd_text=JD, match_score=50)

        assert api.get(reverse('cv-job-match-detail', args=[theirs.id])).status_code == 404


def test_the_prompt_is_a_constant_and_forbids_invention():
    """Same two guarantees as every other prompt in the module."""
    import re

    from apps.cv_builder.services.ai import prompts

    assert not re.search(r'\{[a-z_]+\}', prompts.JOB_MATCH)
    text = ' '.join(prompts.JOB_MATCH.lower().split())
    assert 'you may never credit the candidate with a skill' in text
    assert 'that is not a prediction' in text or 'not a prediction' in text
