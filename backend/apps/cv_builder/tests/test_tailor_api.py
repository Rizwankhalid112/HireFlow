"""The tailoring endpoints and the storage room.

The properties worth testing here are ownership, the master CV staying
untouched, and the PDF case degrading honestly rather than silently.
"""

import io

import pytest
from django.urls import reverse
from docx import Document

from apps.cv_builder.models import CVUploadLog, CVVersion, JobMatch

REWORDED = [
    {'keyword': 'PostgreSQL', 'current_wording': 'Postgres', 'where': 'Skills'},
    {'keyword': 'AWS', 'current_wording': 'Amazon Web Services', 'where': 'Experience'},
]

CV_TEXT = (
    'Backend engineer. Tuned Postgres queries for the reporting endpoint.\n'
    'Deployed to Amazon Web Services daily.\n'
)


def make_docx(text=CV_TEXT):
    document = Document()
    for line in text.splitlines():
        document.add_paragraph(line)
    out = io.BytesIO()
    document.save(out)
    return out.getvalue()


@pytest.fixture
def docx_upload(sample_cv):
    return CVUploadLog.objects.create(
        cv=sample_cv,
        original_filename='rizwan-cv.docx',
        file_type=CVUploadLog.FileType.DOCX,
        file_path='cv_uploads/1/rizwan-cv.docx',
        raw_extracted_text=CV_TEXT,
        file_blob=make_docx(),
    )


@pytest.fixture
def pdf_upload(sample_cv):
    return CVUploadLog.objects.create(
        cv=sample_cv,
        original_filename='rizwan-cv.pdf',
        file_type=CVUploadLog.FileType.PDF,
        file_path='cv_uploads/1/rizwan-cv.pdf',
        raw_extracted_text=CV_TEXT,
    )


def make_match(cv, upload=None, **kwargs):
    return JobMatch.objects.create(
        cv=cv,
        source_type=JobMatch.SourceType.UPLOAD if upload else JobMatch.SourceType.PROFILE,
        source_upload=upload,
        jd_text='We need PostgreSQL and AWS experience. ' * 8,
        job_title='Senior Backend Engineer',
        company='Acme Corp',
        match_score=65,
        reworded_keywords=REWORDED,
        cover_letter='Dear hiring manager,',
        **kwargs,
    )


@pytest.mark.django_db
class TestPreview:
    def test_it_reports_what_would_change_before_anything_does(self, api, sample_cv, docx_upload):
        match = make_match(sample_cv, docx_upload)

        body = api.get(reverse('cv-tailor-preview', args=[match.id])).json()

        assert {p['keyword'] for p in body['planned']} == {'PostgreSQL', 'AWS'}
        assert body['can_edit_file'] is True
        assert body['notice'] == ''

    def test_a_pdf_upload_says_plainly_that_it_cannot_be_edited(
        self, api, sample_cv, pdf_upload,
    ):
        match = make_match(sample_cv, pdf_upload)

        body = api.get(reverse('cv-tailor-preview', args=[match.id])).json()

        assert body['can_edit_file'] is False
        assert 'Word version' in body['notice']
        # The change list is still produced — it is the fallback, not a failure.
        assert len(body['planned']) == 2

    def test_another_users_match_is_not_visible(self, api, sample_cv, other_user):
        from apps.cv_builder.models import CVProfile
        theirs = make_match(CVProfile.objects.create(user=other_user, email=other_user.email))

        assert api.get(reverse('cv-tailor-preview', args=[theirs.id])).status_code == 404


