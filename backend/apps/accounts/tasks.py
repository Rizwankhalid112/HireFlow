from django.conf import settings
from django.core.mail import send_mail
from django.core.signing import dumps

from celery import shared_task

from apps.accounts.models import User

VERIFY_SALT = 'email-verify'
RESET_SALT = 'password-reset'


@shared_task
def send_verification_email(user_id):
    user = User.objects.get(id=user_id)
    token = dumps({'user_id': str(user.id)}, salt=VERIFY_SALT)
    verification_url = f'{settings.FRONTEND_URL}/verify-email/{token}'

    send_mail(
        subject='Verify your HireFlow account',
        message=(
            f'Hi {user.full_name},\n\n'
            f'Please verify your email by visiting:\n{verification_url}\n\n'
            f'This link expires in 24 hours.'
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        fail_silently=False,
    )


@shared_task
def send_password_reset_email(user_id):
    user = User.objects.get(id=user_id)
    token = dumps({'user_id': str(user.id)}, salt=RESET_SALT)
    reset_url = f'{settings.FRONTEND_URL}/reset-password/{token}'

    send_mail(
        subject='Reset your HireFlow password',
        message=(
            f'Hi {user.full_name},\n\n'
            f'Reset your password by visiting:\n{reset_url}\n\n'
            f'This link expires in 1 hour.'
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        fail_silently=False,
    )
