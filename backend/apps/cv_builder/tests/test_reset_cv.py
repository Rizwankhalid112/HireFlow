"""Clearing a CV, in whole or in part.

Exists because the alternative was deleting nine roles and twelve skills one row
at a time. The tests that matter here are the ones about what reset must *not*
touch — a reset that also wipes the user's email or their template choice is
worse than no reset at all.
"""

import pytest
from django.urls import reverse

from apps.cv_builder.models import CVProfile
from apps.cv_builder.services.reset_cv import delete_cv, reset_cv


@pytest.mark.django_db
class TestResetEverything:
    def test_all_sections_are_emptied(self, sample_cv):
        reset_cv(sample_cv)

        assert sample_cv.work_experiences.count() == 0
        assert sample_cv.education_entries.count() == 0
        assert sample_cv.skills.count() == 0
        assert sample_cv.projects.count() == 0

    def test_the_profile_row_survives(self, sample_cv):
        reset_cv(sample_cv)
        assert CVProfile.objects.filter(pk=sample_cv.pk).exists()

    def test_personal_fields_are_cleared(self, sample_cv):
        reset_cv(sample_cv)
        sample_cv.refresh_from_db()
        assert sample_cv.full_name == ''
        assert sample_cv.summary == ''

    def test_the_email_is_kept(self, sample_cv, user):
        """Pre-filled from the account and how the CV is contacted. Blanking it
        on a reset would silently break the rendered CV's contact line."""
        reset_cv(sample_cv)
        sample_cv.refresh_from_db()
        assert sample_cv.email == user.email

    def test_the_template_choice_is_kept(self, sample_cv):
        """A preference, not content. Resetting content should not send the user
        back to the default template they had already rejected."""
        sample_cv.template_id = 'classic'
        sample_cv.save()

        reset_cv(sample_cv)

        sample_cv.refresh_from_db()
        assert sample_cv.template_id == 'classic'

    def test_completion_drops_to_zero(self, sample_cv):
        assert sample_cv.completion_score > 0
        reset_cv(sample_cv)
        sample_cv.refresh_from_db()
        assert sample_cv.completion_score == 0

    def test_the_reminder_flag_is_cleared(self, sample_cv):
        """A cleared draft should get its 30 days and its reminder again."""
        sample_cv.reminder_sent = True
        sample_cv.save()

        reset_cv(sample_cv)

        sample_cv.refresh_from_db()
        assert sample_cv.reminder_sent is False

    def test_counts_are_reported(self, sample_cv):
        cleared = reset_cv(sample_cv)
        assert cleared['work_experience'] == 1
        assert cleared['skills'] == 5

    def test_resetting_an_already_empty_cv_is_harmless(self, empty_cv):
        cleared = reset_cv(empty_cv)
        assert sum(cleared.values()) == 0


@pytest.mark.django_db
class TestResetOneSection:
    def test_only_the_named_section_is_cleared(self, sample_cv):
        """The common case: an import brought in the wrong roles and nothing
        else needs touching."""
        reset_cv(sample_cv, ['work_experience'])

        assert sample_cv.work_experiences.count() == 0
        assert sample_cv.skills.count() == 5
        assert sample_cv.education_entries.count() == 1

    def test_personal_details_survive_a_section_reset(self, sample_cv):
        reset_cv(sample_cv, ['skills'])
        sample_cv.refresh_from_db()
        assert sample_cv.full_name == 'Ada Lovelace'

    def test_bullets_go_with_their_role(self, sample_cv):
        from apps.cv_builder.models import WorkBullet

        reset_cv(sample_cv, ['work_experience'])
        assert WorkBullet.objects.filter(experience__cv=sample_cv).count() == 0


@pytest.mark.django_db
class TestDelete:
    def test_the_profile_and_its_rows_are_gone(self, sample_cv):
        from apps.cv_builder.models import WorkBullet, WorkExperience

        pk = sample_cv.pk
        delete_cv(sample_cv)

        assert not CVProfile.objects.filter(pk=pk).exists()
        assert WorkExperience.objects.filter(cv_id=pk).count() == 0
        assert WorkBullet.objects.filter(experience__cv_id=pk).count() == 0

    def test_upload_logs_go_too(self, sample_cv):
        from apps.cv_builder.models import CVUploadLog

        CVUploadLog.objects.create(
            cv=sample_cv, original_filename='cv.pdf', file_type='pdf', file_path='x',
        )
        pk = sample_cv.pk
        delete_cv(sample_cv)
        assert CVUploadLog.objects.filter(cv_id=pk).count() == 0


@pytest.mark.django_db
class TestTheEndpoints:
    def test_reset_everything(self, api, sample_cv):
        response = api.post(reverse('cv-profile-reset'), {}, format='json')

        assert response.status_code == 200
        assert response.data['total_cleared'] > 0
        assert sample_cv.work_experiences.count() == 0

    def test_reset_named_sections(self, api, sample_cv):
        response = api.post(
            reverse('cv-profile-reset'), {'sections': ['skills']}, format='json',
        )

        assert response.status_code == 200
        assert response.data['cleared'] == {'skills': 5}
        assert sample_cv.work_experiences.count() == 1

    def test_an_unknown_section_is_rejected(self, api, sample_cv):
        response = api.post(
            reverse('cv-profile-reset'), {'sections': ['salary_history']}, format='json',
        )
        assert response.status_code == 400
        assert 'salary_history' in response.data['detail']

    def test_an_empty_section_list_is_rejected(self, api, sample_cv):
        """Ambiguous between "clear nothing" and "clear everything", and one of
        those is destructive — so it is refused rather than guessed."""
        response = api.post(reverse('cv-profile-reset'), {'sections': []}, format='json')
        assert response.status_code == 400

    def test_sections_must_be_a_list(self, api, sample_cv):
        response = api.post(
            reverse('cv-profile-reset'), {'sections': 'skills'}, format='json',
        )
        assert response.status_code == 400

    def test_delete_the_cv(self, api, sample_cv):
        response = api.delete(reverse('cv-profile'))

        assert response.status_code == 204
        assert not CVProfile.objects.filter(pk=sample_cv.pk).exists()

    def test_the_user_can_start_again_after_deleting(self, api, sample_cv):
        api.delete(reverse('cv-profile'))
        response = api.post(reverse('cv-profile'))
        assert response.status_code == 201

    def test_reset_needs_authentication(self, sample_cv):
        from rest_framework.test import APIClient

        assert APIClient().post(reverse('cv-profile-reset')).status_code in (401, 403)

    def test_one_user_cannot_reset_another(self, api, other_user, sample_cv):
        """Both endpoints resolve the profile from the caller, so there is no
        id to tamper with — this pins that."""
        from rest_framework.test import APIClient

        other_profile = CVProfile.objects.create(user=other_user, email=other_user.email)
        client = APIClient()
        client.force_authenticate(user=other_user)

        client.post(reverse('cv-profile-reset'), {}, format='json')

        assert sample_cv.work_experiences.count() == 1
        assert CVProfile.objects.filter(pk=other_profile.pk).exists()
