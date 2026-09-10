from datetime import timedelta
from pathlib import Path

from decouple import config

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = config('SECRET_KEY')
DEBUG = config('DEBUG', default=False, cast=bool)
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost,127.0.0.1').split(',')

DJANGO_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',
]

THIRD_PARTY_APPS = [
    'rest_framework',
    'rest_framework_simplejwt',
    'rest_framework_simplejwt.token_blacklist',
    'corsheaders',
    'django_celery_beat',
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'allauth.socialaccount.providers.google',
    'allauth.socialaccount.providers.github',
]

LOCAL_APPS = [
    'apps.accounts',
    'apps.cv_builder',
    'apps.analytics',
    'apps.reports',
    'apps.settings_app',
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'allauth.account.middleware.AccountMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': config('DB_NAME'),
        'USER': config('DB_USER'),
        'PASSWORD': config('DB_PASSWORD'),
        'HOST': config('DB_HOST', default='db'),
        'PORT': config('DB_PORT', default='5432'),
    }
}

AUTH_USER_MODEL = 'accounts.User'

AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
    'allauth.account.auth_backends.AuthenticationBackend',
]

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

SITE_ID = 1

REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ],
    # Only the AI suggestion endpoints are throttled today. They call a metered
    # API, so an unthrottled endpoint is uncapped billing exposure — this is a
    # cost control, not an abuse control.
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.ScopedRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'ai_suggest': config('AI_SUGGEST_THROTTLE', default='20/min'),
        # An upload does not call Claude itself -- it queues a task that does.
        # Same exposure one step removed, so it gets its own, tighter scope: a
        # parse costs several times a suggestion and nobody uploads their CV
        # five times an hour legitimately.
        'cv_upload': config('CV_UPLOAD_THROTTLE', default='5/hour'),
        # The most expensive call in the product: a whole CV and a whole job
        # description in, a cover letter out. Tighter than suggestions by an
        # order of magnitude, because one run costs roughly that much more.
        'job_match': config('JOB_MATCH_THROTTLE', default='10/hour'),
    },
}

# --- AI writing suggestions -------------------------------------------------
# The key is read from the environment and never checked in. If it is absent the
# suggestion endpoints return 503 with a clear message; nothing else degrades.
ANTHROPIC_API_KEY = config('ANTHROPIC_API_KEY', default='')

# Opus 5. Suggestions are short-form generation, so effort stays low — the
# quality ceiling here is set by the guardrails, not by thinking depth.
AI_MODEL = config('AI_MODEL', default='claude-opus-5')
AI_EFFORT = config('AI_EFFORT', default='low')
AI_TIMEOUT_SECONDS = config('AI_TIMEOUT_SECONDS', default=30, cast=int)

# Monthly per-user allowance. ~1 cent per suggestion, so 60 lands near the
# market's free tier (Teal ships 10 bullet + 2 summary credits).
AI_MONTHLY_CREDITS = config('AI_MONTHLY_CREDITS', default=60, cast=int)

# --- CV upload and AI parse (spec Steps 7-8) --------------------------------
# A whole-CV parse is a much larger call than a suggestion: a two-page CV plus a
# full structured response runs several times the cost, so it is metered
# separately and far more tightly. Counted from CVUploadLog rows, never
# decremented -- a drifting counter is unrecoverable, a count is recomputable.
AI_PARSE_MONTHLY_LIMIT = config('AI_PARSE_MONTHLY_LIMIT', default=5, cast=int)

# The suggestion ceiling (2000) is sized for three short variants. A full CV --
# several roles with bullets, education, skills, projects -- runs past it, and a
# truncated structured output arrives as parsed_output=None with nothing saying
# why. This is a correctness bound, not a tuning knob.
AI_PARSE_MAX_TOKENS = config('AI_PARSE_MAX_TOKENS', default=8000, cast=int)

# Extraction bounds. A CV is never 40 pages; an unbounded input is an unbounded
# bill, and the cap is hit long before any real CV is truncated.
CV_UPLOAD_MAX_BYTES = config('CV_UPLOAD_MAX_BYTES', default=5 * 1024 * 1024, cast=int)
CV_EXTRACT_MAX_PAGES = config('CV_EXTRACT_MAX_PAGES', default=30, cast=int)
CV_EXTRACT_MAX_CHARS = config('CV_EXTRACT_MAX_CHARS', default=60_000, cast=int)

# Below this, the file carried no usable text: a scanned image PDF, or a DOCX
# holding only pictures. Detected before any API call is spent.
CV_EXTRACT_MIN_CHARS = config('CV_EXTRACT_MIN_CHARS', default=100, cast=int)

# A non-terminal upload older than this had its worker die under it.
CV_UPLOAD_STUCK_MINUTES = config('CV_UPLOAD_STUCK_MINUTES', default=5, cast=int)

# Set explicitly rather than left to the 2.5MB default, so that where an upload
# spills to a temp file is a decision rather than an accident.
FILE_UPLOAD_MAX_MEMORY_SIZE = 2 * 1024 * 1024

# --- Job match (Module 1) ---------------------------------------------------
# Its own allowance rather than sharing AI_MONTHLY_CREDITS: a job match sends two
# whole documents and returns a cover letter, so one run is worth many
# suggestions and mixing them would let a few matches eat a month of writing help.
AI_JOB_MATCH_MONTHLY_LIMIT = config('AI_JOB_MATCH_MONTHLY_LIMIT', default=20, cast=int)

# Keyword lists plus a full cover letter. Past this the structured output is cut
# off mid-object and arrives as nothing at all.
AI_JOB_MATCH_MAX_TOKENS = config('AI_JOB_MATCH_MAX_TOKENS', default=6000, cast=int)

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=15),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
}

CORS_ALLOWED_ORIGINS = config(
    'CORS_ALLOWED_ORIGINS',
    default='http://localhost,http://localhost:5173,http://127.0.0.1:5173',
).split(',')
CORS_ALLOW_CREDENTIALS = True

USE_X_FORWARDED_HOST = True
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

FRONTEND_URL = config('FRONTEND_URL', default='http://localhost:5173')

EMAIL_BACKEND = config(
    'EMAIL_BACKEND',
    default='django.core.mail.backends.console.EmailBackend',
)
EMAIL_HOST = config('EMAIL_HOST', default='smtp.gmail.com')
EMAIL_PORT = config('EMAIL_PORT', default=587, cast=int)
EMAIL_USE_TLS = config('EMAIL_USE_TLS', default=True, cast=bool)
EMAIL_HOST_USER = config('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')
DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL', default='noreply@hireflow.com')

# Without this, django.core.cache falls back to per-process LocMemCache, so the
# rendered-PDF cache would miss on every other gunicorn worker (and the
# canonical-skill cache would never invalidate).
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        # Deliberately db 2 — db 0 is the Celery broker, db 1 the result backend.
        'LOCATION': config('CACHE_URL', default='redis://redis:6379/2'),
    }
}

CELERY_BROKER_URL = config('CELERY_BROKER_URL', default='redis://redis:6379/0')
CELERY_RESULT_BACKEND = config('CELERY_RESULT_BACKEND', default='redis://redis:6379/1')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE

ACCOUNT_EMAIL_VERIFICATION = 'none'
ACCOUNT_AUTHENTICATION_METHOD = 'email'
ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_USERNAME_REQUIRED = False
