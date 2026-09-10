"""CV file upload, status polling and retry.

The upload request itself does no work beyond validating and saving: it hands
off to Celery and returns immediately, so the response time is independent of
how long extraction and parsing take.

Nothing here writes parsed data to the CV. That happens only on an explicit
apply (see `views/apply.py`), which is what makes overwrite protection real
rather than a promise.
"""

import logging

from django.conf import settings
from django.core.files.storage import default_storage
from django.shortcuts import get_object_or_404
from django.utils import timezone

from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.cv_builder.models import CVUploadLog, parses_used_this_period
from apps.cv_builder.serializers.upload import CVUploadSerializer
from apps.cv_builder.utils import get_user_cv_profile

logger = logging.getLogger(__name__)

CAP_REACHED_MESSAGE = (
    'You have used all your CV imports for this month. They reset on the 1st.'
)


def _cap_response(used):
    return Response(
        {
            'detail': CAP_REACHED_MESSAGE,
            'parses': {'used': used, 'limit': settings.AI_PARSE_MONTHLY_LIMIT},
        },
        status=status.HTTP_429_TOO_MANY_REQUESTS,
    )


class CVUploadView(APIView):
    """POST a PDF or DOCX. Returns 202 with a log id to poll."""

    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]
    # An upload does not call Claude itself, it queues a task that does — the
    # same billing exposure one step removed, so it is throttled like one.
    throttle_scope = 'cv_upload'

    def post(self, request):
        profile = get_user_cv_profile(request.user)

        # Checked before the file is written, so a capped user does not leave a
        # file on disk for the orphan sweeper to collect later.
        used = parses_used_this_period(profile)
        if used >= settings.AI_PARSE_MONTHLY_LIMIT:
            return Response(
                {
                    'detail': CAP_REACHED_MESSAGE,
                    'parses': {'used': used, 'limit': settings.AI_PARSE_MONTHLY_LIMIT},
                },
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        serializer = CVUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        uploaded = serializer.validated_data['file']
        safe_name = serializer.safe_filename()
        stamp = timezone.now().strftime('%Y%m%d%H%M%S')
        # The user id in the path is what keeps one user's uploads out of
        # another's directory even if the filename sanitiser were ever wrong.
        relative_path = f'cv_uploads/{request.user.id}/{stamp}_{safe_name}'

        stored_path = default_storage.save(relative_path, uploaded)

        # Django's multipart parser raises on a truncated body, so a short file
        # here means something stranger — a full disk, a storage backend that
        # silently dropped bytes. Either way the file is unusable, and leaving
        # it would feed a corrupt file to the extractor.
        written = default_storage.size(stored_path)
        if written != uploaded.size:
            default_storage.delete(stored_path)
            logger.error(
                'Upload size mismatch for user %s: expected %d, wrote %d',
                request.user.id, uploaded.size, written,
            )
            return Response(
                {'detail': 'Upload incomplete — please try again.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        log = CVUploadLog.objects.create(
            cv=profile,
            original_filename=(uploaded.name or safe_name)[:300],
            file_type=serializer.detected_type,
            file_path=stored_path,
        )

        # Imported here rather than at module load: tasks.py imports models, and
        # a top-level import in both directions is a cycle waiting to happen.
        from apps.cv_builder.tasks import extract_text_from_cv

        extract_text_from_cv.delay(str(log.id))

        return Response(
            {'log_id': str(log.id), 'status': log.parse_status},
            status=status.HTTP_202_ACCEPTED,
        )


class CVUploadStatusView(APIView):
    """Polled every 2s by the frontend until the status is terminal."""

    permission_classes = [IsAuthenticated]

    def get(self, request, log_id):
        profile = get_user_cv_profile(request.user)
        log = get_object_or_404(CVUploadLog, id=log_id, cv=profile)

        payload = {
            'log_id': str(log.id),
            'status': log.parse_status,
            'fields_extracted': log.fields_extracted,
            'fields_total': log.fields_total,
            'error_message': log.error_message or None,
            'is_terminal': log.is_terminal,
        }

        if log.parse_status in (CVUploadLog.ParseStatus.SUCCESS, CVUploadLog.ParseStatus.PARTIAL):
            # Derived per request, never stored: the user can delete their
            # experience in another tab between the parse finishing and this
            # call, and a stored flag would then be wrong. See the plan, §3.3.
            payload['requires_review'] = _has_existing_content(profile)
            payload['parsed_data'] = log.ai_parsed_json or {}
            payload['existing_data'] = (
                _existing_summary(profile) if payload['requires_review'] else {}
            )

        return Response(payload)


class CVUploadRetryView(APIView):
    """Re-run the AI stage on text we already extracted.

    Exists because the most common failure is upstream and transient, and making
    the user re-upload a file we still have on disk to recover from it would be
    gratuitous. It is a real metered call, so it counts against the cap.
    """

    permission_classes = [IsAuthenticated]
    throttle_scope = 'cv_upload'

    def post(self, request, log_id):
        profile = get_user_cv_profile(request.user)
        log = get_object_or_404(CVUploadLog, id=log_id, cv=profile)

        if not log.raw_extracted_text:
            return Response(
                {'detail': 'There is no extracted text to parse. Upload the file again.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if log.parse_status not in (
            CVUploadLog.ParseStatus.FAILED,
            CVUploadLog.ParseStatus.PARTIAL,
        ):
            return Response(
                {'detail': 'This import is not in a state that can be retried.'},
                status=status.HTTP_409_CONFLICT,
            )

        used = parses_used_this_period(profile)
        if used >= settings.AI_PARSE_MONTHLY_LIMIT:
            return _cap_response(used)

        from apps.cv_builder.tasks import send_to_ai_parser

        log.parse_status = CVUploadLog.ParseStatus.PARSING
        log.error_message = ''
        log.save(update_fields=['parse_status', 'error_message'])

        send_to_ai_parser.delay(str(log.id))

        return Response(
            {'log_id': str(log.id), 'status': log.parse_status},
            status=status.HTTP_202_ACCEPTED,
        )


def _has_existing_content(profile):
    """Whether importing could overwrite something the user already has.

    Deliberately the three sections the spec names. Contact details are excluded:
    they are pre-filled from the account at profile creation, so their presence
    says nothing about whether the user has done any work.
    """
    return (
        profile.work_experiences.exists()
        or profile.education_entries.exists()
        or profile.skills.exists()
    )


def _existing_summary(profile):
    """A compact view of what is already on the CV, for the diff UI.

    Counts and labels rather than full rows — the modal shows "3 roles, oldest
    Acme Corp", not a second copy of the CV.
    """
    return {
        'personal': {
            'full_name': profile.full_name,
            'professional_title': profile.professional_title,
            'email': profile.email,
            'phone': profile.phone,
            'has_summary': bool(profile.summary),
        },
        'work_experience': {
            'count': profile.work_experiences.count(),
            'labels': [
                f'{e.role_title} at {e.company_name}'
                for e in profile.work_experiences.all()[:5]
            ],
        },
        'education': {
            'count': profile.education_entries.count(),
            'labels': [e.institution for e in profile.education_entries.all()[:5]],
        },
        'skills': {
            'count': profile.skills.count(),
            'labels': [s.name for s in profile.skills.all()[:15]],
        },
        'projects': {
            'count': profile.projects.count(),
            'labels': [p.name for p in profile.projects.all()[:5]],
        },
        'certifications': {'count': profile.certifications.count()},
        'languages': {'count': profile.languages.count()},
    }


class CVUploadApplyView(APIView):
    """Write a reviewed import onto the CV.

    The second half of the overwrite protection: the parse produced data and
    stopped, and nothing reaches the CV until this is called with an explicit
    per-section choice.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, log_id):
        from apps.cv_builder.services.apply_parsed import (
            VALID_CHOICES,
            apply_parsed_cv,
        )

        profile = get_user_cv_profile(request.user)
        log = get_object_or_404(CVUploadLog, id=log_id, cv=profile)

        if log.parse_status not in (
            CVUploadLog.ParseStatus.SUCCESS,
            CVUploadLog.ParseStatus.PARTIAL,
        ):
            return Response(
                {'detail': 'This import has no data to apply.'},
                status=status.HTTP_409_CONFLICT,
            )

        if log.applied_at is not None:
            # Apply is destructive under `replace`, so a double-submitted form
            # would wipe the rows the first submit had just created.
            return Response(
                {'detail': 'This import has already been applied.'},
                status=status.HTTP_409_CONFLICT,
            )

        choices = request.data.get('choices') or {}
        if not isinstance(choices, dict):
            return Response(
                {'detail': 'choices must be an object.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        invalid = {
            section: value
            for section, value in choices.items()
            if value not in VALID_CHOICES
        }
        if invalid:
            return Response(
                {'detail': f'Invalid choice for: {", ".join(sorted(invalid))}.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        answers = request.data.get('answers') or {}
        if not isinstance(answers, dict):
            return Response(
                {'detail': 'answers must be an object.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        result = apply_parsed_cv(profile, log.ai_parsed_json or {}, choices, answers)

        log.applied_at = timezone.now()
        log.save(update_fields=['applied_at'])

        payload = result.as_dict()
        payload['notes'] = (log.ai_parsed_json or {}).get('notes', [])
        return Response(payload)
