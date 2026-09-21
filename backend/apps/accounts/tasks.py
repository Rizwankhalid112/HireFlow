"""Transactional mail.

Both of these decide whether somebody can use their account at all, so a
failure is logged loudly rather than swallowed. Without a Celery worker these
run inline during the request (`CELERY_TASK_ALWAYS_EAGER`), and eager mode does
not propagate exceptions — so the log line below is the *only* evidence that a
send failed. A blocked outbound port, a wrong app password and a provider
outage all look identical from the outside otherwise: registration returns 201
and no mail arrives.
"""

import logging

from django.conf import settings
from django.core.mail import send_mail
from django.core.signing import dumps

from celery import shared_task

from apps.accounts.models import User

logger = logging.getLogger(__name__)

VERIFY_SALT = 'email-verify'
RESET_SALT = 'password-reset'


def _deliver(subject, body, recipient):
    """Send, and make the outcome visible either way.

    `fail_silently=False` on purpose: the exception carries the reason, and the
    reason is the whole diagnostic. A connection timeout means the host blocks
    outbound SMTP; an authentication error means the credentials are wrong.
    """
    try:
        send_mail(
            subject=subject,
            message=body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[recipient],
            fail_silently=False,
        )
    except Exception:
        logger.exception(
            'EMAIL FAILED: %r to %s via %s. The recipient cannot continue '
            'without this message.',
            subject, recipient, settings.EMAIL_HOST,
        )
        raise

    logger.info('Sent %r to %s', subject, recipient)


@shared_task
def send_verification_email(user_id):
    user = User.objects.get(id=user_id)
    token = dumps({'user_id': str(user.id)}, salt=VERIFY_SALT)
    verification_url = f'{settings.FRONTEND_URL}/verify-email/{token}'

    _deliver(
        'Verify your HireFlow account',
        (
            f'Hi {user.full_name},\n\n'
            f'Please verify your email by visiting:\n{verification_url}\n\n'
            f'This link expires in 24 hours.'
        ),
        user.email,
    )


@shared_task
def send_password_reset_email(user_id):
    user = User.objects.get(id=user_id)
    token = dumps({'user_id': str(user.id)}, salt=RESET_SALT)
    reset_url = f'{settings.FRONTEND_URL}/reset-password/{token}'

    _deliver(
        'Reset your HireFlow password',
        (
            f'Hi {user.full_name},\n\n'
            f'Reset your password by visiting:\n{reset_url}\n\n'
            f'This link expires in 1 hour.'
        ),
        user.email,
    )
