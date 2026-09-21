# Single-service image: the React build and the Django API in one container.
#
# This is "Option A" — the shape that fits a free plan, where you get one web
# service and a managed Postgres and nothing else. The React bundle is built
# here and copied in; Django serves it through WhiteNoise, so there is no nginx
# and no second container. Docker Compose still uses the per-service
# backend/Dockerfile and frontend/Dockerfile for local development.
#
# Built from the repository root:
#   docker build -t hireflow .

# ── 1. build the SPA ────────────────────────────────────────────────────────
FROM node:20-alpine AS frontend

WORKDIR /app

COPY frontend/package.json frontend/package-lock.json* ./
RUN npm install

COPY frontend/ ./
# VITE_API_URL is deliberately not passed. The client falls back to a relative
# /api, which is correct here because Django serves the bundle and the API from
# the same origin — and it means this image works on any domain unrebuilt.
RUN npm run build

# ── 2. the application ──────────────────────────────────────────────────────
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# WeasyPrint renders through Pango/Cairo, and python:3.12-slim ships neither —
# nor any font, which would silently render every glyph as tofu.
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    libpango-1.0-0 \
    libpangoft2-1.0-0 \
    libharfbuzz0b \
    libffi8 \
    libjpeg62-turbo \
    fontconfig \
    fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && pip install --no-cache-dir -r requirements.txt

COPY backend/ .

# settings.SERVE_SPA switches on the presence of this directory, and WhiteNoise
# serves it at the root so /assets/*.js and /favicon.svg resolve.
COPY --from=frontend /app/dist ./frontend_dist

RUN chmod +x /app/entrypoint.sh && python manage.py collectstatic --noinput \
    || echo "collectstatic deferred to runtime (needs env)"

EXPOSE 8000

ENTRYPOINT ["/app/entrypoint.sh"]
# Two workers, not four: a free instance is typically 512 MB and four Django
# processes plus WeasyPrint will be killed by the OOM reaper. Raise via
# WEB_CONCURRENCY when the plan has the memory for it.
CMD ["sh", "-c", "gunicorn config.wsgi:application --bind 0.0.0.0:${PORT:-8000} --workers ${WEB_CONCURRENCY:-2} --timeout ${WEB_TIMEOUT:-60}"]
