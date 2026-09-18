"""template_id arrives from the client, so it is an allowlist lookup and never
a path. These tests pin that, plus ownership isolation on the preview."""

import pytest

TRAVERSAL = [
    '../../../etc/passwd',
    '../base',
    'cv_templates/minimal.html',
    'minimal.html',
]


@pytest.mark.django_db
@pytest.mark.parametrize('template_id', TRAVERSAL)
def test_path_traversal_is_rejected(api, sample_cv, template_id):
    response = api.get('/api/cv/preview/', {'template': template_id})

    assert response.status_code == 400
    assert 'template' in response.json()


@pytest.mark.django_db
def test_an_unknown_template_is_rejected_rather_than_silently_defaulted(api, sample_cv):
    """The renderer falls back to the default, but the *endpoint* must not:
    silently serving a different template than the one asked for would make the
    picker lie about what is selected."""
    response = api.get('/api/cv/preview/', {'template': 'gothic'})

    assert response.status_code == 400


@pytest.mark.django_db
def test_the_preview_only_ever_renders_the_callers_own_cv(api, sample_cv, other_user):
    """There is no id in the URL — the CV is resolved from request.user — so the
    guarantee to pin is that a second user gets their own CV, not this one."""
    from rest_framework.test import APIClient

    from apps.cv_builder.models import CVProfile

    CVProfile.objects.create(user=other_user, full_name='Grace Hopper', email=other_user.email)

    intruder = APIClient()
    intruder.force_authenticate(user=other_user)

    theirs = intruder.get('/api/cv/preview/?template=minimal')
    mine = api.get('/api/cv/preview/?template=minimal')

    assert theirs.status_code == 200
    assert theirs.content != mine.content
    assert theirs['ETag'] != mine['ETag']


@pytest.mark.django_db
def test_the_preview_requires_authentication(client, sample_cv):
    assert client.get('/api/cv/preview/').status_code == 401
