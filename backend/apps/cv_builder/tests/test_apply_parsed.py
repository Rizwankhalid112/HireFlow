"""Applying a reviewed import.

The only path by which parsed data reaches the database, so this is where the
promises made everywhere else are actually kept: nothing overwrites without a
choice, one bad row does not cost the user the others, and a row missing a
required field waits for an answer rather than getting a guess.
"""

import pytest
from django.urls import reverse

from apps.cv_builder.models import CVUploadLog
from apps.cv_builder.services.apply_parsed import apply_parsed_cv


def payload(**overrides):
    base = {
        'personal': {
            'full_name': 'Grace Hopper', 'professional_title': 'Rear Admiral',
            'email': 'grace@navy.mil', 'phone': '+1 202 000 0000',
            'city': 'Arlington', 'country': 'USA', 'linkedin_url': '',
            'github_url': '', 'portfolio_url': '', 'summary': 'A summary.',
        },
        'work_experience': [],
        'education': [],
        'skills': [],
        'projects': [],
        'certifications': [],
        'languages': [],
        'unmapped_sections': [],
        'notes': [],
    }
    return {**base, **overrides}


def role(**overrides):
    base = {
        'company_name': 'US Navy', 'role_title': 'Programmer', 'employment_type': '',
        'location': '', 'location_type': '', 'start_year': 1944, 'start_month': None,
        'end_year': 1949, 'end_month': None, 'is_current': False,
        'bullets': ['Wrote the first compiler for a computer programming language.'],
        'needs_attention': [],
    }
    return {**base, **overrides}


def degree(**overrides):
    base = {
        'institution': 'Yale', 'degree_type': 'phd', 'field_of_study': 'Mathematics',
        'cgpa': None, 'cgpa_scale': None, 'thesis_title': '', 'achievements': '',
        'start_year': 1930, 'end_year': 1934, 'is_current': False,
        'needs_attention': [],
    }
    return {**base, **overrides}


@pytest.mark.django_db
class TestChoices:
    def test_keep_writes_nothing(self, sample_cv):
        before = sample_cv.work_experiences.count()
        apply_parsed_cv(sample_cv, payload(work_experience=[role()]), {'work_experience': 'keep'})
        assert sample_cv.work_experiences.count() == before

    def test_replace_clears_first(self, sample_cv):
        apply_parsed_cv(
            sample_cv, payload(work_experience=[role()]), {'work_experience': 'replace'},
        )
        assert sample_cv.work_experiences.count() == 1
        assert sample_cv.work_experiences.first().company_name == 'US Navy'

    def test_merge_appends(self, sample_cv):
        before = sample_cv.work_experiences.count()
        apply_parsed_cv(
            sample_cv, payload(work_experience=[role()]), {'work_experience': 'merge'},
        )
        assert sample_cv.work_experiences.count() == before + 1

    def test_an_absent_section_defaults_to_keep(self, sample_cv):
        """A choices object that omits a section must not be read as consent to
        overwrite it."""
        before = sample_cv.skills.count()
        apply_parsed_cv(sample_cv, payload(skills=[{'name': 'COBOL'}]), {})
        assert sample_cv.skills.count() == before


@pytest.mark.django_db
class TestPersonal:
    def test_replace_overwrites(self, sample_cv):
        apply_parsed_cv(sample_cv, payload(), {'personal': 'replace'})
        sample_cv.refresh_from_db()
        assert sample_cv.full_name == 'Grace Hopper'

    def test_merge_only_fills_blanks(self, sample_cv):
        """The useful reading: they typed their name already and do not want it
        replaced, but do want the phone number the CV had."""
        sample_cv.phone = ''
        sample_cv.save()

        apply_parsed_cv(sample_cv, payload(), {'personal': 'merge'})

        sample_cv.refresh_from_db()
        assert sample_cv.full_name == 'Ada Lovelace'
        assert sample_cv.phone == '+1 202 000 0000'

    def test_email_is_never_overwritten(self, sample_cv):
        """It is pre-filled from the account and is how the CV gets contacted.
        A stale address in an old CV file must not silently replace it."""
        original = sample_cv.email
        apply_parsed_cv(sample_cv, payload(), {'personal': 'replace'})
        sample_cv.refresh_from_db()
        assert sample_cv.email == original


