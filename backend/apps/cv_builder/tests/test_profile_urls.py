"""Scheme-less URLs on the profile endpoint.

People write `linkedin.com/in/you`. DRF's `URLField` rejected it inside
`to_internal_value()`, which runs *before* `validate_<field>()` — so the
normalizer that existed to fix this never saw the value, and the frontend had to
prepend `https://` itself. The CV import, meanwhile, accepted scheme-less URLs
happily, so the same input got two different answers depending on the door it
came through.
"""

import pytest
from django.urls import reverse


@pytest.mark.django_db
class TestSchemelessUrls:
    @pytest.mark.parametrize('field,value,expected', [
        ('linkedin_url', 'linkedin.com/in/ada', 'https://linkedin.com/in/ada'),
        ('github_url', 'github.com/ada', 'https://github.com/ada'),
        ('portfolio_url', 'ada.dev', 'https://ada.dev'),
    ])
    def test_a_bare_url_is_accepted_and_normalised(self, api, sample_cv, field, value, expected):
        response = api.patch(reverse('cv-profile'), {field: value}, format='json')

        assert response.status_code == 200, response.data
        assert response.data[field] == expected

    def test_an_explicit_scheme_is_left_alone(self, api, sample_cv):
        response = api.patch(
            reverse('cv-profile'), {'github_url': 'http://github.com/ada'}, format='json',
        )
        assert response.data['github_url'] == 'http://github.com/ada'

    def test_a_protocol_relative_url_gets_https(self, api, sample_cv):
        response = api.patch(
            reverse('cv-profile'), {'github_url': '//github.com/ada'}, format='json',
        )
        assert response.data['github_url'] == 'https://github.com/ada'

    def test_blank_stays_blank(self, api, sample_cv):
        response = api.patch(reverse('cv-profile'), {'github_url': ''}, format='json')
        assert response.status_code == 200
        assert response.data['github_url'] == ''

    def test_the_linkedin_domain_check_still_applies(self, api, sample_cv):
        response = api.patch(
            reverse('cv-profile'), {'linkedin_url': 'example.com/ada'}, format='json',
        )
        assert response.status_code == 400
        assert 'LinkedIn' in str(response.data)

    def test_genuine_nonsense_is_still_rejected(self, api, sample_cv):
        """Normalising the scheme must not turn the field into a free-text box."""
        response = api.patch(
            reverse('cv-profile'), {'github_url': 'not a url at all'}, format='json',
        )
        assert response.status_code == 400

    def test_the_form_and_the_import_now_agree(self, api, sample_cv):
        """The inconsistency this fix closes: both paths take the same input."""
        from apps.cv_builder.services.parse_normalize import _url

        assert _url('linkedin.com/in/ada') == 'https://linkedin.com/in/ada'
        response = api.patch(
            reverse('cv-profile'), {'linkedin_url': 'linkedin.com/in/ada'}, format='json',
        )
        assert response.data['linkedin_url'] == _url('linkedin.com/in/ada')
