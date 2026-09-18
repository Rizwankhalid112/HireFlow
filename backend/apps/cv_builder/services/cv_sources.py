"""Which CV are we matching against?

Users have more than one in practice — the one they maintain in the builder, and
whatever they have uploaded — so "score my CV" is ambiguous and the choice has to
be explicit. This resolves that choice to plain text.

There is no `CVVersion` model yet (the decision is still owed — see
docs/job_match_rnd.md §6), so "their CVs" today means the built one plus the text
we already extracted from anything they uploaded. That is enough for this module
and does not prejudge the shape of the fix.
"""

from apps.cv_builder.models import CVUploadLog
from apps.cv_builder.services.ai.context import build_full_cv_text

PROFILE = 'profile'
UPLOAD = 'upload'


def list_sources(profile):
    """Everything this user could match against, newest upload first."""
    sources = [{
        'type': PROFILE,
        'id': None,
        'label': 'My HireFlow CV',
        'detail': f'{profile.completion_score}% complete',
        'created_at': profile.updated_at,
    }]

    uploads = CVUploadLog.objects.filter(
        cv=profile,
    ).exclude(raw_extracted_text='').order_by('-uploaded_at')[:10]

    for upload in uploads:
        sources.append({
            'type': UPLOAD,
            'id': str(upload.id),
            'label': upload.original_filename,
            'detail': f'Uploaded {upload.uploaded_at:%d %b %Y}',
            'created_at': upload.uploaded_at,
        })

    return sources


def resolve_cv_text(profile, source_type, upload_id=None):
    """`(text, upload_log_or_None)`. Raises ValueError on a bad choice.

    The upload is re-fetched scoped to this profile rather than trusted from the
    request, so an id belonging to someone else resolves to nothing rather than
    to their CV.
    """
    if source_type == UPLOAD:
        if not upload_id:
            raise ValueError('Choose which uploaded CV to use.')
        upload = CVUploadLog.objects.filter(id=upload_id, cv=profile).first()
        if upload is None:
            raise ValueError('That uploaded CV could not be found.')
        if not upload.raw_extracted_text:
            raise ValueError('We could not read any text from that upload.')
        return upload.raw_extracted_text, upload

    return build_full_cv_text(profile), None
