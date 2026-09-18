from django.conf import settings

REFRESH_COOKIE_NAME = 'refresh_token'
REFRESH_COOKIE_MAX_AGE = 7 * 24 * 60 * 60


def set_refresh_cookie(response, refresh_token):
    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=str(refresh_token),
        httponly=True,
        secure=not settings.DEBUG,
        samesite='Lax',
        max_age=REFRESH_COOKIE_MAX_AGE,
    )


def clear_refresh_cookie(response):
    response.delete_cookie(
        key=REFRESH_COOKIE_NAME,
        samesite='Lax',
    )


def get_refresh_token_from_cookie(request):
    return request.COOKIES.get(REFRESH_COOKIE_NAME)
