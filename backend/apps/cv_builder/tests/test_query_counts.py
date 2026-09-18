"""Regressions for the query-count work.

These assert on *how many* queries a path costs, not just its result. That is
unusual and deliberate: an N+1 does not fail a test, it just makes the product
slower every time someone adds a row, and it comes back the moment somebody
writes the obvious loop. Each number below is a ceiling that was measured, not
an aspiration.
"""

import pytest

from apps.cv_builder.models import SkillCanonical, WorkBullet, WorkExperience
from apps.cv_builder.services.ai.guardrails import lookup_canonical, lookup_canonical_bulk
from apps.cv_builder.services.completion import calculate_section_completion

pytestmark = pytest.mark.django_db


class TestBulkCanonicalLookup:
    """`lookup_canonical_bulk` must agree with `lookup_canonical`, exactly."""

    def test_it_matches_the_single_name_version(self, canonical_skills):
        names = ['Python', 'python', 'PostgreSQL', 'nonsense-not-a-skill', '']

        bulk = lookup_canonical_bulk(names)

        for name in names:
            expected = lookup_canonical(name)
            actual = bulk.get(name.strip().lower())
            assert getattr(actual, 'pk', None) == getattr(expected, 'pk', None), name

    def test_an_exact_canonical_name_still_beats_an_alias(self, canonical_skills):
        """The Java / JavaScript pair.

        'Java' is one skill's canonical name and a substring of another's alias.
        Losing that race silently relabels the user's skill, which is why the
        single-name version queries exact-first — the batch version must too.
        """
        java = SkillCanonical.objects.filter(canonical_name__iexact='Java').first()
        if java is None:
            pytest.skip('fixture has no Java row')

        resolved = lookup_canonical_bulk(['Java'])['java']

        assert resolved.pk == java.pk
        assert resolved.canonical_name == 'Java'

    def test_it_is_two_queries_regardless_of_how_many_names(
        self, canonical_skills, django_assert_max_num_queries,
    ):
        many = [row.canonical_name for row in SkillCanonical.objects.all()[:30]]

        with django_assert_max_num_queries(2):
            lookup_canonical_bulk(many)

    def test_unknown_names_are_absent_rather_than_None_valued(self, canonical_skills):
        assert lookup_canonical_bulk(['definitely-not-a-skill']) == {}


class TestCompletionQueryCount:
    """Completion runs on every write to a CV, not just on the dashboard.

    `CVProfile.save()` recomputes it and a `post_save` on all seven child models
    calls that — so a query per work experience here is a query per experience
    on every bullet anyone types.
    """

    def test_it_does_not_scale_with_the_number_of_experiences(
        self, sample_cv, django_assert_max_num_queries,
    ):
        for index in range(6):
            experience = WorkExperience.objects.create(
                cv=sample_cv,
                company_name=f'Company {index}',
                role_title='Engineer',
                start_year=2020,
            )
            WorkBullet.objects.create(experience=experience, text='A sufficiently long bullet.')

        # Four section queries: experience, education, skills, projects.
        # Contact and summary are plain field reads on a loaded row.
        with django_assert_max_num_queries(4):
            calculate_section_completion(sample_cv)

    def test_the_experience_rule_still_needs_two_bullets(self, sample_cv):
        sample_cv.work_experiences.all().delete()

        thin = WorkExperience.objects.create(
            cv=sample_cv, company_name='Thin Ltd', role_title='Engineer', start_year=2021,
        )
        WorkBullet.objects.create(experience=thin, text='Only one bullet here.')

        assert calculate_section_completion(sample_cv)['experience'] is False

        WorkBullet.objects.create(experience=thin, text='And now a second bullet.')

        assert calculate_section_completion(sample_cv)['experience'] is True
