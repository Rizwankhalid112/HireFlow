"""End-to-end through the suggestion services, with the model call stubbed.

Every test here patches `complete`. Nothing in this suite is allowed to make a
real API call: it would be slow, non-deterministic, and would spend money on
every CI run.
"""

import pytest

from apps.cv_builder.models import AISuggestionLog
from apps.cv_builder.services.ai import suggest
from apps.cv_builder.services.ai.client import Usage
from apps.cv_builder.services.ai.schemas import (
    BulletSuggestions,
    GapQuestion,
    SkillCandidate,
    SkillSuggestions,
    SummarySuggestions,
    TextVariant,
    TitleSuggestions,
    TitleVariant,
)


def stub(parsed, usage=None):
    """Replace the model call with a fixed parsed response."""
    def _complete(system_prompt, user_content, output_format):
        _complete.seen = {'system': system_prompt, 'user': user_content}
        return parsed, usage or Usage(input_tokens=900, output_tokens=200, cached_tokens=800)

    return _complete


@pytest.fixture
def experience(sample_cv):
    return sample_cv.work_experiences.first()


@pytest.mark.django_db
class TestSuggestBullets:
    def test_grounded_variants_come_back_and_are_logged(self, monkeypatch, experience):
        parsed = BulletSuggestions(
            variants=[
                TextVariant(text='Raised test coverage from 54% to 93%.', grounded_in=['54% to 93%']),
                TextVariant(text='Backfilled unit and integration tests across the service.', grounded_in=[]),
            ],
            gaps=[],
        )
        monkeypatch.setattr(suggest, 'complete', stub(parsed))

        result = suggest.suggest_bullets(experience, note='coverage went from 54 to 93')

        assert len(result['variants']) == 2
        assert AISuggestionLog.objects.filter(cv=experience.cv, section='bullets').count() == 1

    def test_a_fabricated_metric_is_dropped_before_the_user_sees_it(
        self, monkeypatch, experience,
    ):
        parsed = BulletSuggestions(
            variants=[
                TextVariant(text='Cut API latency by 40% using Redis.', grounded_in=[]),
                TextVariant(text='Cut API latency by introducing Redis caching.', grounded_in=[]),
            ],
            gaps=[],
        )
        monkeypatch.setattr(suggest, 'complete', stub(parsed))

        result = suggest.suggest_bullets(experience, note='added redis caching to the api')

        texts = [variant['text'] for variant in result['variants']]
        assert '40%' not in ' '.join(texts)
        assert result['rejected'] == 1

    def test_a_metricless_result_gets_a_gap_question_even_if_the_model_forgot(
        self, monkeypatch, experience,
    ):
        """The deterministic half of the gap prompt. It must not depend on the
        model choosing to cooperate."""
        parsed = BulletSuggestions(
            variants=[TextVariant(text='Introduced a Redis caching layer.', grounded_in=[])],
            gaps=[],
        )
        monkeypatch.setattr(suggest, 'complete', stub(parsed))

        result = suggest.suggest_bullets(experience, note='added redis caching')

        assert len(result['gaps']) == 1
        assert result['gaps'][0]['field'] == 'impact'

    def test_a_result_that_already_has_a_metric_is_not_nagged(self, monkeypatch, experience):
        parsed = BulletSuggestions(
            variants=[TextVariant(text='Raised coverage from 54% to 93%.', grounded_in=[])],
            gaps=[],
        )
        monkeypatch.setattr(suggest, 'complete', stub(parsed))

        result = suggest.suggest_bullets(experience, note='coverage 54 to 93')

        assert result['gaps'] == []

    def test_the_model_gets_the_existing_bullets_so_it_does_not_repeat_them(
        self, monkeypatch, experience,
    ):
        stubbed = stub(BulletSuggestions(variants=[], gaps=[]))
        monkeypatch.setattr(suggest, 'complete', stubbed)

        suggest.suggest_bullets(experience, note='did a thing')

        assert 'Cut checkout latency' in stubbed.seen['user']

    def test_no_user_data_reaches_the_cached_system_prompt(self, monkeypatch, experience):
        """If the user's name ends up in `system`, the prefix is unique per user
        and prompt caching silently stops working for everyone."""
        stubbed = stub(BulletSuggestions(variants=[], gaps=[]))
        monkeypatch.setattr(suggest, 'complete', stubbed)

        suggest.suggest_bullets(experience, note='secret note text')

        assert 'secret note text' not in stubbed.seen['system']
        assert experience.company_name not in stubbed.seen['system']


