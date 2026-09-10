"""The two text extractors that had no tests and were both wrong.

Both feed things the user sees: `skills_demonstrated` is stored on every bullet,
and `extract_metric` decides whether the AI asks someone for a figure. Silent
wrongness in either is invisible until you read the data.
"""

import pytest

from apps.cv_builder.services.metric_extractor import extract_metric
from apps.cv_builder.services.skill_detector import (
    extract_skills_from_bullet,
    invalidate_skill_index,
)


@pytest.fixture(autouse=True)
def _fresh_index():
    invalidate_skill_index()
    yield
    invalidate_skill_index()


@pytest.mark.django_db
class TestSkillDetection:
    """The bug: matching was `name in text`, and 27 canonical skills are one or
    two characters. Every bullet came back tagged `R`, most also `C`."""

    def test_a_one_letter_skill_does_not_match_inside_a_word(self, canonical_skills):
        # 'checkout' contains c; 'fraud' contains r. Neither is a skill mention.
        found = extract_skills_from_bullet(
            'Cut checkout latency by 40% by replacing synchronous fraud checks.'
        )
        assert found == []

    def test_a_short_skill_matches_when_actually_mentioned(self, canonical_skills):
        assert 'Java' in extract_skills_from_bullet('Ported the parser to Java last year.')

    def test_prose_with_no_technology_finds_nothing(self, canonical_skills):
        assert extract_skills_from_bullet('Managed relationships with 30 enterprise clients.') == []

    def test_a_skill_at_the_end_of_a_sentence_is_found(self, canonical_skills):
        """The full stop is a token boundary, not part of the name — but `.` has
        to stay meaningful for `Node.js`, which is what makes this subtle."""
        assert 'Python' in extract_skills_from_bullet('Scripted the deployment in Python.')

    def test_an_alias_resolves_to_its_canonical_name(self, canonical_skills):
        found = extract_skills_from_bullet('Tuned postgres queries for the reporting service.')
        assert found == ['PostgreSQL']

    def test_one_skill_is_reported_once_not_once_per_alias(self, canonical_skills):
        """'PostgreSQL' used to return PostgreSQL, postgres, Postgres and SQL —
        four chips on the CV for one mention."""
        found = extract_skills_from_bullet('Migrated the monolith to PostgreSQL.')
        assert found == ['PostgreSQL']

    def test_order_follows_first_appearance(self, canonical_skills):
        found = extract_skills_from_bullet('Built it with Django, backed by PostgreSQL and Redis.')
        assert found == ['Django', 'PostgreSQL', 'Redis']

    def test_java_is_not_javascript(self, canonical_skills):
        assert extract_skills_from_bullet('Wrote the service in Java.') == ['Java']
        assert extract_skills_from_bullet('Wrote the widget in JavaScript.') == ['JavaScript']

    def test_empty_text_is_safe(self, canonical_skills):
        assert extract_skills_from_bullet('') == []

    def test_no_canonical_rows_is_safe(self, db):
        """A fresh deploy, before `seed_skills` has run."""
        assert extract_skills_from_bullet('Anything at all.') == []


class TestMetricExtraction:
    """The bug: patterns required a specific verb (`reduced X by 40%`) or exact
    adjacency (`30 clients`), so ordinary bullets returned nothing — and
    `wants_a_metric` then had the AI ask for a number already in the line."""

    @pytest.mark.parametrize('text,expected', [
        ('Cut checkout latency by 40% by replacing fraud checks.', '40%'),
        ('Improved page load speed by 60%.', '60%'),
        ('Raised coverage from 54% to 93% over two quarters.', '54% to 93%'),
        ('Managed relationships with over 30 enterprise clients.', '30 enterprise clients'),
        ('Shipped the platform to 12 countries.', '12 countries'),
        ('Saved $1.2M annually.', '$1.2M'),
        ('Made the importer 3x faster.', '3x'),
    ])
    def test_real_bullets_yield_their_figure(self, text, expected):
        assert extract_metric(text) == expected

    def test_a_range_beats_a_figure_nested_inside_it(self):
        """Longest-match, so the before/after pair survives rather than half of it."""
        assert extract_metric('Cut p99 from 800ms to 120ms.') == '800ms to 120ms'

    @pytest.mark.parametrize('text', [
        'Refactored the checkout flow for readability.',
        'Led the team through a platform migration.',
        '',
    ])
    def test_prose_with_no_figure_returns_none(self, text):
        assert extract_metric(text) is None

    def test_a_spelled_out_number_is_not_a_metric(self):
        """Documented limitation rather than an oversight: parsing English
        numerals is a different job, and the AI asking for the figure here is
        the right outcome."""
        assert extract_metric('Led a team of four engineers.') is None


@pytest.mark.django_db
class TestTheAiGapQuestionUsesThis:
    def test_a_bullet_with_a_percentage_is_not_asked_for_one(self):
        """The whole point of fixing the extractor: the assistant must not ask
        for a number the user already wrote."""
        from apps.cv_builder.services.ai.guardrails import wants_a_metric

        assert wants_a_metric('Cut checkout latency by 40%.') is False
        assert wants_a_metric('Refactored the checkout flow.') is True
