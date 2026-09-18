"""Layer 2: what the schema cannot enforce.

Every rule here exists because a real CV would otherwise fail the import with a
DataError or a serializer rejection. These are the cheapest tests in the module
— pure functions over plain data — and they cover the failures that would
otherwise only appear when a user uploads an unusual CV.
"""

from decimal import Decimal

import pytest

from apps.cv_builder.services import parse_normalize as pn
from apps.cv_builder.tests import factories as f


class TestCgpa:
    """CGPA is a DecimalField(max_digits=3, decimal_places=2), so it physically
    cannot hold a percentage. Storing one raises; dropping it does not."""

    @pytest.mark.parametrize('raw,expected', [
        ('3.3/4.0', (Decimal('3.3'), Decimal('4.0'))),
        ('3.72', (Decimal('3.72'), None)),
        ('9.1 out of 10', (Decimal('9.1'), Decimal('10'))),
    ])
    def test_a_real_grade_is_kept(self, raw, expected):
        assert pn.parse_cgpa(raw) == expected

    @pytest.mark.parametrize('raw', ['85%', 'First Class Honours', '', '   ', '12.0'])
    def test_what_cannot_be_a_cgpa_is_dropped(self, raw):
        assert pn.parse_cgpa(raw) == (None, None)

    def test_a_grade_above_its_own_scale_is_dropped(self):
        """'4.0/3.3' is the two numbers swapped, and there is no way to tell
        which the user meant."""
        assert pn.parse_cgpa('4.0/3.3') == (None, None)

    def test_a_bare_grade_over_four_gets_a_ten_point_scale(self):
        """EducationSerializer defaults an absent scale to 4.0 and rejects a
        CGPA above its scale, so a bare '9.1' is unstorable without this."""
        cgpa, scale = pn.parse_cgpa('9.1')
        assert cgpa == Decimal('9.1')
        assert scale == Decimal('10.0')


class TestUrls:
    def test_a_bare_url_gets_a_scheme(self):
        """CVs write it this way constantly and URLValidator rejects it, so
        without this a large share of imports would silently lose their links."""
        assert pn._url('linkedin.com/in/ada') == 'https://linkedin.com/in/ada'

    def test_an_existing_scheme_is_left_alone(self):
        assert pn._url('http://example.com') == 'http://example.com'

    def test_empty_stays_empty(self):
        assert pn._url('') == ''
        assert pn._url(None) == ''


class TestYears:
    @pytest.mark.parametrize('value', [0, None, '', 1900, 12, 3025, 'nonsense'])
    def test_nonsense_becomes_none(self, value):
        assert pn._year(value) is None

    def test_a_real_year_survives(self):
        assert pn._year(2021) == 2021

    def test_next_year_is_allowed(self):
        """An expected graduation date is legitimately in the future."""
        from django.utils import timezone
        assert pn._year(timezone.now().year + 1) is not None


@pytest.mark.django_db
class TestExperiences:
    def test_strings_are_truncated_to_what_the_column_holds(self):
        payload = pn.normalize(f.parsed_cv(work_experience=[
            f.experience(company_name='A' * 400, role_title='B' * 400),
        ]))
        row = payload['work_experience'][0]
        assert len(row['company_name']) == 200
        assert len(row['role_title']) == 200

    def test_short_bullets_are_dropped_and_the_role_survives(self):
        """WorkBulletSerializer rejects under 10 chars. Letting the fragment
        through would fail the whole role over a stray column header."""
        payload = pn.normalize(f.parsed_cv(work_experience=[
            f.experience(bullets=['Java, SQL', 'Cut checkout latency by 40% this quarter.']),
        ]))
        assert payload['work_experience'][0]['bullets'] == [
            'Cut checkout latency by 40% this quarter.',
        ]

    def test_a_reversed_date_range_is_swapped(self):
        payload = pn.normalize(f.parsed_cv(work_experience=[
            f.experience(start_year=2023, end_year=2020),
        ]))
        row = payload['work_experience'][0]
        assert (row['start_year'], row['end_year']) == (2020, 2023)

    def test_a_current_role_has_no_end_date(self):
        payload = pn.normalize(f.parsed_cv(work_experience=[
            f.experience(is_current=True, end_year=2024, end_month=6),
        ]))
        row = payload['work_experience'][0]
        assert row['end_year'] is None and row['end_month'] is None

    def test_a_row_with_neither_company_nor_title_is_not_a_job(self):
        payload = pn.normalize(f.parsed_cv(work_experience=[
            f.experience(company_name='', role_title=''),
        ]))
        assert payload['work_experience'] == []

    def test_a_missing_start_year_is_flagged_not_invented(self):
        """start_year is NOT NULL. The tempting shortcut is to guess one."""
        payload = pn.normalize(f.parsed_cv(work_experience=[
            f.experience(start_year=0),
        ]))
        row = payload['work_experience'][0]
        assert row['start_year'] is None
        assert row['needs_attention'] == ['start_year']


