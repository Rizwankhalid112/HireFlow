"""A brand new CV is an empty shell, and every template has to survive it.

The client skips the render for an empty CV and shows a placeholder instead, but
that is a presentation choice — the server must not be the thing that makes it
mandatory.
"""

import pytest

from apps.cv_builder.services.pdf_renderer import render_cv_pdf
from apps.cv_builder.templates_registry import CV_TEMPLATES, DEFAULT_TEMPLATE_ID


@pytest.mark.slow
@pytest.mark.django_db
@pytest.mark.parametrize('template_id', sorted(CV_TEMPLATES))
def test_an_empty_cv_renders_on_every_template(empty_cv, template_id):
    pdf_bytes, page_count = render_cv_pdf(empty_cv, template_id)

    assert pdf_bytes.startswith(b'%PDF')
    assert page_count == 1


@pytest.mark.django_db
def test_a_new_cv_always_has_a_template_id(api, user):
    """Nothing downstream handles a null template_id — the renderer would fall
    back, but the picker would show nothing selected.

    Read through GET rather than the POST response: the creation serializer is
    deliberately minimal (id and score only).
    """
    created = api.post('/api/cv/profile/')
    assert created.status_code in (200, 201)

    profile = api.get('/api/cv/profile/').json()

    assert profile['template_id'] == DEFAULT_TEMPLATE_ID


@pytest.mark.django_db
def test_the_preview_of_an_empty_cv_is_a_pdf_not_an_error(api, empty_cv):
    response = api.get('/api/cv/preview/')

    assert response.status_code == 200
    assert response.content.startswith(b'%PDF')
