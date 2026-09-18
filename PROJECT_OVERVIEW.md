# HireFlow — Complete Project Overview

> **Purpose of this file.** This is the single orientation document for HireFlow.
> Feed it to an AI assistant or hand it to a new developer and they should be able
> to work on the project without reading the whole codebase first. Everything here
> was verified against the actual code on **2026-09-18**, not written from memory.
>
> Deeper reading, once you need it:
> [backend/context.md](backend/context.md) (645 lines) and
> [frontend/context.md](frontend/context.md) (579 lines) are the per-side detail docs.
> Design rationale lives in [docs/](docs/).

---

## 1. What HireFlow is

A job-application platform. A user builds a structured CV, gets AI help writing it,
browses real jobs pulled nightly from employers' own job boards, sees which of those
jobs match their CV, and tailors their CV to a specific job description.

The product splits into four user-facing modules:

| # | Module | What the user does |
|---|--------|--------------------|
| 1 | **CV Builder** | Builds a CV section by section, or uploads an existing PDF/DOCX and lets AI parse it into structured data. Live preview, six templates, exact-snapshot PDF export. |
| 2 | **Job Match** | Pastes a job description, gets back matching keywords, a gap analysis and a cover letter. |
| 3 | **Job Search** | Browses jobs gathered nightly from four ATS platforms, filtered and ranked against their own CV skills. |
| 4 | **Applications** | Kanban tracker for applications they've sent. **Not built yet** — research and build plan complete. |

---

## 2. Languages and tech stack

**Backend is Python. Frontend is JavaScript.** There is no TypeScript anywhere
(zero `.ts`/`.tsx` files) — type safety at the API boundary comes from Zod schemas,
not a compiler.

### Backend — Python 3.12

| Package | Version | Role |
|---|---|---|
| Django | 5.1.4 | Web framework |
| djangorestframework | 3.15.2 | REST API |
| djangorestframework-simplejwt | 5.3.1 | JWT auth |
| django-allauth | 65.3.0 | Google / GitHub social login |
| django-cors-headers | 4.4.0 | CORS |
| psycopg2-binary | 2.9.10 | Postgres driver |
| python-decouple | 3.8 | `.env` config loading |
| celery | 5.4.0 | Background jobs |
| django-celery-beat | 2.7.0 | Database-backed schedules |
| redis | 5.2.1 | Broker / results / cache client |
| gunicorn | 23.0.0 | WSGI server in production |
| whitenoise | 6.8.2 | Static file serving |
| anthropic | 1.3.0 | Claude API client |
| pdfplumber | 0.11.5 | PDF text extraction |
| python-docx | 1.1.2 | DOCX text extraction |
| weasyprint | 66.0 | HTML → PDF rendering |
| pypdfium2 | 5.13.0 | PDF → image thumbnails |
| Pillow | 11.1.0 | Image handling |
| pytest + pytest-django | 8.3.4 / 4.9.0 | Test suite |

### Frontend — JavaScript (JSX) on Node 20

| Package | Version | Role |
|---|---|---|
| react / react-dom | 19.1.0 | UI |
| vite | 6.3.5 | Build tool + dev server |
| react-router-dom | 7.6.2 | Routing |
| @tanstack/react-query | 5.80.7 | Server state, caching, polling |
| @reduxjs/toolkit + react-redux | 2.8.2 / 9.2.0 | Client state (auth) |
| react-hook-form + @hookform/resolvers | 7.57.0 / 5.0.1 | Forms |
| zod | 3.25.56 | Schema validation |
| axios | 1.9.0 | HTTP client |
| tailwindcss + @tailwindcss/vite | 4.1.8 | Styling |
| sonner | 2.0.5 | Toast notifications |
| pdfjs-dist | 6.2.108 | In-browser PDF preview |
| @react-oauth/google | 0.12.2 | Google sign-in |

### Infrastructure

