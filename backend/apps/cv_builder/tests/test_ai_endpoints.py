"""The HTTP surface: auth, ownership, credits, and graceful degradation.

The credit and 503 paths matter more than they look. These are the only
endpoints in the project that spend money per call, and both failure modes have
to leave the user's text untouched.
"""

import pytest
from rest_framework.test import APIClient

from apps.cv_builder.models import AISuggestionLog, CVProfile
from apps.cv_builder.services.ai import suggest
from apps.cv_builder.services.ai.client import SuggestionUnavailable, Usage
from apps.cv_builder.services.ai.schemas import BulletSuggestions, SummarySuggestions, TextVariant


def stub(parsed):
    def _complete(system_prompt, user_content, output_format):
        return parsed, Usage(input_tokens=900, output_tokens=200, cached_tokens=800)
    return _complete


def raises_unavailable(*_args, **_kwargs):
    raise SuggestionUnavailable('The writing assistant is unavailable right now.')


@pytest.fixture
def experience(sample_cv):
    return sample_cv.work_experiences.first()


@pytest.mark.django_db
class TestAvailability:
    def test_without_a_key_the_endpoint_degrades_to_503(self, api, sample_cv, settings):
        """No key configured is a server state, not a user error — so 503 and a
        message that tells them their text is safe."""
        settings.ANTHROPIC_API_KEY = ''

        response = api.post('/api/cv/suggest/summary/', {}, format='json')

        assert response.status_code == 503
        assert 'detail' in response.json()

    def test_an_upstream_failure_is_503_not_500(self, api, sample_cv, ai_enabled, monkeypatch):
        monkeypatch.setattr(suggest, 'complete', raises_unavailable)

        response = api.post('/api/cv/suggest/summary/', {}, format='json')

        assert response.status_code == 503

    def test_the_credits_endpoint_reports_whether_the_feature_is_on(
        self, api, sample_cv, settings,
    ):
        settings.ANTHROPIC_API_KEY = ''
        assert api.get('/api/cv/suggest/credits/').json()['enabled'] is False

        settings.ANTHROPIC_API_KEY = 'test-key-not-a-real-credential'
        assert api.get('/api/cv/suggest/credits/').json()['enabled'] is True


@pytest.mark.django_db
class TestCredits:
    def test_a_successful_call_reports_the_remaining_allowance(
        self, api, sample_cv, ai_enabled, monkeypatch,
    ):
        monkeypatch.setattr(suggest, 'complete', stub(SummarySuggestions(variants=[], gaps=[])))

        body = api.post('/api/cv/suggest/summary/', {}, format='json').json()

        assert body['credits']['used'] == 1
        assert body['credits']['remaining'] == ai_enabled.AI_MONTHLY_CREDITS - 1

    def test_an_exhausted_allowance_returns_429_without_calling_the_model(
        self, api, sample_cv, ai_enabled, monkeypatch,
    ):
        ai_enabled.AI_MONTHLY_CREDITS = 1
        called = []

        def _complete(*args, **kwargs):
            called.append(1)
            return SummarySuggestions(variants=[], gaps=[]), Usage()

        monkeypatch.setattr(suggest, 'complete', _complete)

        assert api.post('/api/cv/suggest/summary/', {}, format='json').status_code == 200
        second = api.post('/api/cv/suggest/summary/', {}, format='json')

        assert second.status_code == 429
        assert len(called) == 1, 'the model was called after the allowance ran out'

    def test_credits_are_counted_from_the_log_not_a_counter(
        self, api, sample_cv, ai_enabled, monkeypatch,
    ):
        monkeypatch.setattr(suggest, 'complete', stub(SummarySuggestions(variants=[], gaps=[])))
        api.post('/api/cv/suggest/summary/', {}, format='json')

        used = api.get('/api/cv/suggest/credits/').json()['used']
        assert used == AISuggestionLog.objects.filter(cv=sample_cv).count()


@pytest.mark.django_db
class TestOwnership:
    def test_suggestions_require_authentication(self, client, sample_cv):
        assert client.post('/api/cv/suggest/summary/').status_code == 401

    def test_one_user_cannot_request_bullets_for_another_users_role(
        self, sample_cv, other_user, ai_enabled, monkeypatch,
    ):
        monkeypatch.setattr(suggest, 'complete', stub(BulletSuggestions(variants=[], gaps=[])))
        CVProfile.objects.create(user=other_user, email=other_user.email)

        intruder = APIClient()
        intruder.force_authenticate(user=other_user)
        experience_id = str(sample_cv.work_experiences.first().id)

        response = intruder.post(
            '/api/cv/suggest/bullets/', {'experience_id': experience_id}, format='json',
        )

        assert response.status_code == 404

    def test_one_user_cannot_accept_another_users_suggestion(
        self, sample_cv, other_user, ai_enabled, api, monkeypatch,
    ):
        monkeypatch.setattr(suggest, 'complete', stub(SummarySuggestions(variants=[], gaps=[])))
        log_id = api.post('/api/cv/suggest/summary/', {}, format='json').json()['log_id']

        CVProfile.objects.create(user=other_user, email=other_user.email)
        intruder = APIClient()
        intruder.force_authenticate(user=other_user)

        response = intruder.post(f'/api/cv/suggest/{log_id}/accept/', {'index': 0}, format='json')

        assert response.status_code == 404


@pytest.mark.django_db
class TestAccept:
    def test_accepting_records_which_variant_was_taken(
        self, api, sample_cv, ai_enabled, monkeypatch,
    ):
        """Accept rate per section is the only honest measure of whether this
        feature works, and it cannot be reconstructed after the fact."""
        parsed = SummarySuggestions(
            variants=[TextVariant(text='Backend engineer with six years in payments.', grounded_in=[])],
            gaps=[],
        )
        monkeypatch.setattr(suggest, 'complete', stub(parsed))

        log_id = api.post('/api/cv/suggest/summary/', {}, format='json').json()['log_id']
        response = api.post(f'/api/cv/suggest/{log_id}/accept/', {'index': 0}, format='json')

        assert response.status_code == 204
        assert AISuggestionLog.objects.get(pk=log_id).accepted_index == 0

    def test_a_rejection_is_recorded_as_a_null_index(
        self, api, sample_cv, ai_enabled, monkeypatch,
    ):
        monkeypatch.setattr(suggest, 'complete', stub(SummarySuggestions(variants=[], gaps=[])))
        log_id = api.post('/api/cv/suggest/summary/', {}, format='json').json()['log_id']

        api.post(f'/api/cv/suggest/{log_id}/accept/', {'index': None}, format='json')

        assert AISuggestionLog.objects.get(pk=log_id).accepted_index is None


@pytest.mark.django_db
def test_the_target_role_falls_back_to_the_account_profile(
    api, user, sample_cv, ai_enabled, monkeypatch,
):
    """`UserProfile.target_role` already existed and nothing read it. It means
    exactly this, so it is reused rather than duplicated."""
    user.profile.target_role = 'Staff Backend Engineer'
    user.profile.save()

    seen = {}

    def _complete(system_prompt, user_content, output_format):
        seen['user'] = user_content
        return SummarySuggestions(variants=[], gaps=[]), Usage()

    monkeypatch.setattr(suggest, 'complete', _complete)
    api.post('/api/cv/suggest/summary/', {}, format='json')

    assert 'Staff Backend Engineer' in seen['user']