@pytest.mark.django_db
class TestSkills:
    def test_merge_does_not_duplicate(self, sample_cv):
        """sample_cv already has Python."""
        before = sample_cv.skills.count()
        apply_parsed_cv(
            sample_cv,
            payload(skills=[{'name': 'Python'}, {'name': 'COBOL'}]),
            {'skills': 'merge'},
        )
        assert sample_cv.skills.count() == before + 1
        assert sample_cv.skills.filter(name__iexact='python').count() == 1

    def test_duplicates_are_case_insensitive(self, sample_cv):
        before = sample_cv.skills.count()
        apply_parsed_cv(sample_cv, payload(skills=[{'name': 'PYTHON'}]), {'skills': 'merge'})
        assert sample_cv.skills.count() == before

    def test_a_canonical_skill_arrives_verified(self, sample_cv, canonical_skills):
        """An imported skill should be indistinguishable from one picked out of
        the autocomplete."""
        apply_parsed_cv(
            sample_cv,
            payload(skills=[{
                'name': 'Django', 'category': 'Frameworks',
                'canonical_id': str(canonical_skills[5].id),
            }]),
            {'skills': 'replace'},
        )
        skill = sample_cv.skills.get(name='Django')
        assert skill.is_verified is True
        assert skill.canonical_id is not None


@pytest.mark.django_db
class TestNeedsAttention:
    def test_a_row_missing_a_required_field_does_not_import(self, sample_cv):
        result = apply_parsed_cv(
            sample_cv,
            payload(education=[degree(start_year=None, needs_attention=['start_year'])]),
            {'education': 'replace'},
        )
        assert sample_cv.education_entries.count() == 0
        assert result.skipped[0]['section'] == 'education'
        assert 'start_year' in result.skipped[0]['reason']

    def test_an_answered_row_imports(self, sample_cv):
        result = apply_parsed_cv(
            sample_cv,
            payload(education=[degree(start_year=None, needs_attention=['start_year'])]),
            {'education': 'replace'},
            answers={'education': {'0': {'start_year': 1930}}},
        )
        assert result.skipped == []
        assert sample_cv.education_entries.get().start_year == 1930

    def test_one_blocked_row_does_not_block_the_others(self, sample_cv):
        result = apply_parsed_cv(
            sample_cv,
            payload(education=[
                degree(institution='Yale', start_year=None, needs_attention=['start_year']),
                degree(institution='Vassar', start_year=1924),
            ]),
            {'education': 'replace'},
        )
        assert [e.institution for e in sample_cv.education_entries.all()] == ['Vassar']
        assert len(result.skipped) == 1


@pytest.mark.django_db
class TestPartialFailure:
    def test_a_bad_row_is_skipped_and_the_rest_import(self, sample_cv):
        """One malformed role must not cost the user the other two."""
        result = apply_parsed_cv(
            sample_cv,
            payload(work_experience=[
                role(company_name='Good Corp'),
                role(company_name='', role_title=''),
                role(company_name='Also Good Corp'),
            ]),
            {'work_experience': 'replace'},
        )
        names = set(sample_cv.work_experiences.values_list('company_name', flat=True))
        assert names == {'Good Corp', 'Also Good Corp'}
        assert len(result.skipped) == 1

    def test_a_short_bullet_does_not_cost_the_role(self, sample_cv):
        """WorkBulletSerializer rejects under 10 characters."""
        apply_parsed_cv(
            sample_cv,
            payload(work_experience=[role(bullets=['Too short', 'A properly long bullet line.'])]),
            {'work_experience': 'replace'},
        )
        experience = sample_cv.work_experiences.get()
        assert experience.bullets.count() == 1


@pytest.mark.django_db
class TestBullets:
    def test_bullets_attach_to_their_role_in_order(self, sample_cv):
        apply_parsed_cv(
            sample_cv,
            payload(work_experience=[role(bullets=[
                'The first thing that was accomplished here.',
                'The second thing that was accomplished here.',
            ])]),
            {'work_experience': 'replace'},
        )
        bullets = list(sample_cv.work_experiences.get().bullets.order_by('order'))
        assert [b.order for b in bullets] == [0, 1]
        assert bullets[0].text.startswith('The first')