- **PostgreSQL 16** (alpine) — primary datastore, plus full-text search
- **Redis 7** (alpine) — Celery broker, result backend, and application cache
- **nginx 1.27** (alpine) — reverse proxy, the real entry point on port 80
- **Docker Compose** — seven services, orchestrating all of the above

---

## 3. Services and how they fit together

Seven containers defined in [docker-compose.yml](docker-compose.yml):

```
                    ┌─────────────┐
   browser  ──────> │  nginx :80  │  ← the real entry point
                    └──────┬──────┘
                           │
              ┌────────────┴────────────┐
              ▼                         ▼
      ┌───────────────┐         ┌───────────────┐
      │ backend :8000 │         │ frontend :5173│
      │ Django + DRF  │         │ Vite dev srv  │
      └───────┬───────┘         └───────────────┘
              │
      ┌───────┴────────┬──────────────┬──────────────┐
      ▼                ▼              ▼              ▼
┌──────────┐   ┌─────────────┐ ┌─────────────┐ ┌──────────┐
│  db :5432│   │ redis :6379 │ │celery_worker│ │celery_beat│
│ Postgres │   │             │ │  does work  │ │ schedules │
└──────────┘   └─────────────┘ └─────────────┘ └──────────┘
```

**Exposed ports:** nginx `80` (use this), backend `8000`, frontend `5173`,
Postgres `5433` on the host (mapped from 5432 inside, so it doesn't clash with a
local Postgres install).

`db` and `redis` have healthchecks and `backend` waits on them, so startup
ordering is handled automatically.

**Named volumes** — these survive `docker compose down`:
`postgres_data`, `static_volume`, `media_volume`.

> ⚠️ `media_volume` is mounted into **backend, celery_worker and celery_beat**.
> This is load-bearing: `extract_text_from_cv` runs in the worker and opens the
> uploaded file from `MEDIA_ROOT`. Without the mount on the worker, *every CV
> upload fails* with a misleading "this PDF could not be read". This was a real
> launch blocker, fixed 2026-09-08.

### Redis database allocation

Deliberately separated so the app, the queue and the tests never collide:

| DB | Used for |
|---|---|
| 0 | Celery broker |
| 1 | Celery result backend |
| 2 | Django application cache |
| 3 | Test cache — repointed in `pytest_configure` |

Django swaps the *Postgres* database for tests automatically, but **not Redis**.
Without db 3, the suite would write into the running app's cache and leak state
between tests.

---

## 4. Repository layout

```
HireFlow/
├── PROJECT_OVERVIEW.md      ← you are here
├── README.md
├── JOB_SOURCES_RND.md       job-platform research (369 lines)
├── docker-compose.yml       the seven services
├── docker-compose.dev.yml   dev overrides (NOT auto-loaded — needs -f)
├── .env.example             every config key, with comments
├── nginx/                   reverse-proxy config
├── docs/                    design docs and R&D (see §12)
├── backend/
│   ├── config/              settings.py, urls.py, wsgi.py
│   ├── celery_app/          celery.py — the Celery entry point
│   ├── apps/
│   │   ├── accounts/        auth + user profile        ✅ built
│   │   ├── cv_builder/      the big one                ✅ built
│   │   ├── jobs/            job ingestion + browsing   ✅ built
│   │   ├── analytics/       registered, EMPTY
│   │   ├── reports/         registered, EMPTY
│   │   ├── settings_app/    registered, EMPTY
│   │   ├── applications/    NOT registered, EMPTY
│   │   └── notifications/   NOT registered, EMPTY
│   ├── conftest.py          pytest fixtures
│   ├── pytest.ini
│   └── requirements.txt
└── frontend/
    └── src/
        ├── app/             router, providers, redux store
        ├── features/
        │   ├── auth/        13 files  ✅
        │   ├── cvBuilder/   36 files  ✅
        │   ├── jobs/         5 files  ✅
        │   └── jobMatch/     2 files  ✅
        ├── components/      shared UI
        ├── routes/          ProtectedRoute, PublicOnlyRoute
        ├── api/  hooks/  lib/  store/  styles/  utils/  pages/
        └── main.jsx
```

