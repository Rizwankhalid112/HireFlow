"""The mechanical half of the anti-fabrication design.

The prompt asks the model not to invent figures. These tests cover what happens
when it does anyway — which is the case that actually matters, because a prompt
is a request and this is enforcement.
"""

import pytest

from apps.cv_builder.services.ai import guardrails as guard
from apps.cv_builder.services.ai.schemas import SkillCandidate, TextVariant


class TestInventedNumbers:
    def test_a_number_from_nowhere_is_caught(self):
        sources = ['added redis caching to the api']
        assert guard.invented_numbers('Cut latency by 40% using Redis.', sources) == ['40']

    def test_a_number_the_user_supplied_is_allowed(self):
        sources = ['coverage went from 54 to 93']
        assert guard.invented_numbers('Raised coverage from 54% to 93%.', sources) == []

    def test_commas_and_units_are_normalised(self):
        sources = ['handled 1,200 requests per second']
        assert guard.invented_numbers('Handled 1200 requests per second.', sources) == []

    def test_currency_and_multipliers_are_compared_on_the_numeral(self):
        assert guard.invented_numbers('Saved $20k annually.', ['saved 20k a year']) == []
        assert guard.invented_numbers('Made it 3x faster.', ['made it much faster']) == []

    def test_small_ordinals_are_not_treated_as_claims(self):
        """'first', '2 services' in ordinary prose would otherwise trip on
        every bullet. Anything above 3 is a real quantity."""
        assert guard.invented_numbers('Led 2 migrations.', ['led migrations']) == []
        assert guard.invented_numbers('Led 12 migrations.', ['led migrations']) == ['12']

    def test_a_year_in_the_date_range_counts_as_sourced(self):
        assert guard.invented_numbers('Shipped in 2021.', ['March 2021 — Present']) == []


class TestGroundVariants:
    def _variant(self, text):
        return TextVariant(text=text, grounded_in=[])

    def test_a_fabricated_variant_is_dropped_and_the_rest_survive(self):
        variants = [
            self._variant('Cut API latency by introducing a Redis caching layer.'),
            self._variant('Cut API latency by 40% via Redis.'),
        ]
        kept, rejected = guard.ground_variants(
            variants, ['added redis caching'], max_chars=220, min_chars=10,
        )

        assert len(kept) == 1
        assert '40%' not in kept[0].text
        assert len(rejected) == 1

    def test_overlong_variants_are_dropped(self):
        kept, rejected = guard.ground_variants(
            [self._variant('x' * 300)], [], max_chars=220,
        )
        assert kept == []
        assert 'longer than' in rejected[0][1]

    def test_variants_below_the_serializer_minimum_are_dropped(self):
        """WorkBulletSerializer rejects under 10 characters, so returning one
        would offer the user a suggestion the API then refuses to save."""
        kept, _ = guard.ground_variants([self._variant('Did it.')], [], max_chars=220, min_chars=10)
        assert kept == []

    def test_text_is_stripped_in_place(self):
        kept, _ = guard.ground_variants(
            [self._variant('  Built a deploy pipeline.  ')], [], max_chars=220,
        )
        assert kept[0].text == 'Built a deploy pipeline.'


class TestWantsAMetric:
    def test_a_line_without_a_figure_wants_one(self):
        assert guard.wants_a_metric('Introduced a Redis caching layer.') is True

    def test_a_line_with_a_figure_does_not(self):
        assert guard.wants_a_metric('Raised coverage from 54% to 93%.') is False


@pytest.mark.django_db
class TestResolveSkills:
    def test_a_canonical_name_resolves_and_is_verified(self, canonical_skills):
        resolved = guard.resolve_skills([SkillCandidate(name='python', evidence='wrote Python')])

        assert resolved[0]['name'] == 'Python'
        assert resolved[0]['is_verified'] is True
        assert resolved[0]['category'] == 'Languages'

    def test_an_alias_resolves_to_its_canonical_name(self, canonical_skills):
        resolved = guard.resolve_skills([SkillCandidate(name='postgres', evidence='used postgres')])

        assert resolved[0]['name'] == 'PostgreSQL'
        assert resolved[0]['is_verified'] is True

    def test_a_substring_of_an_alias_is_not_treated_as_a_match(self, canonical_skills):
        """The alias lookup is a substring query, so 'script' hits
        'ecmascript'. Accepting that would relabel it as JavaScript."""
        resolved = guard.resolve_skills([SkillCandidate(name='script', evidence='x')])

        assert resolved[0]['name'] == 'script'
        assert resolved[0]['is_verified'] is False

    def test_a_canonical_name_wins_over_another_skills_alias(self, canonical_skills):
        """'Java' is a canonical skill and also a substring of 'JavaScript'.
        The exact name must win, or a real skill silently becomes freetext."""
        resolved = guard.resolve_skills([SkillCandidate(name='Java', evidence='wrote Java')])

        assert resolved[0]['name'] == 'Java'
        assert resolved[0]['is_verified'] is True

    def test_an_unknown_skill_is_kept_as_unverified_freetext(self, canonical_skills):
        resolved = guard.resolve_skills([SkillCandidate(name='Blorptran', evidence='x')])

        assert resolved[0]['name'] == 'Blorptran'
        assert resolved[0]['is_verified'] is False
        assert resolved[0]['canonical_id'] is None

    def test_duplicates_collapse(self, canonical_skills):
        resolved = guard.resolve_skills([
            SkillCandidate(name='Python', evidence='a'),
            SkillCandidate(name='python', evidence='b'),
        ])
        assert len(resolved) == 1

    def test_blank_names_are_discarded(self, canonical_skills):
        assert guard.resolve_skills([SkillCandidate(name='   ', evidence='')]) == []


def test_drop_existing_is_case_insensitive():
    skills = [{'name': 'Python'}, {'name': 'Redis'}]
    assert guard.drop_existing(skills, ['python']) == [{'name': 'Redis'}]
