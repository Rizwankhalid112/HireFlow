import re
from datetime import timedelta
from pathlib import Path

import dj_database_url
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
    'apps.jobs',
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

# Managed platforms hand out a single DATABASE_URL; Docker Compose sets the
# five DB_* vars. Accept either, so the same image runs in both places.
#
# CONN_MAX_AGE is not cosmetic on hosted Postgres: connecting costs real
# latency per request, and reusing the connection removes it from every call.
_DATABASE_URL = config('DATABASE_URL', default='')

if _DATABASE_URL:
    DATABASES = {
        'default': dj_database_url.parse(
            _DATABASE_URL,
            conn_max_age=config('CONN_MAX_AGE', default=600, cast=int),
            ssl_require=config('DB_SSL_REQUIRE', default=not DEBUG, cast=bool),
        )
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': config('DB_NAME'),
            'USER': config('DB_USER'),
            'PASSWORD': config('DB_PASSWORD'),
            'HOST': config('DB_HOST', default='db'),
            'PORT': config('DB_PORT', default='5432'),
            'CONN_MAX_AGE': config('CONN_MAX_AGE', default=600, cast=int),
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

# Option A (single service): the React build is copied into the image and
# served by WhiteNoise at the root, so /assets/*.js and /favicon.svg resolve
# without nginx. `config.views.spa` then answers every non-API path with
# index.html. When the directory is absent — local Compose, where the Vite dev
# server owns the frontend — none of this engages.
_VITE_ASSET = re.compile(r'^/assets/.+-[A-Za-z0-9_-]{8,}\.[a-z0-9]+$')


def _is_hashed_asset(path, url):
    """True for Vite's content-hashed output, which is safe to cache forever."""
    return _VITE_ASSET.match(url) is not None


FRONTEND_DIST = BASE_DIR / 'frontend_dist'
SERVE_SPA = FRONTEND_DIST.is_dir()

if SERVE_SPA:
    WHITENOISE_ROOT = FRONTEND_DIST
    # index.html must never be cached, or a deploy leaves browsers loading
    # asset filenames that no longer exist.
    WHITENOISE_INDEX_FILE = False

    # WhiteNoise only caches aggressively for files it *knows* are
    # content-hashed, which it learns from Django's staticfiles manifest —
    # and Vite's output is not in that manifest. Without this it falls back to
    # 60 seconds, so a returning visitor re-downloads the whole bundle roughly
    # every minute. Vite emits assets/<name>-<hash>.<ext>, which is safe to
    # pin for a year: a new build is a new filename.
    WHITENOISE_IMMUTABLE_FILE_TEST = _is_hashed_asset

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

# --- Job ingestion (Module 2) -----------------------------------------------
# We identify ourselves honestly to the boards we read. No platform we tested
# publishes a rate limit, but undocumented is not the same as absent, so a pause
# between requests stays in the design.
JOBS_USER_AGENT = config(
    'JOBS_USER_AGENT',
    default='HireFlow/1.0 (job aggregator; +https://hireflow.com)',
)
JOBS_FETCH_TIMEOUT = config('JOBS_FETCH_TIMEOUT', default=45, cast=int)
JOBS_FETCH_PAUSE = config('JOBS_FETCH_PAUSE', default=1.0, cast=float)
# Lever runs 5-20s per company while the others are ~1s, so a serial run would
# be dominated by it. Modest concurrency, since these are someone else's servers.
JOBS_FETCH_WORKERS = config('JOBS_FETCH_WORKERS', default=4, cast=int)
# Counted from when we last SAW a job in the feed, never from its posting date:
# live listings exist that were published in 2009.
JOBS_RETENTION_DAYS = config('JOBS_RETENTION_DAYS', default=45, cast=int)

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

# Django 5 rejects an admin POST whose Origin is not listed here, so without
# this the admin login form fails on any HTTPS deploy — with a CSRF error that
# does not mention the setting.
CSRF_TRUSTED_ORIGINS = [
    origin for origin in config('CSRF_TRUSTED_ORIGINS', default='').split(',') if origin
]

if not DEBUG:
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = config('SECURE_HSTS_SECONDS', default=31536000, cast=int)
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True

FRONTEND_URL = config('FRONTEND_URL', default='http://localhost:5173')

# The console backend prints mail to stdout instead of sending it. That is
# right for local work and actively harmful in a deployment: no user can ever
# complete registration, and every verification link — each one a working
# account-takeover token — is written in clear text to the platform's logs,
# readable by anyone who can open the dashboard.
#
# Set EMAIL_BACKEND to the SMTP backend and the four EMAIL_HOST_* values to fix
# it; see .env.example. The warning below exists because this failure is
# completely silent: registration returns 201 either way.
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


# Logging. There was none, which on a hosted deploy means the only evidence of
# anything going wrong is whatever happens to reach stderr by accident — and an
# email that failed to send reached nothing at all.
#
# Deliberately plain: one console handler, because every platform worth using
# collects stdout. No files, no rotation, nothing to configure per host.
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'standard': {
            'format': '[{levelname}] {name}: {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'standard',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'WARNING',
    },
    'loggers': {
        # Our own code at INFO: these are the lines that say a gather ran or an
        # email went out, and they are worth having in a deploy log.
        'apps': {
            'handlers': ['console'],
            'level': config('LOG_LEVEL', default='INFO'),
            'propagate': False,
        },
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        # Every 404 for a missing favicon is not worth a log line.
        'django.request': {
            'handlers': ['console'],
            'level': 'WARNING',
            'propagate': False,
        },
    },
}