@pytest.mark.django_db
class TestEducation:
    def test_graduation_year_only_is_flagged(self):
        """The single most common shape of a real education line: 'BSc
        Computer Science, MIT, 2019' gives no start year at all."""
        payload = pn.normalize(f.parsed_cv(education=[
            f.education(start_year=0, end_year=2019),
        ]))
        row = payload['education'][0]
        assert row['end_year'] == 2019
        assert row['start_year'] is None
        assert row['needs_attention'] == ['start_year']

    def test_a_percentage_grade_does_not_reach_the_cgpa_column(self):
        payload = pn.normalize(f.parsed_cv(education=[f.education(cgpa='85%')]))
        assert payload['education'][0]['cgpa'] is None

    def test_an_assumed_scale_is_reported_to_the_user(self):
        payload = pn.normalize(f.parsed_cv(education=[
            f.education(institution='IIT Delhi', cgpa='9.1'),
        ]))
        assert any('10-point' in note for note in payload['notes'])

    def test_an_entry_with_no_institution_is_dropped(self):
        payload = pn.normalize(f.parsed_cv(education=[f.education(institution='')]))
        assert payload['education'] == []


@pytest.mark.django_db
class TestSkills:
    def test_duplicates_collapse_case_insensitively(self):
        payload = pn.normalize(f.parsed_cv(skills=[
            f.skill(name='Python'), f.skill(name='python'), f.skill(name='PYTHON'),
        ]))
        assert len(payload['skills']) == 1

    def test_a_canonical_match_supplies_the_spelling_and_category(self, canonical_skills):
        """'postgres' and 'PostgreSQL' must not become two chips on the CV."""
        payload = pn.normalize(f.parsed_cv(skills=[f.skill(name='postgres')]))
        row = payload['skills'][0]
        assert row['name'] == 'PostgreSQL'
        assert row['category'] == 'Databases'
        assert row['is_verified'] is True

    def test_an_unknown_skill_is_kept_as_freetext(self, canonical_skills):
        payload = pn.normalize(f.parsed_cv(skills=[
            f.skill(name='Internal Tooling', category='Tools'),
        ]))
        row = payload['skills'][0]
        assert row['name'] == 'Internal Tooling'
        assert row['is_verified'] is False
        assert row['category'] == 'Tools'

    def test_java_does_not_lose_to_javascript(self, canonical_skills):
        """The alias lookup is a substring search, so this pair is where a
        naive resolver silently relabels one skill as the other."""
        payload = pn.normalize(f.parsed_cv(skills=[f.skill(name='Java')]))
        assert payload['skills'][0]['name'] == 'Java'


@pytest.mark.django_db
class TestProjects:
    def test_tech_stack_is_capped_at_what_the_serializer_accepts(self):
        """CVProjectSerializer rejects more than 10, which would fail the whole
        project over a long technology list."""
        payload = pn.normalize(f.parsed_cv(projects=[
            f.project(tech_stack=[f'tech{n}' for n in range(20)]),
        ]))
        assert len(payload['projects'][0]['tech_stack']) == 10


@pytest.mark.django_db
class TestUnmappedSections:
    def test_they_survive_normalisation(self):
        """Silently dropping a user's Publications list is the worst outcome
        this feature can produce."""
        payload = pn.normalize(f.parsed_cv(unmapped_sections=[
            f.unmapped(heading='Awards', content='Best paper, 2021.'),
        ]))
        assert payload['unmapped_sections'] == [
            {'heading': 'Awards', 'content': 'Best paper, 2021.'},
        ]

    def test_a_section_with_no_heading_still_gets_one(self):
        payload = pn.normalize(f.parsed_cv(unmapped_sections=[
            f.unmapped(heading='', content='Some text.'),
        ]))
        assert payload['unmapped_sections'][0]['heading'] == 'Untitled section'


@pytest.mark.django_db
def test_the_payload_survives_a_json_round_trip():
    """It is stored in a JSONField and read back by the frontend, so a Decimal
    or a date object anywhere in it would blow up at save time."""
    import json

    payload = pn.normalize(f.parsed_cv(
        personal=f.personal(full_name='Ada'),
        education=[f.education(cgpa='3.3/4.0')],
        work_experience=[f.experience(bullets=['Built the thing that does stuff.'])],
    ))
    assert json.loads(json.dumps(payload))['education'][0]['cgpa'] == '3.3'