@pytest.mark.django_db
class TestSuggestSummary:
    def test_variants_are_returned_and_logged(self, monkeypatch, sample_cv):
        parsed = SummarySuggestions(
            variants=[TextVariant(
                text=(
                    'Backend engineer building payment systems in Python, with '
                    'ownership from schema design through on-call.'
                ),
                grounded_in=['Backend Engineer'],
            )],
            gaps=[],
        )
        monkeypatch.setattr(suggest, 'complete', stub(parsed))

        result = suggest.suggest_summary(sample_cv)

        assert len(result['variants']) == 1
        assert AISuggestionLog.objects.filter(section='summary').count() == 1

    def test_the_whole_cv_is_sent(self, monkeypatch, sample_cv):
        stubbed = stub(SummarySuggestions(variants=[], gaps=[]))
        monkeypatch.setattr(suggest, 'complete', stubbed)

        suggest.suggest_summary(sample_cv)

        sent = stubbed.seen['user']
        assert 'Analytical Engines' in sent      # a role
        assert 'University of London' in sent    # education
        assert 'PostgreSQL' in sent              # a skill


@pytest.mark.django_db
class TestSuggestSkills:
    def test_evidenced_skills_resolve_against_the_canonical_table(
        self, monkeypatch, sample_cv, canonical_skills,
    ):
        # 'js' rather than 'postgres': the fixture CV already lists PostgreSQL,
        # so it would be correctly dropped as a duplicate before we could see
        # whether the alias resolved.
        parsed = SkillSuggestions(
            evidenced=[SkillCandidate(name='js', evidence='built the frontend')],
            suggested_for_role=[SkillCandidate(name='Kubernetes', evidence='')],
        )
        monkeypatch.setattr(suggest, 'complete', stub(parsed))

        result = suggest.suggest_skills(sample_cv)

        evidenced = result['evidenced']
        assert evidenced[0]['name'] == 'JavaScript'
        assert evidenced[0]['is_verified'] is True
        assert evidenced[0]['category'] == 'Languages'
        assert [skill['name'] for skill in result['suggested_for_role']] == ['Kubernetes']

    def test_skills_already_on_the_cv_are_not_suggested_again(
        self, monkeypatch, sample_cv, canonical_skills,
    ):
        parsed = SkillSuggestions(
            evidenced=[SkillCandidate(name='Python', evidence='wrote Python')],
            suggested_for_role=[],
        )
        monkeypatch.setattr(suggest, 'complete', stub(parsed))

        result = suggest.suggest_skills(sample_cv)

        assert result['evidenced'] == []

    def test_an_evidenced_skill_with_no_evidence_is_demoted_not_promoted(
        self, monkeypatch, sample_cv, canonical_skills,
    ):
        """Claiming evidence without supplying it is the model's way of
        smuggling an aspirational skill into the one-click list."""
        parsed = SkillSuggestions(
            evidenced=[SkillCandidate(name='Kubernetes', evidence='')],
            suggested_for_role=[],
        )
        monkeypatch.setattr(suggest, 'complete', stub(parsed))

        result = suggest.suggest_skills(sample_cv)

        assert result['evidenced'] == []
        assert [skill['name'] for skill in result['suggested_for_role']] == ['Kubernetes']


@pytest.mark.django_db
class TestSuggestTitle:
    def test_variants_are_returned(self, monkeypatch, sample_cv):
        parsed = TitleSuggestions(variants=[
            TitleVariant(text='Backend Engineer', why='The most widely posted form.'),
        ])
        monkeypatch.setattr(suggest, 'complete', stub(parsed))

        result = suggest.suggest_title(sample_cv)

        assert result['variants'][0]['text'] == 'Backend Engineer'
        assert result['variants'][0]['why']


@pytest.mark.django_db
def test_usage_is_recorded_for_cost_attribution(monkeypatch, sample_cv):
    parsed = SummarySuggestions(variants=[], gaps=[])
    monkeypatch.setattr(
        suggest, 'complete',
        stub(parsed, Usage(input_tokens=1100, output_tokens=250, cached_tokens=900)),
    )

    suggest.suggest_summary(sample_cv)
    log = AISuggestionLog.objects.get()

    assert (log.input_tokens, log.output_tokens, log.cached_tokens) == (1100, 250, 900)
    assert log.input_digest


@pytest.mark.django_db
def test_a_figure_from_a_sibling_bullet_does_not_license_a_new_one(monkeypatch, experience):
    """The role's other bullets are shown to the model for de-duplication, but
    a number belonging to one achievement must not silently attach itself to a
    different one. The fixture's existing bullet already contains "40%"."""
    assert '40%' in experience.bullets.first().text

    parsed = BulletSuggestions(
        variants=[TextVariant(text='Cut API latency by 40% using Redis.', grounded_in=[])],
        gaps=[],
    )
    monkeypatch.setattr(suggest, 'complete', stub(parsed))

    result = suggest.suggest_bullets(experience, note='added redis caching')

    assert result['variants'] == []
    assert result['rejected'] == 1