**Scale:** 192 Python files, 75 `.jsx` + 25 `.js` files.
`cv_builder` alone is 7,867 lines across 90 files — it is by far the largest app.
`jobs` is 1,471 lines / 29 files; `accounts` is 587 lines / 14 files.

---

## 5. Module completion status

**Three of eight backend apps are built. Five are empty scaffolding.**

| App | In `INSTALLED_APPS` | Files | Lines | Models | Migrations | Status |
|---|---|---|---|---|---|---|
| `accounts` | ✅ | 14 | 587 | 1 | 1 | ✅ **Complete** |
| `cv_builder` | ✅ | 90 | 7,867 | 12 | 7 | ✅ **Complete** |
| `jobs` | ✅ | 29 | 1,471 | 2 | 2 | ✅ **Complete** |
| `analytics` | ✅ | 8 | **0** | 0 | 0 | ⬜ Empty stub |
| `reports` | ✅ | 8 | **0** | 0 | 0 | ⬜ Empty stub |
| `settings_app` | ✅ | 8 | **0** | 0 | 0 | ⬜ Empty stub |
| `applications` | ❌ | 8 | **0** | 0 | 0 | ⬜ Empty stub — **next to build** |
| `notifications` | ❌ | 8 | **0** | 0 | 0 | ⬜ Empty stub |

The five empty apps contain only Django's default `models.py` / `views.py` /
`tests.py` scaffolding with no content. `applications` and `notifications` are on
disk but **not registered** in `INSTALLED_APPS`, so Django does not load them at all.

### Feature-level status

| Feature | Status | Notes |
|---|---|---|
| Email registration + verification | ✅ | Token-based, email sent via Celery |
| JWT login / refresh / logout | ✅ | Refresh token in httpOnly cookie |
| Password reset | ✅ | Token-based |
| Google OAuth | ✅ | via allauth |
| GitHub OAuth | ✅ | endpoint exists |
| CV Builder — all 7 sections | ✅ | experience, education, skills, projects, certifications, languages, profile |
| Drag-and-drop reordering | ✅ | every list section has a `reorder/` endpoint |
| Live CV preview | ✅ | debounced, ETag-cached, single-flight |
| 6 CV templates | ✅ | exact-snapshot rendering |
| PDF export (WeasyPrint) | ✅ | what you see is what you download |
| CV upload (PDF/DOCX) | ✅ | 5 MB cap, path-traversal guard, scanned-PDF detection |
| AI CV parsing | ✅ | Claude structured outputs; handles CVs whose section names differ from ours |
| Diff / overwrite protection on import | ✅ | an upload never silently clobbers existing data |
| CV reset / delete | ✅ | per-section or whole-CV |
| AI writing suggestions | ✅ | bullets, summary, skills, projects, title |
| Job Match (paste a JD) | ✅ | keywords, gap analysis, cover letter |
| Job ingestion from 4 ATS platforms | ✅ | nightly, concurrent, upsert-safe |
| Job browsing + filters + search | ✅ | Postgres full-text search |
| CV-based job ranking | ✅ | ranks jobs against the user's own skills |
| One-click tailor handover | ✅ | job → Job Match |
| **Applications Kanban tracker** | ❌ | **R&D + build plan done, no code** |
| Analytics dashboard | ❌ | empty app |
| Reports | ❌ | empty app |
| In-app notifications | ❌ | empty app |
| User settings page | ❌ | empty app |
| Frontend test harness | ❌ | no automated frontend coverage at all |

---

## 6. Data model — 15 models

### `accounts` (1)
- **`UserProfile`** — extends Django's `User`. Email verification and password-reset tokens.

