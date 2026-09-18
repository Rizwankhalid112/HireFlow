import logging
import os
from datetime import datetime, timedelta
from datetime import timezone as dt_timezone
from pathlib import Path

from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone

from celery import shared_task

from apps.cv_builder.models import CVProfile, CVUploadLog

logger = logging.getLogger(__name__)


@shared_task
def send_draft_reminder():
    now = timezone.now()
    window_start = now - timedelta(days=25)
    window_end = now - timedelta(days=23)

    profiles = CVProfile.objects.filter(
        is_complete=False,
        reminder_sent=False,
        content_updated_at__gte=window_start,
        content_updated_at__lte=window_end,
    ).select_related('user')

    for profile in profiles:
        send_mail(
            subject='Complete your HireFlow CV',
            message=(
                f'Hi {profile.full_name or profile.user.full_name},\n\n'
                'Your CV draft has been inactive for about 23 days. '
                'Complete it soon to avoid automatic deletion after 30 days.\n\n'
                f'{settings.FRONTEND_URL}/cv-builder'
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[profile.user.email],
            fail_silently=False,
        )
        profile.reminder_sent = True
        profile.save(update_fields=['reminder_sent'])


@shared_task
def delete_stale_drafts():
    cutoff = timezone.now() - timedelta(days=30)
    profiles = CVProfile.objects.filter(
        is_complete=False,
        content_updated_at__lt=cutoff,
    )

    for profile in profiles:
        if profile.pdf_file:
            try:
                profile.pdf_file.delete(save=False)
            except Exception as exc:
                logger.exception('Failed to delete PDF for CV %s: %s', profile.id, exc)
        profile.delete()


@shared_task
def delete_orphaned_files():
    """Delete upload files with no log row pointing at them.

    Dead code until Step 7 shipped; live now, which makes the age guard below
    load-bearing rather than theoretical.
    """
    uploads_dir = Path(settings.MEDIA_ROOT) / 'cv_uploads'
    if not uploads_dir.exists():
        return

    known_paths = set(
        CVUploadLog.objects.values_list('file_path', flat=True),
    )

    # The upload view writes the file and then creates the log row. Between
    # those two statements the file is legitimately orphaned, and a sweep
    # landing in that window would delete a file a request is about to use.
    # An hour is far longer than that gap and far shorter than the weekly
    # schedule, so it costs nothing.
    cutoff = timezone.now() - timedelta(hours=1)

    for root, _dirs, files in os.walk(uploads_dir):
        for filename in files:
            full_path = Path(root) / filename
            relative_path = str(full_path.relative_to(settings.MEDIA_ROOT))
            if relative_path in known_paths:
                continue
            try:
                modified = datetime.fromtimestamp(full_path.stat().st_mtime, tz=dt_timezone.utc)
                if modified > cutoff:
                    continue
                full_path.unlink()
            except OSError as exc:
                logger.exception('Failed to delete orphaned file %s: %s', full_path, exc)


# --- Upload pipeline (spec Steps 7-8) ---------------------------------------
#
# Two stages rather than one task, because they fail for unrelated reasons and
# `parse_status` should say which one broke: a corrupt PDF is the user's problem
# to fix, an upstream outage is ours.


def _fail(log, message):
    log.parse_status = CVUploadLog.ParseStatus.FAILED
    log.error_message = message
    log.save(update_fields=['parse_status', 'error_message'])


@shared_task
def extract_text_from_cv(log_id):
    """Stage 1: file to text. Chains to stage 2 only if there is text worth sending."""
    from apps.cv_builder.services.extraction import ExtractionError, extract_text

    try:
        log = CVUploadLog.objects.get(id=log_id)
    except CVUploadLog.DoesNotExist:
        # The profile was deleted while the task sat in the queue. Nothing to
        # do and nothing wrong — CASCADE already cleaned up.
        logger.info('Upload log %s vanished before extraction', log_id)
        return

    log.parse_status = CVUploadLog.ParseStatus.EXTRACTING
    log.save(update_fields=['parse_status'])

    full_path = Path(settings.MEDIA_ROOT) / log.file_path
    try:
        text = extract_text(str(full_path), log.file_type)
    except ExtractionError as exc:
        _fail(log, str(exc))
        return
    except Exception as exc:
        # A task that dies here leaves the row in `extracting` forever, which is
        # what fail_stuck_uploads exists for — but catching it means the user
        # gets an answer in seconds rather than in five minutes.
        logger.exception('Unexpected extraction failure for log %s: %s', log_id, exc)
        _fail(log, 'We could not read that file. Please try a different export.')
        return

    if len(text.strip()) < settings.CV_EXTRACT_MIN_CHARS:
        # A scanned image PDF, or a DOCX holding only pictures. Stopping here is
        # the point: sending an empty string to a metered API buys nothing.
        log.parse_status = CVUploadLog.ParseStatus.SCANNED
        log.error_message = (
            'This looks like a scanned image rather than a text document. '
            'Upload a text-based PDF, or fill your CV in manually.'
        )
        log.save(update_fields=['parse_status', 'error_message'])
        return

    log.raw_extracted_text = text
    log.extracted_at = timezone.now()
    log.save(update_fields=['raw_extracted_text', 'extracted_at'])

    send_to_ai_parser.delay(str(log.id))


@shared_task
def send_to_ai_parser(log_id):
    """Stage 2: text to structured data. Writes nothing to the CV itself."""
    from apps.cv_builder.services.ai import SuggestionUnavailable, parse_cv_text

    try:
        log = CVUploadLog.objects.get(id=log_id)
    except CVUploadLog.DoesNotExist:
        logger.info('Upload log %s vanished before parsing', log_id)
        return

    log.parse_status = CVUploadLog.ParseStatus.PARSING
    # Counted before the call, not after: a call that times out still cost
    # money, and a cap that only counts successes is not a cap.
    log.parse_attempts = (log.parse_attempts or 0) + 1
    log.save(update_fields=['parse_status', 'parse_attempts'])

    try:
        payload, usage, is_thin = parse_cv_text(log.raw_extracted_text)
    except SuggestionUnavailable as exc:
        _fail(log, str(exc))
        return
    except Exception as exc:
        logger.exception('Unexpected parse failure for log %s: %s', log_id, exc)
        _fail(log, 'Something went wrong reading your CV. Please try again.')
        return

    log.ai_parsed_json = payload
    log.fields_extracted = payload.get('fields_extracted', 0)
    log.fields_total = payload.get('fields_total', 0)
    log.parsed_at = timezone.now()
    # `partial` no longer means "some of the JSON validated" — structured
    # outputs make that unreachable. It means the file parsed but we found no
    # roles and no education, which is the honest signal for an odd layout.
    log.parse_status = (
        CVUploadLog.ParseStatus.PARTIAL if is_thin else CVUploadLog.ParseStatus.SUCCESS
    )
    log.error_message = (
        'We could not find any work experience or education in this file. '
        'Check it is the right document, or fill those sections in manually.'
        if is_thin else ''
    )
    log.save(update_fields=[
        'ai_parsed_json', 'fields_extracted', 'fields_total',
        'parsed_at', 'parse_status', 'error_message',
    ])

    logger.info(
        'Parsed CV upload %s: %d/%d fields, %d in / %d out tokens',
        log_id, log.fields_extracted, log.fields_total,
        usage.input_tokens, usage.output_tokens,
    )


@shared_task
def fail_stuck_uploads():
    """Move uploads whose worker died to a terminal status.

    Without this the frontend polls a row that will never change. `pending` is
    included deliberately — the spec only names `extracting`, but a worker that
    is down never picks the task up at all, which leaves the row in `pending`
    and is the more likely failure of the two.
    """
    cutoff = timezone.now() - timedelta(minutes=settings.CV_UPLOAD_STUCK_MINUTES)
    stuck = CVUploadLog.objects.filter(
        parse_status__in=[
            CVUploadLog.ParseStatus.PENDING,
            CVUploadLog.ParseStatus.EXTRACTING,
            CVUploadLog.ParseStatus.PARSING,
        ],
        uploaded_at__lt=cutoff,
    )

    count = stuck.update(
        parse_status=CVUploadLog.ParseStatus.FAILED,
        error_message='This import timed out. Please try uploading again.',
    )
    if count:
        logger.warning('Failed %d stuck CV upload(s)', count)
