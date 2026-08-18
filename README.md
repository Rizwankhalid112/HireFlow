# HireFlow

**Track. Automate. Get Hired.**

Full-stack SaaS for managing job applications, follow-ups, and hiring progress.

## Stack

- **Backend:** Django + Django REST Framework
- **Frontend:** React + Vite
- **Database:** PostgreSQL
- **Task queue:** Celery + Redis
- **Proxy:** Nginx
- **Containers:** Docker Compose

## Quick start (development)

```bash
# 1. Copy environment variables
cp .env.example .env

# 2. Start all services
docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build
```

### URLs

| Service   | URL                        |
|-----------|----------------------------|
| App       | http://localhost           |
| API       | http://localhost:8000      |
| Frontend  | http://localhost:5173      |
| Admin     | http://localhost/admin/    |
| Health    | http://localhost/health/   |

### Common commands

```bash
# Create superuser
docker compose exec backend python manage.py createsuperuser

# Run migrations manually
docker compose exec backend python manage.py migrate

# View logs
docker compose logs -f backend celery_worker celery_beat

# Stop all services
docker compose down

# Reset database (destroys data)
docker compose down -v
```

## Production

```bash
docker compose up --build -d
```

Production uses the built React app (served by Nginx inside the frontend container) and Gunicorn for Django.

## Services

| Service        | Description                          |
|----------------|--------------------------------------|
| `db`           | PostgreSQL database                  |
| `redis`        | Celery broker & result backend       |
| `backend`      | Django API                           |
| `celery_worker`| Background task worker               |
| `celery_beat`  | Scheduled task scheduler             |
| `frontend`     | React application                    |
| `nginx`        | Reverse proxy (single entry point)   |
