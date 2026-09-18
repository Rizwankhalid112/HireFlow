"""The normalisation rules, each of which exists because the live data needed it."""

import pytest
from django.utils import timezone

from apps.jobs.services import normalise


class TestDescriptions:
    def test_greenhouse_entity_escaped_html_is_readable(self):
        """The trap: Greenhouse sends HTML that has been entity-encoded, so it
        arrives as `&lt;h2&gt;`. Stripping tags before unescaping leaves the
        markup visible to the user as literal text."""
        raw = '&lt;h2&gt;About&lt;/h2&gt;&lt;p&gt;We build things.&lt;/p&gt;'
        out = normalise.clean_description(raw, is_html=True)
        assert '<' not in out and '&lt;' not in out
        assert 'About' in out and 'We build things.' in out

    def test_raw_html_is_stripped(self):
        out = normalise.clean_description('<p>Hello</p><ul><li>One</li></ul>', is_html=True)
        assert '<' not in out
        assert 'Hello' in out and 'One' in out

    def test_plain_text_passes_through(self):
        out = normalise.clean_description('Just words.', is_html=False)
        assert out == 'Just words.'

    def test_empty_is_safe(self):
        assert normalise.clean_description(None, is_html=True) == ''


class TestDates:
    def test_iso_string(self):
        assert normalise.parse_date('2026-01-15T10:00:00Z').year == 2026

    def test_epoch_milliseconds(self):
        """Lever publishes epoch millis, not ISO."""
        assert normalise.parse_date(1259971200000).year == 2009

    def test_naive_datetime_gets_a_timezone(self):
        assert normalise.parse_date('2026-01-15').tzinfo is not None

    def test_a_future_date_is_rejected(self):
        """It would sort above every real job and cannot be true."""
        future = (timezone.now() + timezone.timedelta(days=30)).isoformat()
        assert normalise.parse_date(future) is None

    @pytest.mark.parametrize('value', [None, '', 'not a date', {}])
    def test_junk_is_none(self, value):
        assert normalise.parse_date(value) is None


class TestLocation:
    @pytest.mark.parametrize('raw,city,country', [
        ('Dublin, Ireland', 'Dublin', 'Ireland'),
        ('Karachi, Pakistan', 'Karachi', 'Pakistan'),
        ('London, United Kingdom', 'London', 'United Kingdom'),
        ('Tokyo, Japan ', 'Tokyo', 'Japan'),
        ('Singapore', '', 'Singapore'),
    ])
    def test_recognised_countries(self, raw, city, country):
        assert normalise.split_location(raw) == (city, country)

    def test_a_us_state_implies_the_country(self):
        """"New York, NY" never says United States, but it means it."""
        assert normalise.split_location('New York, NY') == ('New York', 'United States')
        assert normalise.split_location('Menlo Park, California')[1] == 'United States'

    def test_an_unrecognised_name_leaves_country_blank(self):
        """Storing "San Francisco" as a country would make a country filter
        actively wrong. Blank is honest."""
        city, country = normalise.split_location('San Francisco')
        assert city == 'San Francisco'
        assert country == ''

    def test_multiple_offices_take_the_first(self):
        assert normalise.split_location('Menlo Park, CA; New York') == ('Menlo Park', 'United States')

    @pytest.mark.parametrize('junk', ['N/A', 'none', '-', '', 'Various'])
    def test_junk_locations_are_dropped(self, junk):
        assert normalise.split_location(junk) == ('', '')


class TestRemoteDetection:
    def test_remote_wording(self):
        assert normalise.detect_remote('Remote, United States') == 'remote'

    def test_hybrid_beats_remote(self):
        assert normalise.detect_remote('Hybrid — 2 days remote') == 'hybrid'

    def test_unknown_stays_blank_rather_than_guessing_onsite(self):
        """Greenhouse has no remote field, so this is inferred. Defaulting to
        on-site would be a claim we cannot support."""
        assert normalise.detect_remote('Dublin, Ireland') == ''


class TestTruncation:
    def test_long_values_are_cut_to_the_column_width(self):
        """A DataError mid-run loses the whole batch."""
        row = normalise.normalised(
            source='greenhouse', external_id='1', title='T' * 500,
            company_name='C' * 400, location_raw='L' * 400, apply_url='u',
        )
        assert len(row['title']) == 300
        assert len(row['company_name']) == 200
        assert len(row['location_raw']) == 300