### `cv_builder` (12)
- **`CVProfile`** — the root. One per user. Holds name, contact, summary, `template_id`.
- **`WorkExperience`** → **`WorkBullet`** — jobs and their achievement lines.
  ⚠️ `WorkBullet` has **no `cv` field**; it attaches via `experience=`.
- **`Education`** — degrees, institutions, CGPA (stored as value + scale).
- **`CVSkill`** — a skill on a CV, resolved against `SkillCanonical`.
- **`SkillCanonical`** — the master skill list (see §8).
- **`CVProject`**, **`CVCertification`**, **`CVLanguage`** — the smaller sections.
- **`CVUploadLog`** — one row per uploaded file: status, extracted text, parsed JSON, errors. Drives the frontend's polling.
- **`AISuggestionLog`** — every AI suggestion request, for auditing and monthly credit counting.
- **`JobMatch`** — a pasted job description plus its AI analysis and cover letter.

### `jobs` (2)
- **`TrackedCompany`** — a company we harvest. Holds `platform`, `slug`, `is_active`,
  `last_fetched_at`, `last_fetch_status`, `last_job_count`, `consecutive_failures`.
  Those last fields make a board that quietly stopped returning jobs *visible*
  rather than silently absent.
- **`Job`** — a listing. Unique on **`(source, external_id)`** so re-running the
  gather updates rather than duplicates.

**Job indexing for scale** (this is what stops it slowing down at millions of rows):
- `GinIndex` on `search_vector` for full-text search
- descending index on `posted_at`
- composite indexes pairing each filter with each sort
- `is_long_running` flags listings older than 365 days
- retention sweeps key on `last_seen_at`

Two `TextChoices` enums, not models: **`ATSPlatform`** (greenhouse, ashby, lever,
workable) and **`RemoteType`**.

---

## 7. Celery — background jobs and schedules

Entry point: [backend/celery_app/celery.py](backend/celery_app/celery.py).
`celery_beat` runs with `--scheduler django_celery_beat.schedulers:DatabaseScheduler`,
so **schedules live in the database**, not in code. They survive restarts and are
editable live in Django admin under *Periodic Tasks*.

### All 9 tasks

**`apps.accounts.tasks`**
| Task | Trigger |
|---|---|
| `send_verification_email(user_id)` | on registration |
| `send_password_reset_email(user_id)` | on reset request |

**`apps.cv_builder.tasks`**
| Task | Schedule |
|---|---|
| `extract_text_from_cv(log_id)` | on upload |
| `send_to_ai_parser(log_id)` | after extraction |
| `send_draft_reminder()` | daily 09:00 |
| `delete_stale_drafts()` | daily 02:00 |
| `delete_orphaned_files()` | weekly, Sunday 03:00 |
| `fail_stuck_uploads()` | **every 5 minutes** |

> `fail_stuck_uploads` runs every 5 minutes rather than daily on purpose: it is
> what stops the frontend polling a row whose worker died. The delay before it
> fires is time a user spends watching a spinner.

**`apps.jobs.tasks`**
| Task | Schedule |
|---|---|
| `gather_jobs()` | daily **03:00 UTC** |

### ⚠️ Schedules are NOT registered automatically

Because the schedules live in the database, a fresh deploy has **no schedules at
all** until you run two one-time commands. Nothing auto-runs them — not an
entrypoint script, not a settings `beat_schedule`, not an app-ready hook. This is
the single easiest thing to forget when deploying.

```bash
docker compose exec backend python manage.py setup_cv_beat_tasks   # 4 CV tasks
docker compose exec backend python manage.py setup_job_beat_tasks  # nightly gather
```

Run each **once**. After that they fire forever with no further input.

Verify they registered:
```bash
docker compose exec backend python manage.py shell -c \
  "from django_celery_beat.models import PeriodicTask; print(list(PeriodicTask.objects.values_list('name','enabled')))"
```

---

## 8. The skill seed — 270 canonical skills

Fixture: [backend/apps/cv_builder/fixtures/canonical_skills.json](backend/apps/cv_builder/fixtures/canonical_skills.json) (78 KB).

