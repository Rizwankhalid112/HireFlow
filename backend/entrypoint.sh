#!/bin/sh
set -e

echo "Waiting for PostgreSQL at ${DB_HOST:-db}:${DB_PORT:-5432}..."

# A managed database is reached through DATABASE_URL and is already up; only
# the Compose database needs waiting on.
if [ -z "${DATABASE_URL}" ]; then
  while ! python -c "
import socket
s = socket.socket()
s.settimeout(1)
s.connect(('${DB_HOST:-db}', int('${DB_PORT:-5432}')))
s.close()
" 2>/dev/null; do
    sleep 1
  done
  echo "PostgreSQL is ready."
fi

echo "Running migrations..."
python manage.py migrate --noinput

# DatabaseCache needs its table. Harmless and silent when the cache is Redis,
# and "already exists" on every run after the first.
python manage.py createcachetable 2>/dev/null || true

# The image tries collectstatic at build time, but manage.py needs SECRET_KEY
# and a build has no environment — so on a platform it fails there and the
# admin ends up with no CSS. Re-run whenever the directory is missing.
if [ "${COLLECT_STATIC:-false}" = "true" ] || [ ! -d /app/staticfiles ]; then
  echo "Collecting static files..."
  python manage.py collectstatic --noinput
fi

# Both commands are idempotent by design (fixed UUIDs / get_or_create), so
# running them on every boot is safe and removes the two manual post-deploy
# steps that a fresh install silently needs. Without seed_skills the CV
# Builder's autocomplete is empty and no skill is ever canonical-matched.
#
# Worker containers set RUN_SEEDS=false so they do not repeat the web boot.
if [ "${RUN_SEEDS:-true}" = "true" ]; then
  echo "Seeding canonical skills and periodic tasks..."
  python manage.py seed_skills
  python manage.py setup_cv_beat_tasks
  python manage.py setup_job_beat_tasks

  # Companies are seeded on first boot only, not on every deploy.
  # `seed_companies` sets is_active=True on every row it touches, which would
  # quietly undo the runner's auto-disable — the thing that stops us calling a
  # permanently wrong slug 365 times a year. Re-enable one deliberately from
  # the admin, not as a side effect of shipping.
  if [ "$(python manage.py shell -c 'from apps.jobs.models import TrackedCompany; print(TrackedCompany.objects.exists())')" = "False" ]; then
    echo "No tracked companies yet — seeding the verified starter list..."
    python manage.py seed_companies
  fi
fi

# Create the admin account when one is asked for and does not exist yet.
#
# Managed platforms often give no shell, so `createsuperuser` cannot be run
# after a deploy and there is no way into the admin at all. Both variables must
# be set; nothing is created otherwise, and an existing account is never
# touched — so this cannot silently reset a password.
if [ -n "${DJANGO_SUPERUSER_EMAIL}" ] && [ -n "${DJANGO_SUPERUSER_PASSWORD}" ]; then
  python manage.py shell -c "
from django.contrib.auth import get_user_model
import os
User = get_user_model()
email = os.environ['DJANGO_SUPERUSER_EMAIL']
if User.objects.filter(email=email).exists():
    print(f'Admin {email} already exists — leaving it alone.')
else:
    User.objects.create_superuser(
        email=email,
        password=os.environ['DJANGO_SUPERUSER_PASSWORD'],
        full_name=os.environ.get('DJANGO_SUPERUSER_NAME', 'Admin'),
    )
    print(f'Created admin {email}.')
"
fi

exec "$@"
