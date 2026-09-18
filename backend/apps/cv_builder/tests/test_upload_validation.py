"""The upload endpoint.

This is the app's first user-supplied-file path other than the profile photo, so
this file is the security surface of the feature. The theme throughout: decide
what a file is by looking inside it, never by trusting what the client said.
"""

from unittest.mock import patch

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from apps.cv_builder.models import CVUploadLog

PDF_BYTES = b'%PDF-1.4\n' + b'x' * 500
DOCX_BYTES = b'PK\x03\x04' + b'x' * 500


@pytest.fixture(autouse=True)
def no_celery():
    """Never queue real work from a validation test."""
    with patch('apps.cv_builder.tasks.extract_text_from_cv.delay') as mock:
        yield mock


@pytest.fixture(autouse=True)
def no_throttle(settings):
    """The throttle has its own test; everywhere else it just breaks the suite
    on the sixth request."""
    settings.REST_FRAMEWORK = {
        **settings.REST_FRAMEWORK,
        'DEFAULT_THROTTLE_RATES': {'ai_suggest': '1000/min', 'cv_upload': '1000/min'},
    }


def upload(api, content=PDF_BYTES, name='cv.pdf', content_type='application/pdf'):
    return api.post(
        reverse('cv-upload'),
        {'file': SimpleUploadedFile(name, content, content_type=content_type)},
        format='multipart',
    )


@pytest.mark.django_db
class TestAccepting:
    def test_a_pdf_is_accepted_and_queued(self, api, sample_cv, no_celery):
        response = upload(api)

        assert response.status_code == 202
        assert response.data['status'] == 'pending'
        log = CVUploadLog.objects.get(id=response.data['log_id'])
        assert log.file_type == 'pdf'
        assert log.cv == sample_cv
        no_celery.assert_called_once_with(str(log.id))

    def test_a_docx_is_accepted(self, api, sample_cv):
        response = upload(
            api, DOCX_BYTES, 'cv.docx',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        )
        assert response.status_code == 202
        assert CVUploadLog.objects.get(id=response.data['log_id']).file_type == 'docx'

    def test_the_file_lands_under_the_users_own_directory(self, api, sample_cv, user):
        response = upload(api)
        log = CVUploadLog.objects.get(id=response.data['log_id'])
        assert log.file_path.startswith(f'cv_uploads/{user.id}/')


@pytest.mark.django_db
class TestRejecting:
    def test_an_empty_file_is_rejected(self, api, sample_cv):
        assert upload(api, b'').status_code == 400

    def test_an_oversized_file_is_rejected(self, api, sample_cv, settings):
        settings.CV_UPLOAD_MAX_BYTES = 1024
        response = upload(api, b'%PDF-1.4' + b'x' * 4000)
        assert response.status_code == 400
        assert 'smaller' in str(response.data).lower()

    def test_a_file_that_is_neither_is_rejected(self, api, sample_cv):
        assert upload(api, b'just some text', 'cv.txt', 'text/plain').status_code == 400

    def test_an_old_doc_file_gets_its_own_message(self, api, sample_cv):
        """The most common wrong upload, and "upload a PDF or DOCX" does not
        tell someone holding a .doc what to actually do."""
        response = upload(api, b'\xd0\xcf\x11\xe0' + b'x' * 100, 'cv.doc', 'application/msword')
        assert response.status_code == 400
        assert '.docx' in str(response.data)

    def test_a_spoofed_content_type_does_not_get_through(self, api, sample_cv):
        """content_type is supplied by the client. The magic bytes are the
        real check."""
        response = upload(api, b'<html>not a pdf at all</html>', 'cv.pdf', 'application/pdf')
        assert response.status_code == 400

    def test_a_renamed_pdf_is_still_read_as_a_pdf(self, api, sample_cv):
        """The mirror of the above: the bytes win over the extension in both
        directions, so a correct file with a wrong name still works."""
        response = upload(api, PDF_BYTES, 'resume.docx', '')
        assert response.status_code == 202
        assert CVUploadLog.objects.get(id=response.data['log_id']).file_type == 'pdf'


@pytest.mark.django_db
class TestFilenameSafety:
    def test_a_traversal_attempt_cannot_escape_the_directory(self, api, sample_cv, user):
        response = upload(api, PDF_BYTES, '../../../../etc/passwd')

        assert response.status_code == 202
        log = CVUploadLog.objects.get(id=response.data['log_id'])
        assert '..' not in log.file_path
        assert log.file_path.startswith(f'cv_uploads/{user.id}/')

    def test_a_very_long_filename_is_truncated(self, api, sample_cv):
        response = upload(api, PDF_BYTES, 'a' * 500 + '.pdf')
        log = CVUploadLog.objects.get(id=response.data['log_id'])
        assert len(log.file_path) < 300

    def test_a_filename_that_sanitises_to_nothing_still_works(self, api, sample_cv):
        """`get_valid_filename` raises rather than returning empty when a name
        reduces to nothing. Uncaught, that is a 500 on an odd filename.

        `..` cannot be tested here: Django rejects it when the UploadedFile is
        constructed, before any of our code runs."""
        response = upload(api, PDF_BYTES, '???')
        assert response.status_code == 202
        log = CVUploadLog.objects.get(id=response.data['log_id'])
        assert log.file_path.endswith('_cv')


@pytest.mark.django_db
class TestMetering:
    def test_the_monthly_cap_is_enforced_before_the_file_is_saved(self, api, sample_cv, settings):
        """A capped user must not leave a file on disk for the sweeper."""
        settings.AI_PARSE_MONTHLY_LIMIT = 2
        CVUploadLog.objects.create(
            cv=sample_cv, original_filename='a.pdf', file_type='pdf',
            file_path='x', parse_attempts=2,
        )

        response = upload(api)

        assert response.status_code == 429
        assert response.data['parses'] == {'used': 2, 'limit': 2}
        assert CVUploadLog.objects.filter(original_filename='cv.pdf').count() == 0

    def test_retries_count_towards_the_cap(self, sample_cv, settings):
        """A retry is a real metered call. Counting rows instead of attempts
        would make a retry loop free."""
        from apps.cv_builder.models import parses_used_this_period

        CVUploadLog.objects.create(
            cv=sample_cv, original_filename='a.pdf', file_type='pdf',
            file_path='x', parse_attempts=3,
        )
        assert parses_used_this_period(sample_cv) == 3

    def test_the_throttle_is_configured_on_the_endpoint(self):
        from apps.cv_builder.views.upload import CVUploadView

        assert CVUploadView.throttle_scope == 'cv_upload'


@pytest.mark.django_db
class TestOwnership:
    def test_another_users_log_is_not_visible(self, api, sample_cv, other_user):
        from apps.cv_builder.models import CVProfile

        other_profile = CVProfile.objects.create(user=other_user, email=other_user.email)
        other_log = CVUploadLog.objects.create(
            cv=other_profile, original_filename='theirs.pdf',
            file_type='pdf', file_path='x',
        )

        response = api.get(reverse('cv-upload-status', args=[other_log.id]))
        assert response.status_code == 404

    def test_anonymous_access_is_refused(self, sample_cv):
        from rest_framework.test import APIClient

        assert APIClient().post(reverse('cv-upload')).status_code in (401, 403)