```bash
docker compose exec backend python manage.py seed_skills   # ⚠️ also not automatic
```

Each record has `canonical_name`, `aliases`, `category`, `logo_url`, `is_popular`:

```json
{"canonical_name": "Python", "aliases": ["Python3", "python"],
 "category": "Languages", "logo_url": null, "is_popular": true}
```

| Category | Count |
|---|---|
| Tools | 65 |
| Frameworks | 49 |
| Concepts | 45 |
| Languages | 35 |
| Cloud | 27 |
| Soft Skills | 26 |
| Databases | 23 |
| **Total** | **270** |

**Why aliases matter.** The skill detector resolves aliases to canonical names and
de-duplicates, so "Python3", "python" and "Python" become one skill, not three.
It also drives CV-based job ranking — a CV saying "Postgres" still matches a job
asking for "PostgreSQL".

**The detector is boundary-aware, and this was a real bug.** It used to do a plain
`name in text` substring check. 27 canonical skills are 1–2 characters, so *every*
bullet got tagged `R`, most also `C`, and "Managed relationships with 30 enterprise
clients" returned `['PS','sh','TS','C','R']`. It now uses identifier-aware
boundaries that handle `Node.js` correctly while still matching "deploys in Go."
at the end of a sentence. Fixed 2026-09-08, pinned by tests.

A `post_save`/`post_delete` signal on `SkillCanonical` invalidates the detector's
cache, so a freshly seeded skill is detectable immediately.

---

## 9. Where the jobs come from

**Four ATS platforms, via their public job-board APIs — not scraping:**
**Greenhouse, Ashby, Lever, Workable.**

These are documented public endpoints that employers publish deliberately so their
jobs get distributed.

**Deliberately excluded:**
- **LinkedIn, Indeed, Glassdoor** — their terms prohibit it
- **SmartRecruiters, Recruitee** — tested, return nothing usable

Full research: [JOB_SOURCES_RND.md](JOB_SOURCES_RND.md).

### The 13 seeded companies

All slugs verified live on 2026-09-10 — many slugs in circulation are simply wrong.

| Platform | Companies |
|---|---|
| Greenhouse | Stripe, GitLab, Airbnb, Robinhood, Monzo |
| Ashby | OpenAI, Ramp, Notion, Linear, PostHog |
| Lever | Palantir, Match Group |
| Workable | Blueground |

```bash
docker compose exec backend python manage.py seed_companies   # create the 13
docker compose exec backend python manage.py fetch_jobs       # run the gather now
```

`fetch_jobs` flags: `--platform`, `--slug`, `--no-purge`, `--workers` (default 4).

### How the nightly gather behaves

- **Concurrent across companies**, 4 workers. Lever takes 5–20s per request while
  the others take ~1s; a serial run would spend most of its time waiting on Lever.
- **Failure-isolated** — one company failing never stops the run.
- **Upsert, not insert** — safe to re-run, never duplicates. Batch size 500.
- **Retention sweep** deletes jobs not seen in 45 days (`JOBS_RETENTION_DAYS`).
- **Auto-pause** after 5 consecutive failures — almost always a wrong slug, and
  retrying it nightly forever is just log noise.
- Search-vector refresh is **scoped by source**, so one source can't rewrite
  another's rows.

> 03:00 UTC is 08:00 in Pakistan. If your users are mainly there, consider moving
> it earlier so fresh jobs are ready when they wake up — one line in
> `setup_job_beat_tasks.py`, or edit it live in Django admin.

---

## 10. AI integration (Claude)

Client: [backend/apps/cv_builder/services/ai/client.py](backend/apps/cv_builder/services/ai/client.py).
Uses the Anthropic SDK with **structured outputs** (`messages.parse(output_format=PydanticModel)`)
so responses are validated Pydantic objects, not hand-parsed JSON. System prompts
are constants to keep **prompt caching** effective.

