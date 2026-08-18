import logging
import os
from datetime import timedelta
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
    uploads_dir = Path(settings.MEDIA_ROOT) / 'cv_uploads'
    if not uploads_dir.exists():
        return

    known_paths = set(
        CVUploadLog.objects.values_list('file_path', flat=True),
    )

    for root, _dirs, files in os.walk(uploads_dir):
        for filename in files:
            full_path = Path(root) / filename
            relative_path = str(full_path.relative_to(settings.MEDIA_ROOT))
            if relative_path not in known_paths:
                try:
                    full_path.unlink()
                except OSError as exc:
                    logger.exception('Failed to delete orphaned file %s: %s', full_path, exc)