@pytest.mark.django_db
class TestTailoring:
    def test_a_docx_is_edited_and_frozen_as_a_version(self, api, sample_cv, docx_upload):
        match = make_match(sample_cv, docx_upload)

        response = api.post(reverse('cv-tailor', args=[match.id]), {}, format='json')

        assert response.status_code == 201
        body = response.json()
        assert body['company'] == 'Acme Corp'
        assert body['change_count'] == 2
        assert body['file_name'].endswith('.docx')

        version = CVVersion.objects.get(id=body['id'])
        text = '\n'.join(p.text for p in Document(io.BytesIO(bytes(version.file_blob))).paragraphs)
        assert 'PostgreSQL' in text and 'Postgres ' not in text
        assert 'AWS' in text and 'Amazon Web Services' not in text

    def test_only_the_ticked_changes_are_applied(self, api, sample_cv, docx_upload):
        match = make_match(sample_cv, docx_upload)

        body = api.post(
            reverse('cv-tailor', args=[match.id]),
            {'accept': [{'keyword': 'PostgreSQL', 'current_wording': 'Postgres'}]},
            format='json',
        ).json()

        assert body['change_count'] == 1
        version = CVVersion.objects.get(id=body['id'])
        text = '\n'.join(p.text for p in Document(io.BytesIO(bytes(version.file_blob))).paragraphs)
        assert 'PostgreSQL' in text
        # Untouched, because the user did not tick it.
        assert 'Amazon Web Services' in text

    def test_a_rewrite_we_never_offered_is_ignored(self, api, sample_cv, docx_upload):
        """Otherwise a crafted request could rewrite arbitrary text in a CV."""
        match = make_match(sample_cv, docx_upload)

        response = api.post(
            reverse('cv-tailor', args=[match.id]),
            {'accept': [{'keyword': 'Rockstar', 'current_wording': 'Backend engineer'}]},
            format='json',
        )

        assert response.status_code == 400

    def test_the_master_cv_is_never_written_to(self, api, sample_cv, docx_upload):
        match = make_match(sample_cv, docx_upload)
        before = sample_cv.updated_at

        api.post(reverse('cv-tailor', args=[match.id]), {}, format='json')

        sample_cv.refresh_from_db()
        assert sample_cv.updated_at == before

    def test_a_built_cv_is_rendered_through_the_users_own_template(self, api, sample_cv):
        sample_cv.template_id = 'classic'
        sample_cv.save(update_fields=['template_id'])
        match = make_match(sample_cv)

        body = api.post(reverse('cv-tailor', args=[match.id]), {}, format='json').json()

        assert body['template_id'] == 'classic'
        assert body['file_name'].endswith('.pdf')
        version = CVVersion.objects.get(id=body['id'])
        assert bytes(version.file_blob).startswith(b'%PDF')

    def test_a_pdf_upload_produces_a_change_list_and_no_file(
        self, api, sample_cv, pdf_upload,
    ):
        match = make_match(sample_cv, pdf_upload)

        body = api.post(reverse('cv-tailor', args=[match.id]), {}, format='json').json()

        assert body['change_count'] == 0
        assert body['has_file'] is False
        assert all('Word version' in s['reason'] for s in body['skipped_rewrites'])


@pytest.mark.django_db
class TestStorageRoom:
    def test_it_lists_tailored_cvs_by_company(self, api, sample_cv, docx_upload):
        match = make_match(sample_cv, docx_upload)
        api.post(reverse('cv-tailor', args=[match.id]), {}, format='json')

        body = api.get(reverse('cv-versions')).json()

        assert len(body['versions']) == 1
        assert body['versions'][0]['company'] == 'Acme Corp'
        assert body['versions'][0]['change_count'] == 2

    def test_the_job_description_comes_back_with_the_cv(self, api, sample_cv, docx_upload):
        """The reason to open this months later is to revise for the interview."""
        match = make_match(sample_cv, docx_upload)
        version_id = api.post(reverse('cv-tailor', args=[match.id]), {}, format='json').json()['id']

        body = api.get(reverse('cv-version-detail', args=[version_id])).json()

        assert 'PostgreSQL and AWS' in body['jd_text']
        assert body['cover_letter'].startswith('Dear')

    def test_the_file_downloads_with_the_company_in_its_name(
        self, api, sample_cv, docx_upload,
    ):
        match = make_match(sample_cv, docx_upload)
        version_id = api.post(reverse('cv-tailor', args=[match.id]), {}, format='json').json()['id']

        response = api.get(reverse('cv-version-download', args=[version_id]))

        assert response.status_code == 200
        assert 'Acme-Corp' in response['Content-Disposition']
        assert response.content[:2] == b'PK'  # a DOCX is a zip

    def test_an_expired_cv_is_gone_even_before_the_purge_runs(
        self, api, sample_cv, docx_upload,
    ):
        from datetime import timedelta
        from django.utils import timezone

        match = make_match(sample_cv, docx_upload)
        version_id = api.post(reverse('cv-tailor', args=[match.id]), {}, format='json').json()['id']
        CVVersion.objects.filter(id=version_id).update(
            expires_at=timezone.now() - timedelta(days=1),
        )

        assert api.get(reverse('cv-versions')).json()['versions'] == []
        assert api.get(reverse('cv-version-detail', args=[version_id])).status_code == 404

    def test_another_users_tailored_cv_is_not_reachable(
        self, api, sample_cv, docx_upload, other_user,
    ):
        from apps.cv_builder.models import CVProfile
        theirs = CVVersion.objects.create(
            cv=CVProfile.objects.create(user=other_user, email=other_user.email),
            company='Not Yours',
        )

        assert api.get(reverse('cv-version-detail', args=[theirs.id])).status_code == 404
        assert api.get(reverse('cv-version-download', args=[theirs.id])).status_code == 404

    def test_deleting_removes_it(self, api, sample_cv, docx_upload):
        match = make_match(sample_cv, docx_upload)
        version_id = api.post(reverse('cv-tailor', args=[match.id]), {}, format='json').json()['id']

        assert api.delete(reverse('cv-version-detail', args=[version_id])).status_code == 204
        assert api.get(reverse('cv-versions')).json()['versions'] == []
