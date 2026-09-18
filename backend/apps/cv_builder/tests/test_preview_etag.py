"""ETag revalidation. The live preview re-requests on every save, and most of
those requests are for bytes the client already holds."""

import pytest


@pytest.mark.django_db
def test_first_request_returns_a_pdf_with_an_etag(api, sample_cv):
    response = api.get('/api/cv/preview/?template=minimal')

    assert response.status_code == 200
    assert response['Content-Type'] == 'application/pdf'
    assert response['ETag']
    assert response.content.startswith(b'%PDF')


@pytest.mark.django_db
def test_repeat_request_with_if_none_match_is_a_304_with_no_body(api, sample_cv):
    first = api.get('/api/cv/preview/?template=minimal')

    second = api.get('/api/cv/preview/?template=minimal', HTTP_IF_NONE_MATCH=first['ETag'])

    assert second.status_code == 304
    assert second.content == b''
    assert second['ETag'] == first['ETag']


@pytest.mark.django_db
def test_editing_content_invalidates_the_clients_etag(api, sample_cv):
    first = api.get('/api/cv/preview/?template=minimal')

    sample_cv.summary = f'{sample_cv.summary} A newly added closing line.'
    sample_cv.save()

    second = api.get('/api/cv/preview/?template=minimal', HTTP_IF_NONE_MATCH=first['ETag'])

    assert second.status_code == 200
    assert second['ETag'] != first['ETag']


@pytest.mark.django_db
def test_a_weak_validator_still_matches(api, sample_cv):
    """A proxy may weaken the ETag; that must not defeat revalidation."""
    first = api.get('/api/cv/preview/?template=minimal')

    weak = f'W/{first["ETag"]}'
    second = api.get('/api/cv/preview/?template=minimal', HTTP_IF_NONE_MATCH=weak)

    assert second.status_code == 304


@pytest.mark.django_db
def test_the_preview_is_never_stored_by_a_shared_cache(api, sample_cv):
    """This is one user's CV. `public` here would leak it via any proxy."""
    response = api.get('/api/cv/preview/?template=minimal')

    assert response['Cache-Control'] == 'private, must-revalidate'