### Turning it on

```bash
# in .env
ANTHROPIC_API_KEY=sk-ant-...
```
```bash
docker compose restart backend celery_worker
```

**The design fails soft.** With the key blank, AI endpoints return `503` and
everything else keeps working — CV building, templates, PDF export, job browsing.
The frontend asks the API whether the feature is `enabled` and hides the buttons,
so nobody clicks a dead button.

> 🔒 Put the real key in `.env` only — never in `.env.example` or any tracked file.
> `.env` is gitignored and no key has ever been committed. For a shared repo, a
> vault or CI secret store is a better home than a file on disk.

### What AI is used for

1. **CV parsing** — uploaded PDF/DOCX → structured CV data. The prompt contract
   demands `null` over fabrication. Handles CVs whose section headings differ from ours.
2. **Writing suggestions** — bullets, summary, skills, projects, job title.
   Targets Google's XYZ formula for achievement lines.
3. **Job Match** — job description → keywords, gap analysis, cover letter.

### Cost controls (all tunable in `.env`)

| Setting | Default | Meaning |
|---|---|---|
| `AI_MODEL` | `claude-opus-5` | model used |
| `AI_EFFORT` | `low` | reasoning effort |
| `AI_MONTHLY_CREDITS` | 60 | suggestions per user per month |
| `AI_SUGGEST_THROTTLE` | 20/min | rate limit |
| `AI_PARSE_MONTHLY_LIMIT` | 5 | CV parses per user per month |
| `AI_PARSE_MAX_TOKENS` | 8000 | |
| `CV_UPLOAD_THROTTLE` | 5/hour | |
| `AI_JOB_MATCH_MONTHLY_LIMIT` | 20 | |
| `JOB_MATCH_THROTTLE` | 10/hour | |
| `AI_JOB_MATCH_MAX_TOKENS` | 6000 | |

Credits use a **count-rows-never-decrement** pattern against `AISuggestionLog`, so
a crash mid-request can't leak free credits.

---

## 11. API surface — 59 endpoints

Mounted in [backend/config/urls.py](backend/config/urls.py):

```
/health/              health check
/admin/               Django admin
/api/auth/            authentication
/api/users/           user profile
/api/cv/              CV builder  (45 routes)
/api/jobs/            job search  (3 routes)
```

### `/api/auth/` and `/api/users/` (11)
`register/` · `verify-email/<token>/` · `login/` · `logout/` · `token/refresh/` ·
`forgot-password/` · `reset-password/` · `google/` · `github/` · `profile/` ·
`change-password/`

### `/api/cv/` (45)

**Profile & output** — `profile/` · `profile/completion/` · `profile/reset/` ·
`photo/` · `templates/` · `preview/` · `preview/meta/`

**Upload & AI parse** — `upload/` · `upload/<log_id>/status/` ·
`upload/<log_id>/retry/` · `upload/<log_id>/apply/`

**Job match** — `job-match/` · `job-match/sources/` · `job-match/<pk>/`

**AI suggestions** — `suggest/credits/` · `suggest/bullets/` · `suggest/summary/` ·
`suggest/skills/` · `suggest/projects/` · `suggest/title/` · `suggest/<log_id>/accept/`

**Sections** — each of `work-experience/`, `education/`, `skills/`, `projects/`,
`certifications/`, `languages/` has list/create, `<pk>/` detail and `reorder/`.
Skills additionally have `skills/search/` and `skills/bulk-add/`.

### `/api/jobs/` (3)
`""` (list, with filters + full-text search) · `stats/` · `<uuid:pk>/`

### Frontend routes

Public: `/login` · `/register` · `/forgot-password` · `/reset-password/:token` ·
`/verify-email/:token`
Protected: `/home` · `/cv-builder` · `/job-match` · `/jobs`

---

## 12. Documentation map