@pytest.mark.django_db
class TestTheEndpoint:
    @pytest.fixture
    def parsed_log(self, sample_cv):
        return CVUploadLog.objects.create(
            cv=sample_cv, original_filename='cv.pdf', file_type='pdf', file_path='x',
            parse_status=CVUploadLog.ParseStatus.SUCCESS,
            ai_parsed_json=payload(work_experience=[role()]),
        )

    def test_applying_works(self, api, parsed_log):
        response = api.post(
            reverse('cv-upload-apply', args=[parsed_log.id]),
            {'choices': {'work_experience': 'replace'}}, format='json',
        )
        assert response.status_code == 200
        assert response.data['imported'] >= 1

    def test_applying_twice_is_refused(self, api, parsed_log):
        """Apply is destructive under `replace`, so a double-submitted form
        would wipe the rows the first submit just created."""
        url = reverse('cv-upload-apply', args=[parsed_log.id])
        api.post(url, {'choices': {'work_experience': 'replace'}}, format='json')
        second = api.post(url, {'choices': {'work_experience': 'replace'}}, format='json')

        assert second.status_code == 409
        assert 'already been applied' in second.data['detail']

    def test_an_unparsed_log_cannot_be_applied(self, api, sample_cv):
        log = CVUploadLog.objects.create(
            cv=sample_cv, original_filename='cv.pdf', file_type='pdf',
            file_path='x', parse_status=CVUploadLog.ParseStatus.PENDING,
        )
        response = api.post(reverse('cv-upload-apply', args=[log.id]), {}, format='json')
        assert response.status_code == 409

    def test_an_invalid_choice_is_rejected(self, api, parsed_log):
        response = api.post(
            reverse('cv-upload-apply', args=[parsed_log.id]),
            {'choices': {'work_experience': 'obliterate'}}, format='json',
        )
        assert response.status_code == 400

    def test_another_users_log_cannot_be_applied(self, api, sample_cv, other_user):
        from apps.cv_builder.models import CVProfile

        other_profile = CVProfile.objects.create(user=other_user, email=other_user.email)
        theirs = CVUploadLog.objects.create(
            cv=other_profile, original_filename='theirs.pdf', file_type='pdf',
            file_path='x', parse_status=CVUploadLog.ParseStatus.SUCCESS,
            ai_parsed_json=payload(),
        )
        response = api.post(reverse('cv-upload-apply', args=[theirs.id]), {}, format='json')
        assert response.status_code == 404


@pytest.mark.django_db
class TestStatusEndpoint:
    def test_requires_review_is_true_when_the_cv_has_content(self, api, sample_cv):
        log = CVUploadLog.objects.create(
            cv=sample_cv, original_filename='cv.pdf', file_type='pdf', file_path='x',
            parse_status=CVUploadLog.ParseStatus.SUCCESS, ai_parsed_json=payload(),
        )
        response = api.get(reverse('cv-upload-status', args=[log.id]))
        assert response.data['requires_review'] is True
        assert response.data['existing_data']['work_experience']['count'] == 1

    def test_requires_review_is_false_for_an_empty_cv(self, api, empty_cv):
        """A brand-new user reviewing a diff against nothing is a modal for no
        reason."""
        log = CVUploadLog.objects.create(
            cv=empty_cv, original_filename='cv.pdf', file_type='pdf', file_path='x',
            parse_status=CVUploadLog.ParseStatus.SUCCESS, ai_parsed_json=payload(),
        )
        response = api.get(reverse('cv-upload-status', args=[log.id]))
        assert response.data['requires_review'] is False

    def test_it_is_derived_not_stored(self, api, sample_cv):
        """The user can empty their CV in another tab between the parse
        finishing and looking at the result."""
        log = CVUploadLog.objects.create(
            cv=sample_cv, original_filename='cv.pdf', file_type='pdf', file_path='x',
            parse_status=CVUploadLog.ParseStatus.SUCCESS, ai_parsed_json=payload(),
        )
        assert api.get(reverse('cv-upload-status', args=[log.id])).data['requires_review'] is True

        sample_cv.work_experiences.all().delete()
        sample_cv.education_entries.all().delete()
        sample_cv.skills.all().delete()

        assert api.get(reverse('cv-upload-status', args=[log.id])).data['requires_review'] is False
