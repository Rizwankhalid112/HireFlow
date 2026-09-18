"""Mapping a real CV onto our schema.

Two things the prompt is responsible for but must not be *solely* responsible
for: the Languages collision, and not losing sections we cannot model. A prompt
is guidance; these assert the mechanical half that holds when the model is
wrong.
"""

import pytest

from apps.cv_builder.services import parse_normalize as pn
from apps.cv_builder.services.ai import schemas
from apps.cv_builder.tests import factories as f


@pytest.mark.django_db
class TestTheLanguagesTrap:
    """A CV heading its programming languages "Languages" is common, and
    `Python (native speaker)` is exactly the sort of error that looks plausible
    enough to reach an employer."""

    def test_programming_languages_are_moved_into_skills(self, canonical_skills):
        payload = pn.normalize(f.parsed_cv(languages=[
            f.language(language_name='Python', proficiency='native'),
            f.language(language_name='JavaScript', proficiency='fluent'),
        ]))

        assert payload['languages'] == []
        assert {row['name'] for row in payload['skills']} == {'Python', 'JavaScript'}

    def test_spoken_languages_are_left_alone(self, canonical_skills):
        payload = pn.normalize(f.parsed_cv(languages=[
            f.language(language_name='English', proficiency='native'),
            f.language(language_name='Urdu', proficiency='fluent'),
        ]))

        assert [row['language_name'] for row in payload['languages']] == ['English', 'Urdu']
        assert payload['skills'] == []

    def test_a_mixed_section_is_split(self, canonical_skills):
        payload = pn.normalize(f.parsed_cv(languages=[
            f.language(language_name='English', proficiency='native'),
            f.language(language_name='Python', proficiency='native'),
        ]))

        assert [row['language_name'] for row in payload['languages']] == ['English']
        assert [row['name'] for row in payload['skills']] == ['Python']

    def test_the_user_is_told_it_happened(self, canonical_skills):
        """We overrode a section of their CV. Even when we are right, that is
        something they should be able to see and disagree with."""
        payload = pn.normalize(f.parsed_cv(languages=[f.language(language_name='Python')]))
        assert any('Python' in note and 'Skills' in note for note in payload['notes'])

    def test_a_rescued_language_is_resolved_like_any_other_skill(self, canonical_skills):
        """It goes through the same canonical lookup, so it arrives verified
        and categorised rather than as freetext."""
        payload = pn.normalize(f.parsed_cv(languages=[f.language(language_name='postgres')]))
        row = payload['skills'][0]
        assert row['name'] == 'PostgreSQL'
        assert row['is_verified'] is True

    def test_a_rescued_language_does_not_duplicate_an_existing_skill(self, canonical_skills):
        payload = pn.normalize(f.parsed_cv(
            skills=[f.skill(name='Python')],
            languages=[f.language(language_name='Python')],
        ))
        assert len(payload['skills']) == 1


class TestTheSchemaConstrainsVocabulary:
    """Layer 1. These assert the enum sets match the models exactly — a value
    the model can emit that our column rejects is a failed import, and a value
    our column accepts that is missing here is data we silently cannot capture.
    """

    def test_employment_types_match_the_model(self):
        from apps.cv_builder.models import WorkExperience

        allowed = set(schemas.EmploymentType.__args__)
        model_values = {value for value, _ in WorkExperience.EmploymentType.choices}
        assert allowed == model_values | {''}

    def test_location_types_match_the_model(self):
        from apps.cv_builder.models import WorkExperience

        allowed = set(schemas.LocationType.__args__)
        model_values = {value for value, _ in WorkExperience.LocationType.choices}
        assert allowed == model_values | {''}

    def test_degree_types_match_the_model(self):
        from apps.cv_builder.models import Education

        allowed = set(schemas.DegreeType.__args__)
        model_values = {value for value, _ in Education.DegreeType.choices}
        assert allowed == model_values | {''}

    def test_skill_categories_match_the_canonical_table(self):
        from apps.cv_builder.models import SkillCanonical

        allowed = set(schemas.SkillCategory.__args__)
        model_values = {value for value, _ in SkillCanonical.Category.choices}
        assert allowed == model_values | {''}

    def test_language_proficiencies_match_the_model(self):
        from apps.cv_builder.models import CVLanguage

        allowed = set(schemas.LanguageProficiency.__args__)
        model_values = {value for value, _ in CVLanguage.Proficiency.choices}
        assert allowed == model_values | {''}

    def test_skill_proficiencies_match_the_model(self):
        from apps.cv_builder.models import CVSkill

        allowed = set(schemas.SkillProficiency.__args__)
        model_values = {value for value, _ in CVSkill.Proficiency.choices}
        assert allowed == model_values | {''}

    def test_every_enum_can_express_not_stated(self):
        """Without an empty member the model is forced to pick a value it has
        no evidence for, which is the definition of a guess."""
        for literal in (
            schemas.EmploymentType, schemas.LocationType, schemas.DegreeType,
            schemas.SkillCategory, schemas.SkillProficiency, schemas.LanguageProficiency,
        ):
            assert '' in literal.__args__
