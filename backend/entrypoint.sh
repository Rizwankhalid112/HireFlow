#!/bin/sh
set -e

echo "Waiting for PostgreSQL at ${DB_HOST:-db}:${DB_PORT:-5432}..."
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

echo "Running migrations..."
python manage.py migrate --noinput

if [ "${COLLECT_STATIC:-false}" = "true" ]; then
  echo "Collecting static files..."
  python manage.py collectstatic --noinput
fi

exec "$@"