| File | Lines | What it covers |
|---|---|---|
| [backend/context.md](backend/context.md) | 645 | Backend architecture, settings, API, conventions, loose ends |
| [frontend/context.md](frontend/context.md) | 579 | Frontend architecture and conventions |
| [docs/cv_builder_spec.md](docs/cv_builder_spec.md) | ~1,263 | The master CV spec. Steps 7–10 hold the upload/parse/export designs |
| [docs/applications_build_plan.md](docs/applications_build_plan.md) | ~643 | **Build-ready plan for the next module** |
| [docs/cv_upload_parse_plan.md](docs/cv_upload_parse_plan.md) | ~529 | Upload + AI parse design |
| [docs/cv_live_preview_plan.md](docs/cv_live_preview_plan.md) | ~381 | Live preview caching and single-flight |
| [JOB_SOURCES_RND.md](JOB_SOURCES_RND.md) | 369 | Every job platform evaluated, with legal findings |
| [docs/job_match_rnd.md](docs/job_match_rnd.md) | ~337 | Job match research |
| [docs/cv_templates_build_plan.md](docs/cv_templates_build_plan.md) | — | Template system |
| [docs/cv_templates_rnd.md](docs/cv_templates_rnd.md) | — | Template research |
| [docs/cv_ai_suggestions_rnd.md](docs/cv_ai_suggestions_rnd.md) | — | AI suggestions research |
| [docs/applications_rnd.md](docs/applications_rnd.md) | — | Applications research |
| [docs/job_search_module_spec.md](docs/job_search_module_spec.md) | — | Job search spec |
| [docs/postman/](docs/postman/) | — | Postman collection |

**Working convention:** features are designed in a `docs/*.md` plan *before* any
code is written, and the plan overrides the older spec where they disagree.

---

## 13. Running it

### First-time setup

```bash
cp .env.example .env          # then fill in ANTHROPIC_API_KEY and OAuth creds
docker compose up -d --build

# one-time bootstrap — none of these run automatically
docker compose exec backend python manage.py migrate
docker compose exec backend python manage.py createsuperuser
docker compose exec backend python manage.py seed_skills
docker compose exec backend python manage.py seed_companies
docker compose exec backend python manage.py setup_cv_beat_tasks
docker compose exec backend python manage.py setup_job_beat_tasks
docker compose exec backend python manage.py fetch_jobs
```

App is then at **http://localhost** (through nginx).

### Everyday commands

```bash
docker compose up -d                 # start everything
docker compose down                  # stop everything — data is SAFE
docker compose ps                    # what's running and healthy
docker compose logs -f backend       # follow one service
docker compose restart backend       # after editing .env
docker compose up -d --build         # after changing Dockerfile/requirements
```

> ⚠️ **`docker compose down -v` deletes your database.** The `-v` removes the named
> volumes — users, CVs and every fetched job, permanently, with no undo. Plain
> `down` is what you want for everyday stop/start.

After starting, the backend runs migrations and collectstatic, so the site may 502
for the first 10–20 seconds. Watch `docker compose logs -f backend` until it settles.

**Known gotcha:** if the frontend 500s after a restart with an empty-looking error,
it's a stale anonymous `node_modules` volume. Fix it with
`docker compose exec frontend rm -rf /app/node_modules && docker compose restart frontend`
— *not* `down -v`.

> `docker-compose.dev.yml` is **not** auto-loaded. Compose only auto-loads
> `docker-compose.override.yml`. Pass it explicitly with `-f` if you want it.

---

## 14. Tests

**333 test functions across 26 files**, pytest + pytest-django. Config in
`backend/pytest.ini`, fixtures in `backend/conftest.py`.

```bash
docker compose exec backend pytest                                # everything
docker compose exec backend pytest apps/cv_builder/tests/ -m "not slow"
```

Coverage: **`cv_builder` 23 files, `jobs` 3 files, `accounts` none.**

Three things about the harness are load-bearing:

1. **`pytest_configure` repoints `CACHES` at Redis db 3.** Django swaps the database
   for tests but not Redis. Without this the suite writes into the running app's
   cache and the single-flight test would pass for the wrong reason.
2. **`test_preview_singleflight.py` needs `django_db(transaction=True)`.** The
   default test case wraps each test in a transaction other threads cannot see, so
   a threaded test either deadlocks or renders an empty CV.
3. **`testpaths = apps`** matters — a checked-out `backend/venv/` sits in the tree
   and its site-packages are full of third-party test modules that would otherwise
   be collected.

Renders cost ~250–360ms each, so six-template sweeps are marked `slow` and can be
deselected. Keep it that way or people stop running the suite.

> The suite was not re-run while writing this document (the stack was down), so
> treat the count as accurate and the pass state as unverified-today.

---

## 15. Known loose ends

Ordered by impact. Fuller detail in [backend/context.md](backend/context.md) §13.

1. **`seed_skills`, `seed_companies`, `setup_cv_beat_tasks`, `setup_job_beat_tasks`
   are not automated.** A fresh deploy has no canonical skills, no tracked
   companies and no schedules until someone runs them by hand. **Highest-impact
   item here** — it's silent, and the app looks broken rather than unconfigured.
2. **No frontend test harness.** The import modal, the polling hook and the reset
   UI have zero automated coverage.
3. **No DB-level uniqueness on `CVSkill (cv, name)`** — concurrent adds can slip
   past the application-level `get_or_create`.
4. **`LogoutView` requires a live access token**, so an expired session cannot
   clear or blacklist its refresh cookie.
5. **No logging config and no OpenAPI schema.**
6. **`accounts` has no tests at all** despite handling auth.
7. Deprecated allauth 65 setting names at `settings.py:163-166`.
8. Empty `config/asgi.py`; no `backend/apps/__init__.py` (works only via PEP 420
   namespace packages).
9. `apps.applications` / `apps.notifications` exist on disk but are not in
   `INSTALLED_APPS`.
10. `NotFound` imported but unused in `views/cv_profile.py`; `permissions.py`
    entirely unused.
11. `project_url` and `credential_url` have no scheme normalization (profile URLs do).
12. **`extract_metric` does not read spelled-out numbers** ("a team of four
    engineers"). Deliberate, and pinned by a test so it stays a decision — parsing
    English numerals is a separate job, and the AI asking for the figure is the
    right outcome.

---

## 16. What to build next

1. **Applications / Kanban tracker** — the clear next module. R&D and a ~643-line
   build plan are done; no code exists. Plan splits into Day 1 (data spine) and
   Day 2 (board UI). Note the app is not yet in `INSTALLED_APPS`.
2. **Automate the bootstrap commands** (loose end #1) — cheapest real win available.
3. **Obtain JSearch + Jooble API keys** — the only lawful route to LinkedIn-sourced
   data and Pakistan-market coverage.
4. **Expand the tracked-company list** beyond the 13 verified seeds.
5. **Frontend test harness** — currently zero coverage.
6. **Visual browser click-through of the UI** — verification so far has been
   API-level only.

---

## 17. Conventions worth knowing

- **Plan before code.** Features get a `docs/*.md` plan first; the plan overrides
  the older spec.
- **Keep the context docs current.** If you change a serializer field, choice value
  or route, update `backend/context.md`, `frontend/context.md` and the matching
  frontend feature in the *same* change.
- **The frontend mirrors backend contracts** in
  `features/cvBuilder/constants.js` (choice values) and
  `features/cvBuilder/schemas/cvSchemas.js` (validation). Those are the first two
  places to break when the backend contract moves.
- **Never commit build artifacts.** `.vite/`, `node_modules/`, `__pycache__`,
  `.env`, media uploads are all gitignored.
- **AI features must fail soft** — no API key means a clean `503` and a hidden
  button, never a broken page.
- **Ingestion must be idempotent** — always upsert on `(source, external_id)`.
