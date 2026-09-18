"""The preview is an exact snapshot of the file the user downloads.

This is the single most important guarantee in the CV Builder: the whole reason
the preview is a server render displayed through pdf.js, rather than a much
cheaper client-side HTML reproduction, is that a browser and WeasyPrint disagree
on font metrics and line breaking — and one different line break shifts
everything after it and can change the page count.

The download is produced from the very bytes the preview handed the client, so
this test pins the property that makes that safe: the same content always
renders to the same bytes.
"""

import pytest

from apps.cv_builder.services.pdf_renderer import render_cv_pdf


@pytest.mark.django_db
def test_the_endpoint_returns_exactly_what_the_renderer_produced(api, sample_cv):
    response = api.get('/api/cv/preview/?template=minimal')
    rendered, _ = render_cv_pdf(sample_cv, 'minimal')

    assert response.content == rendered


@pytest.mark.django_db
def test_two_requests_for_unchanged_content_return_identical_bytes(api, sample_cv):
    first = api.get('/api/cv/preview/?template=classic')
    second = api.get('/api/cv/preview/?template=classic')

    assert first.content == second.content


@pytest.mark.django_db
def test_the_reported_page_count_matches_the_rendered_document(api, sample_cv):
    response = api.get('/api/cv/preview/?template=minimal')
    meta = api.get('/api/cv/preview/meta/?template=minimal').json()

    assert int(response['X-CV-Page-Count']) == meta['page_count']
    assert meta['overflows'] is (meta['page_count'] > meta['max_pages'])
