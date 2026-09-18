import requests
from allauth.socialaccount.models import SocialAccount
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.cookies import set_refresh_cookie
from apps.accounts.errors import AuthMessages

User = get_user_model()

GOOGLE_USERINFO_URL = 'https://www.googleapis.com/oauth2/v3/userinfo'
GITHUB_USER_URL = 'https://api.github.com/user'
GITHUB_EMAILS_URL = 'https://api.github.com/user/emails'


def _issue_token_response(user):
    refresh = RefreshToken.for_user(user)
    response = Response(
        {'access': str(refresh.access_token)},
        status=status.HTTP_200_OK,
    )
    set_refresh_cookie(response, refresh)
    return response


def _get_or_create_social_user(provider, uid, email, full_name):
    social_account = SocialAccount.objects.filter(
        provider=provider,
        uid=uid,
    ).select_related('user').first()

    if social_account:
        return social_account.user

    user = User.objects.filter(email__iexact=email).first()
    if not user:
        user = User.objects.create_user(
            email=email,
            full_name=full_name,
            password=None,
            auth_provider=provider,
            is_email_verified=True,
        )

    SocialAccount.objects.get_or_create(
        provider=provider,
        uid=uid,
        defaults={'user': user, 'extra_data': {'email': email}},
    )
    return user


def _fetch_google_profile(access_token):
    response = requests.get(
        GOOGLE_USERINFO_URL,
        headers={'Authorization': f'Bearer {access_token}'},
        timeout=10,
    )
    response.raise_for_status()
    return response.json()


def _fetch_github_profile(access_token):
    headers = {'Authorization': f'Bearer {access_token}', 'Accept': 'application/json'}
    user_response = requests.get(GITHUB_USER_URL, headers=headers, timeout=10)
    user_response.raise_for_status()
    profile = user_response.json()

    email = profile.get('email')
    if not email:
        emails_response = requests.get(GITHUB_EMAILS_URL, headers=headers, timeout=10)
        emails_response.raise_for_status()
        for entry in emails_response.json():
            if entry.get('primary') and entry.get('verified'):
                email = entry.get('email')
                break

    if not email:
        raise ValueError(AuthMessages.GITHUB_EMAIL_UNAVAILABLE)

    profile['email'] = email
    return profile


def perform_google_login(request):
    access_token = request.data.get('access_token')
    if not access_token:
        return Response(
            {'detail': AuthMessages.ACCESS_TOKEN_REQUIRED},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        profile = _fetch_google_profile(access_token)
        user = _get_or_create_social_user(
            provider=User.AuthProvider.GOOGLE,
            uid=profile['sub'],
            email=profile['email'],
            full_name=profile.get('name') or profile['email'].split('@')[0],
        )
    except (requests.RequestException, KeyError, ValueError) as exc:
        return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)

    return _issue_token_response(user)


def perform_github_login(request):
    access_token = request.data.get('access_token')
    if not access_token:
        return Response(
            {'detail': AuthMessages.ACCESS_TOKEN_REQUIRED},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        profile = _fetch_github_profile(access_token)
        user = _get_or_create_social_user(
            provider=User.AuthProvider.GITHUB,
            uid=str(profile['id']),
            email=profile['email'],
            full_name=profile.get('name') or profile['login'],
        )
    except (requests.RequestException, KeyError, ValueError) as exc:
        return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)

    return _issue_token_response(user)