if not DEBUG and 'console' in EMAIL_BACKEND:
    import warnings

    warnings.warn(
        'EMAIL_BACKEND is the console backend while DEBUG is off. No mail will '
        'be sent: verification and password-reset links will only appear in the '
        'server log, so nobody can finish registering and those links are '
        'exposed to anyone who can read it. Configure SMTP — see .env.example.',
        RuntimeWarning,
    )

# Without this, django.core.cache falls back to per-process LocMemCache, so the
# rendered-PDF cache would miss on every other gunicorn worker (and the
# canonical-skill cache would never invalidate).
# The default is the shape that works with nothing configured. `redis:6379` is
# a Compose hostname and resolves nowhere else, so defaulting to it meant a
# deploy that forgot one variable died at boot with a DNS error that named
# neither the variable nor the cause. docker-compose.yml now states its own
# Redis explicitly; everywhere else degrades to a table.
_CACHE_URL = config('CACHE_URL', default='database')

if _CACHE_URL and _CACHE_URL != 'database':
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.redis.RedisCache',
            # Deliberately db 2 — db 0 is the Celery broker, db 1 the result backend.
            'LOCATION': _CACHE_URL,
        }
    }
else:
    # No Redis on the plan. A database table is slower than Redis but it is
    # *shared*, which is the property that matters: the default LocMemCache is
    # per-process, so with more than one gunicorn worker the rendered-PDF cache
    # would miss on every other request and the single-flight lock that stops
    # duplicate renders would not work at all.
    # Requires: manage.py createcachetable (the entrypoint runs it).
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.db.DatabaseCache',
            'LOCATION': 'django_cache',
        }
    }

# Same reasoning as the cache: no broker configured means there is no worker,
# so queueing a task would drop it silently. The first casualty is the
# verification email, and nobody can finish registering. Running tasks inline
# is correct but slower — the register and CV-upload requests do the work
# themselves. Compose sets a broker and gets the real queue back.
CELERY_BROKER_URL = config('CELERY_BROKER_URL', default='')
CELERY_RESULT_BACKEND = config('CELERY_RESULT_BACKEND', default='')

CELERY_TASK_ALWAYS_EAGER = config(
    'CELERY_TASK_ALWAYS_EAGER', default=not CELERY_BROKER_URL, cast=bool,
)
CELERY_TASK_EAGER_PROPAGATES = False
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE

ACCOUNT_EMAIL_VERIFICATION = 'none'
ACCOUNT_AUTHENTICATION_METHOD = 'email'
ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_USERNAME_REQUIRED = False
