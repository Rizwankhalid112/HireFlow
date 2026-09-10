# HireFlow Backend — Context

> Orientation document for the Django backend. Read this first when returning to the project.
> Last verified against commit `d1e740b` (branch `feat/template-user-cv-builder-module`).

---

## 1. What this is

HireFlow is a job-application tracking platform. The backend is a Django 5 + DRF API serving a React SPA
through an nginx reverse proxy. Two modules are actually built today:

- **`accounts`** — authentication and user profiles (email/password, email verification, password reset, Google + GitHub social login).
- **`cv_builder`** — "Module 8": a structured master-CV editor (one CV per user) with completion scoring, skill autocomplete, and retention jobs.

Everything else (`applications`, `notifications`, `analytics`, `reports`, `settings_app`) is **empty scaffolding** — every `.py` file in those apps is 0 bytes.

The CV Builder is being built against a 10-step spec at `docs/cv_builder_spec.md`. **All ten steps are
now built**, though two of them landed differently from the spec:

- **Steps 1–6** — models, lifecycle, contact/summary, work experience, education/skills,
  projects/certs/languages.
- **Steps 7–8** — CV file upload, PDF/DOCX text extraction, and AI parse with a review-before-apply
  diff flow. Built 2026-09-07 against [docs/cv_upload_parse_plan.md](../docs/cv_upload_parse_plan.md),
  which supersedes the spec where they disagree. See §6.6.
- **Step 9** — PDF export, built as an *exact-snapshot preview* (`/cv/preview/`) with the download
  taken client-side from those same bytes. The spec's async `/cv/export/pdf|status|download/`
  endpoints were not built and are not planned; the guarantee they existed to provide (what you
  download is what you saw) is met more directly this way.
- **Step 10** — the React CV Builder UI.

Two features beyond the spec are also live: the **live preview** across all sections
([docs/cv_live_preview_plan.md](../docs/cv_live_preview_plan.md)) and **AI writing suggestions**
([docs/cv_ai_suggestions_rnd.md](../docs/cv_ai_suggestions_rnd.md)).

---

## 2. Tech stack

| Package | Version | Role |
|---|---|---|
| Django | 5.1.4 | web framework |
| djangorestframework | 3.15.2 | API layer |
| djangorestframework-simplejwt | 5.3.1 | JWT access/refresh + blacklist |
| django-cors-headers | 4.4.0 | CORS |
| django-allauth | 65.3.0 | `SocialAccount` models (Google, GitHub) |
| psycopg2-binary | 2.9.10 | Postgres driver |
| python-decouple | 3.8 | env config |
| celery | 5.4.0 | task queue |
| redis | 5.2.1 | broker client |
| django-celery-beat | 2.7.0 | DB-backed scheduler |
| gunicorn | 23.0.0 | prod WSGI server |
| whitenoise | 6.8.2 | static file serving |
| anthropic | 1.3.0 | Claude client for AI writing suggestions |
| weasyprint | 66.0 | CV template → PDF (needs Pango; see Dockerfile) |
| Pillow | 11.1.0 | avatar `ImageField` |
| requests | 2.32.3 | OAuth userinfo calls |

Runtime: Python 3.12-slim, PostgreSQL 16-alpine, Redis 7-alpine, Nginx 1.27-alpine.

All of `pdfplumber`, `python-docx`, `weasyprint`, the Anthropic SDK and `pytest` are now present — the earlier note listing them as deliberately absent is obsolete.

---

## 3. Architecture

```
nginx :80
  ├─ /api/, /admin/, /health/, /media/ ─▶ backend (gunicorn :8000)
  ├─ /static/ ────────────────────────▶ static_volume
  └─ /        ────────────────────────▶ frontend (:80 prod / :5173 dev)

backend ─▶ postgres:5432 (host-mapped 5433)
        ─▶ redis:6379/0 broker, /1 result backend

celery_worker ─ celery -A celery_app worker
celery_beat   ─ celery -A celery_app beat --scheduler django_celery_beat.schedulers:DatabaseScheduler
```

Layout: `backend/config/` (settings, urls, wsgi, asgi) · `backend/celery_app/` · `backend/apps/<app>/`.

Infra files: [docker-compose.yml](../docker-compose.yml) (7 services, healthchecks on db/redis/backend, volumes `postgres_data`/`static_volume`/`media_volume`), [docker-compose.dev.yml](../docker-compose.dev.yml) (bind-mounts source, exposes 8000 + 5173, swaps in `nginx.dev.conf` with WebSocket upgrade headers for Vite HMR), [nginx/nginx.conf](../nginx/nginx.conf) and [nginx/nginx.dev.conf](../nginx/nginx.dev.conf) (`client_max_body_size 20M`), [entrypoint.sh](entrypoint.sh) (TCP-polls Postgres → `migrate --noinput` → conditional `collectstatic` when `COLLECT_STATIC=true` → `exec "$@"`).

---

## 4. Settings — [config/settings.py](config/settings.py)

One settings module, no dev/prod split; everything via `python-decouple`.

**INSTALLED_APPS** — Django (incl. `sites`, `SITE_ID = 1`) + `rest_framework`, `rest_framework_simplejwt`(+`token_blacklist`), `corsheaders`, `django_celery_beat`, `allauth`(+`account`, `socialaccount`, google & github providers) + local `apps.accounts`, `apps.cv_builder`, `apps.analytics`, `apps.reports`, `apps.settings_app`.
Note: `apps.applications` and `apps.notifications` exist on disk but are **not** installed.

**DRF** — default permission `IsAuthenticated`, default auth `JWTAuthentication` only. No pagination, throttling, versioning, filter backends, or OpenAPI schema configured.

**SIMPLE_JWT** — access 15 min, refresh 7 days, `ROTATE_REFRESH_TOKENS=True`, `BLACKLIST_AFTER_ROTATION=True`.

**Auth** — `AUTH_USER_MODEL = 'accounts.User'`; backends `ModelBackend` + allauth's. allauth settings at lines 163–166 use the pre-65 names (`ACCOUNT_AUTHENTICATION_METHOD`, `ACCOUNT_EMAIL_REQUIRED`, `ACCOUNT_USERNAME_REQUIRED`), which allauth 65 renamed — they are effectively inert. Email verification is enforced by our own `LoginSerializer`, not by allauth.

**Other** — Postgres via `DB_*` env vars (no `CONN_MAX_AGE`). Celery JSON-only, UTC. `CORS_ALLOW_CREDENTIALS = True` (needed for the refresh cookie). `USE_X_FORWARDED_HOST` + `SECURE_PROXY_SSL_HEADER`. Email backend defaults to console. Custom `FRONTEND_URL` builds verify/reset/reminder links.

**Configured 2026-08-18:** `CACHES` → Redis db 2 (db 0 is the Celery broker, db 1 the result
backend). Required for the PDF render cache to work across gunicorn workers.

**Throttling:** `ScopedRateThrottle` is the default class, with two rates — `ai_suggest`
(`20/min`, added 2026-09-03) and `cv_upload` (`5/hour`, added 2026-09-07). Both cover endpoints that
spend money per call; an upload does so one step removed, by queueing a task that calls Claude.
Everything else remains unthrottled.

**AI settings:** `ANTHROPIC_API_KEY` (blank by default — the feature degrades to 503 and nothing
else changes), `AI_MODEL` (`claude-opus-5`), `AI_EFFORT` (`low`), `AI_TIMEOUT_SECONDS`,
`AI_MONTHLY_CREDITS` (60).

**Upload & parse settings (2026-09-07):** `AI_PARSE_MONTHLY_LIMIT` (5), `AI_PARSE_MAX_TOKENS`
(8000 — the suggestion ceiling of 2000 truncates a full CV, and a truncated structured output
arrives as `parsed_output=None` with nothing explaining why), `CV_UPLOAD_MAX_BYTES` (5 MB),
`CV_EXTRACT_MAX_PAGES` (30), `CV_EXTRACT_MAX_CHARS` (60k), `CV_EXTRACT_MIN_CHARS` (100 — below this
the file is treated as scanned and no API call is made), `CV_UPLOAD_STUCK_MINUTES` (5),
`FILE_UPLOAD_MAX_MEMORY_SIZE` (2 MB, now set explicitly).

**Not configured:** `LOGGING`, `CSRF_TRUSTED_ORIGINS`, `SECURE_HSTS_*`, `DATA_UPLOAD_MAX_MEMORY_SIZE`.

### URL root — [config/urls.py](config/urls.py)

| Path | Target |
|---|---|
| `/health/` | inline view → `{"status":"ok"}` (used by compose healthcheck + nginx) |
| `/admin/` | Django admin |
| `/api/auth/` | `apps.accounts.urls.auth_urlpatterns` |
| `/api/users/` | `apps.accounts.urls.user_urlpatterns` |
| `/api/cv/` | `apps.cv_builder.urls` |

Media is served by Django only when `DEBUG`. The accounts app exports **two** urlpattern lists from one module instead of using `include()` — an in-house convention, don't be surprised by it.

---

## 5. `apps/accounts`

### Models — [apps/accounts/models.py](apps/accounts/models.py)

**`User(AbstractBaseUser, PermissionsMixin)`**, table `users`, `USERNAME_FIELD='email'`, `REQUIRED_FIELDS=['full_name']`:
UUID PK · `email` (unique) · `full_name` · `auth_provider` (email/google/github/twitter) · `is_email_verified` · `is_active` · `is_staff` · `date_joined`.
There is **no** `username`, `first_name`, or `last_name`. `twitter` is a declared choice with no implementation.

**`UserProfile`**, table `user_profiles` — the `OneToOneField` to User *is* the PK (`related_name='profile'`, CASCADE): `avatar`, `job_title`, `target_role`, `target_country`, `target_salary`, `linkedin_url`, `github_url`, `phone`, timestamps. Auto-created by a `post_save` signal on User.

### Supporting modules

- [managers.py](apps/accounts/managers.py) — `create_user` calls `set_unusable_password()` when password is None (the social path); `create_superuser` forces staff/superuser/active/verified.
- [cookies.py](apps/accounts/cookies.py) — **the refresh-token convention.** `refresh_token` cookie, 7-day max-age, `httponly=True`, `secure=not DEBUG`, `samesite='Lax'`. The refresh token **never appears in a response body**; only the short-lived access token does.
- [errors.py](apps/accounts/errors.py) — `AuthMessages` / `AuthSuccessMessages` constants. All user-facing strings live here, including the deliberately non-enumerating forgot-password copy.
- [social.py](apps/accounts/social.py) — token-exchange social login: the frontend obtains a provider access token, the backend verifies it against Google's `oauth2/v3/userinfo` or GitHub's `/user` (falling back to `/user/emails` for a primary+verified address). Resolves an existing `SocialAccount` by (provider, uid), else matches `email__iexact`, else creates a passwordless verified user. All provider calls use `timeout=10`.
- [tasks.py](apps/accounts/tasks.py) — `send_verification_email` and `send_password_reset_email`, both using `django.core.signing.dumps` with salts `email-verify` / `password-reset`. Max-ages are enforced view-side (`VERIFY_MAX_AGE=86400`, `RESET_MAX_AGE=3600`).

### Behavior notes that will bite you

- `LogoutView` has no `permission_classes` override, so it inherits `IsAuthenticated`. A client whose 15-minute access token already expired gets 401 and its refresh cookie is never cleared or blacklisted.
- `UserProfileView.put` passes `partial=True`, so PUT behaves like PATCH.
- `TokenRefreshView` hand-rolls rotation (blacklist old → mint new) instead of using SimpleJWT's built-in view, which makes the `ROTATE_REFRESH_TOKENS`/`BLACKLIST_AFTER_ROTATION` settings redundant on that path.

---

## 6. `apps/cv_builder`

Deliberately modular: `models/`, `serializers/`, `views/`, `services/`, `management/commands/`, `fixtures/`, plus flat `urls.py`, `permissions.py`, `signals.py`, `tasks.py`, `utils.py`, `admin.py`. One model per file, re-exported through each package's `__init__.py`.

### Models — [apps/cv_builder/models/](apps/cv_builder/models/)

Every model: UUID PK, explicit `db_table`, an `order` IntegerField, and `created_at`. Text fields use `blank=True, default=''` rather than `null=True`.

| Model | Table | Key points |
|---|---|---|
| `CVProfile` | `cv_profiles` | OneToOne → User (`cv_profile`) — **one master CV per user, by design**. Contact fields, `summary`, `template_id`, `is_complete`, `completion_score`, `content_updated_at`, `pdf_file`, `pdf_generated_at`, `reminder_sent`. `save()` recomputes completion every time, so the score is never stale. `touch_content_updated_at()` does a queryset `.update()` to bump the timestamp without re-saving. |
| `WorkExperience` | `cv_work_experiences` | FK → CVProfile (`work_experiences`). `employment_type` (full_time/part_time/internship/contract/freelance), `location_type` (onsite/remote/hybrid), `start_year` required, `is_current`. |
| `WorkBullet` | `cv_work_bullets` | FK → WorkExperience (`bullets`). `text`, plus auto-derived `impact_metric` and `skills_demonstrated` (JSON list). |
| `Education` | `cv_education` | FK → CVProfile (`education_entries`). `degree_type` (bs/ms/phd/diploma/certificate/other), `cgpa` + `cgpa_scale`, `thesis_title`, `achievements`. |
| `SkillCanonical` | `cv_skill_canonical` | `canonical_name` **unique**, `aliases` JSON list, `category` (Languages/Frameworks/Databases/Tools/Concepts/Cloud/Soft Skills), `logo_url`, `is_popular`. |
| `CVSkill` | `cv_skills` | FK → CVProfile (`skills`); FK → SkillCanonical (**SET_NULL**). `proficiency`, `years_of_exp`, `is_featured`, `is_verified` (true iff canonical-matched). |
| `CVProject` | `cv_projects` | FK → CVProfile (`projects`). `tech_stack` JSON list (≤10, enforced in serializer), `is_ongoing`, `is_professional`. |
| `CVCertification` | `cv_certifications` | FK → CVProfile (`certifications`). |
| `CVLanguage` | `cv_languages` | FK → CVProfile (`languages`). `proficiency` (native/fluent/professional/basic). |
| `AISuggestionLog` | `cv_ai_suggestion_logs` | FK → CVProfile (`ai_suggestions`). One row per suggestion request: section, target id, input digest, model, token counts, the returned suggestions, and `accepted_index`. Credits are **counted from these rows** rather than decremented from a counter — a drifting counter is unrecoverable, a count can always be recomputed. |
| `CVUploadLog` | `cv_upload_logs` | FK → CVProfile (`upload_logs`). `parse_status`, `raw_extracted_text`, `ai_parsed_json`, field counters. **Model exists but nothing writes to it** — the upload endpoint and parse task are Steps 7–8. |

There are **no** `unique_together`, indexes, or check constraints anywhere in the migration. The only DB-level uniqueness in the CV schema is `SkillCanonical.canonical_name` and the `CVProfile.user` OneToOne.

### Services — [apps/cv_builder/services/](apps/cv_builder/services/)

Pure functions, no ORM writes. Business logic lives here, never inline in views.

- **`completion.py`** — `COMPLETE_THRESHOLD=75`, `SUMMARY_MIN_LENGTH=80`, `SKILLS_MIN_COUNT=5`. `calculate_section_completion()` returns booleans for `{contact, summary, experience, education, skills, projects}`; `compute_completion()` weights them **contact 25 / summary 10 / experience 25 / education 15 / skills 15 / projects 10**, caps at 100, returns `(score, score >= 75)`. `experience` requires ≥1 experience with ≥2 bullets. (The spec calls this file `completeness.py`; the real name is `completion.py`.)
- **`metric_extractor.py`** — `extract_metric(text)`, first match over 7 regexes (`180+ tests`, `54% to 93%`, `reduced X by 40%`, `$20k`, `3x faster`, `50+ clients`, `10+ engineers`). Synchronous. Returns `None` rather than fabricating.
- **`ai/`** — AI writing suggestions (see §16). `client.py` (one Claude call), `prompts.py`
  (constants, one per section), `context.py` (per-section user payload), `guardrails.py`
  (mechanical grounding checks), `schemas.py` (Pydantic structured-output models), `suggest.py`
  (one entry point per section).
- **`skill_detector.py`** — `extract_skills_from_bullet(text)`. Loads canonical names + aliases, sorts **longest-first** so "React Native" beats "React", caches for 3600 s, then does case-insensitive substring matching. Known false-positive risk ("Python" in "Monty Python"), acknowledged in the spec. Because no `CACHES` backend is configured, this cache is per-process and never invalidated when `SkillCanonical` changes.

### Shared helpers — [apps/cv_builder/utils.py](apps/cv_builder/utils.py)

- `get_user_cv_profile(user)` → `get_object_or_404(CVProfile, user=user)`. Used at the top of nearly every view.
- `normalize_profile_url(value)` → prepends `https://` unless already schemed.
- `reorder_owned_items(model, ordered_ids, owner_filter)` → inside `transaction.atomic()`, `.update(order=index)` per ID with the owner filter baked in, and **raises `ValueError` if any single ID matches 0 rows**, aborting the whole batch. This is the "never partial-reorder" contract shared by all six reorder endpoints.

### Serializers — [apps/cv_builder/serializers/](apps/cv_builder/serializers/)

Read/write split on `CVProfile`: `CVProfileCreateSerializer` (all read-only — the POST shell response), `CVProfileReadSerializer` (adds `section_completion`), `CVProfileWriteSerializer` (11 writable fields; `validate_linkedin_url` rejects non-linkedin.com hosts, all URL validators run `normalize_profile_url`).

Derived fields are always read-only and computed server-side: `WorkBulletSerializer` populates `impact_metric` and `skills_demonstrated` in `create()`/`update()` by calling the services; `CVSkillSerializer` takes a write-only `canonical_id` and, when it resolves, **overrides user-supplied `name`/`category` with the canonical values and sets `is_verified=True`**.

> `canonical_id` is write-only, so a client never learns it and cannot echo it back on update. `CVSkillSerializer.validate` therefore has an explicit branch: when updating a row that already has a canonical FK and no `canonical_id` is supplied, it re-derives name/category from the existing canonical and keeps `is_verified=True`. Without that branch, editing only a skill's proficiency silently downgraded a verified skill to unverified freetext. Keep the branch if you touch this serializer.

Silent corrections rather than errors, per spec: `is_current` nulls `end_month`/`end_year`. Cross-field validation rejects `cgpa > cgpa_scale`. Bullet `text` must be ≥10 chars after strip. `tech_stack` must be a list of ≤10 strings.

### Views — [apps/cv_builder/views/](apps/cv_builder/views/)

All plain `APIView` subclasses — **no ViewSets, no routers** — with explicit `permission_classes = [IsAuthenticated]`. Detail views expose only **PUT and DELETE**; there is no per-item GET and no PATCH on any child resource.

`views/project.py` defines a `_ReorderMixin` shared by the project/certification/language reorder views; the work-experience, bullet, education, and skill reorder views duplicate that logic inline instead.

### 6.6 Upload & AI parse (spec Steps 7–8, built 2026-09-07)

The one path in the module that ingests a user-supplied file. Design decisions and the full
edge-case analysis live in [docs/cv_upload_parse_plan.md](../docs/cv_upload_parse_plan.md); what
follows is the map.

```
POST /cv/upload/            validate → save → CVUploadLog(pending) → 202
  └─ extract_text_from_cv   pdfplumber / python-docx → 'scanned' if <100 chars (no API call)
      └─ send_to_ai_parser  structured-output Claude call → normalise → 'success' | 'partial'
GET  /cv/upload/{id}/status/  polled every 2s; requires_review is DERIVED per request
POST /cv/upload/{id}/retry/   re-runs stage 2 only; counts against the cap
POST /cv/upload/{id}/apply/   the ONLY writer of parsed data
```

**Three invariants, each with a test that will fail loudly if broken:**

1. **Nothing writes to the CV before apply.** Extraction, the AI call and normalisation are all
   read-only with respect to the CV. `test_cv_parse.py::test_nothing_is_written_to_the_cv_on_any_parse_path`
   guards it. This is the whole of the spec's overwrite protection — do not add a convenience save.
2. **Enum values cannot drift.** `services/ai/schemas.py` uses `Literal` types holding exactly the
   model choices, and structured outputs constrain generation to them, so the model *cannot* emit
   `"Permanent"` into `employment_type`. `test_parse_mapping.py::TestTheSchemaConstrainsVocabulary`
   asserts the literal sets equal the model choices; if you add a choice to a model, add it there.
3. **Missing required fields are asked about, never guessed.** `WorkExperience.start_year` and
   `Education.start_year` are NOT NULL and real CVs omit them (an education line usually prints only
   a graduation year). `services/parse_normalize.py` flags the row `needs_attention`; the diff modal
   collects one answer; apply refuses the row until it has one.

**Files:**

| File | Role |
|---|---|
| `serializers/upload.py` | File validation. Magic bytes (`%PDF-`, `PK\x03\x04`), not `content_type` — the client supplies that |
| `services/extraction.py` | PDF and DOCX to text. DOCX reads **table cells** as well as paragraphs; two-column CVs put half their content in a table |
| `services/ai/prompts.py::PARSE` | The mapping rules: headings by content not text, the Languages trap, unmapped sections, enum guidance |
| `services/ai/parse.py` | One call, its own token ceiling (`AI_PARSE_MAX_TOKENS`) and its own failure message |
| `services/parse_normalize.py` | Layer 2 — lengths, URL schemes, CGPA range, short bullets, date sanity, dedupe, the Languages guard |
| `services/apply_parsed.py` | Layer 3 — per-row savepoints, writes through the section serializers |
| `views/upload.py` | The four endpoints |

**Metering.** A parse costs several times a suggestion, so it has its own controls:
`cv_upload` throttle scope (5/hour) and `AI_PARSE_MONTHLY_LIMIT` (5), summed from
`CVUploadLog.parse_attempts` — summed, not counted, because a retry is a real metered call.

**The "Languages" trap.** A CV heading its programming languages "Languages" would otherwise store
`Python (native speaker)` as a spoken language. The prompt covers it and `parse_normalize` enforces
it: any `language_name` resolving to a canonical skill in the `Languages` category is moved to
skills, and the user is told in `payload['notes']`.

### Signals — [apps/cv_builder/signals.py](apps/cv_builder/signals.py)

`post_save` + `post_delete` on all seven child models funnel into `_touch_cv_profile(cv)`, which bumps `content_updated_at`, recomputes completion, and saves. This is how the parent stays in sync. `WorkBullet` routes via `instance.experience.cv`, costing an extra query per bullet write.

### Management commands & fixtures

- `python manage.py seed_skills` → loads `fixtures/canonical_skills.json`: **270 `SkillCanonical` records** with hard-coded UUID PKs (so re-running upserts safely). Categories: Tools 65, Frameworks 49, Concepts 45, Languages 35, Cloud 27, Soft Skills 26, Databases 23; 110 flagged `is_popular`.
- `python manage.py setup_cv_beat_tasks` → idempotently creates three `CrontabSchedule` + three enabled `PeriodicTask` rows.

**Neither runs automatically.** `entrypoint.sh` does not call them, so both are manual post-deploy steps and the CV Builder is non-functional without `seed_skills`.

---

## 7. Celery

[celery_app/celery.py](celery_app/celery.py) is the standard three-liner: `Celery('hireflow')` → `config_from_object('django.conf:settings', namespace='CELERY')` → `autodiscover_tasks()`.

`celery_app/__init__.py` is empty, which normally breaks `.delay()` from the web process — but here [config/__init__.py](config/__init__.py) carries `from celery_app.celery import app as celery_app` instead. Django imports the settings package on startup, so the configured app *is* instantiated and `.delay()` routes to Redis correctly. The app is simply registered from `config/` rather than the conventional `celery_app/`. **Not a bug — just non-standard placement.** Don't "fix" it by adding the import to `celery_app/__init__.py` without removing the other, or the app gets built twice.

### Beat schedule (all UTC, all in `apps/cv_builder/tasks.py`)

| Task | Schedule | Behavior |
|---|---|---|
| `send_draft_reminder` | daily 09:00 | Emails owners of `is_complete=False, reminder_sent=False` profiles whose `content_updated_at` falls in the **23–25 day** window; sets `reminder_sent=True` |
| `delete_stale_drafts` | daily 02:00 | Deletes `is_complete=False` profiles older than 30 days; removes `pdf_file` from storage first (logs and continues on failure), then CASCADE-deletes |
| `delete_orphaned_files` | Sundays 03:00 | Walks `MEDIA_ROOT/cv_uploads`, unlinks any file whose relative path is not in `CVUploadLog.file_path` |

Two operational caveats: the schedule only exists after someone runs `setup_cv_beat_tasks`; and in `docker-compose.yml` the `celery_worker`/`celery_beat` services mount **no `media_volume`**, so both file-touching tasks operate on an empty container-local `/app/media`.

---

## 8. Full API surface

Auth is the global `IsAuthenticated` default (Bearer access token in the `Authorization` header) unless noted.

### Root
| Method | Path | Auth | Purpose |
|---|---|---|---|
| GET | `/health/` | none | `{"status":"ok"}` liveness probe |
| — | `/admin/` | staff session | Django admin |

### Auth — `apps/accounts/urls.py::auth_urlpatterns`
| Method | Path | Auth | Purpose |
|---|---|---|---|
| POST | `/api/auth/register/` | AllowAny | Create user; queues verification email; **201 with a generic message, no tokens** |
| GET | `/api/auth/verify-email/<token>/` | AllowAny | Validate signed token (24 h), mark verified, return `{access}` + set refresh cookie (auto-login on verify) |
| POST | `/api/auth/login/` | AllowAny | Rejects inactive **and unverified** accounts; returns `{access}` + refresh cookie |
| POST | `/api/auth/logout/` | IsAuth | Blacklist the cookie refresh token, clear cookie |
| POST | `/api/auth/token/refresh/` | AllowAny | Reads refresh **from cookie, no body**; blacklists it, issues new cookie + `{access}` |
| POST | `/api/auth/forgot-password/` | AllowAny | Always 200 with identical copy (no user enumeration) |
| POST | `/api/auth/reset-password/` | AllowAny | `{token, new_password, new_password2}`, token max-age 1 h |
| POST | `/api/auth/google/` | AllowAny | `{access_token}` → Google userinfo → `{access}` + cookie |
| POST | `/api/auth/github/` | AllowAny | `{access_token}` → GitHub user → `{access}` + cookie |

### Users — `user_urlpatterns`
| Method | Path | Purpose |
|---|---|---|
| GET | `/api/users/profile/` | `UserProfile` + nested read-only `user` |
| PUT | `/api/users/profile/` | Update; accepts write-only `full_name` proxied onto `User`. Behaves as PATCH |
| POST | `/api/users/change-password/` | `{old_password, new_password, new_password2}` |

### CV Builder — `apps/cv_builder/urls.py` (all authenticated, all scoped to the caller's single CVProfile)
| Method | Path | Purpose |
|---|---|---|
| POST | `/api/cv/profile/` | Idempotent shell creation via `get_or_create`, prefilling `email`. **201 if created, 200 if it existed** |
| GET | `/api/cv/profile/` | Full profile + `section_completion` (404 if none) |
| PUT / PATCH | `/api/cv/profile/` | Full / partial update (PATCH is the autosave path) |
| DELETE | `/api/cv/profile/` | Deletes the CV; everything CASCADEs. 204. Re-create with POST |
| POST | `/api/cv/profile/reset/` | `{"sections": [...]}` clears those, omitted clears everything. Keeps the profile row, `template_id` and `email`. Returns `{cleared, total_cleared, profile}` |
| GET | `/api/cv/profile/completion/` | `{completion_score, is_complete, section_completion}` for the progress bar |
| GET / POST | `/api/cv/work-experience/` | List (prefetching bullets) / create |
| PATCH | `/api/cv/work-experience/reorder/` | `{ordered_ids:[...]}`, atomic all-or-nothing |
| PUT / DELETE | `/api/cv/work-experience/<uuid:pk>/` | Update / delete (cascades bullets) |
| GET / POST | `/api/cv/work-experience/<uuid:experience_id>/bullets/` | List / create — create runs metric + skill extraction |
| PATCH | `/api/cv/work-experience/<uuid:experience_id>/bullets/reorder/` | Reorder within one experience |
| PUT / DELETE | `/api/cv/work-experience/<uuid:experience_id>/bullets/<uuid:bullet_id>/` | Update (re-runs extraction) / delete |
| GET / POST · PATCH reorder · PUT/DELETE `<uuid:pk>` | `/api/cv/education/` | Same CRUD+reorder shape |
| GET | `/api/cv/skills/search/?q=` | Canonical autocomplete: name or alias `icontains`, ordered `-is_popular, canonical_name`, **capped at 20**; empty `q` → `[]` |
| POST | `/api/cv/skills/bulk-add/` | `{skills:[…]}` → `get_or_create` per item → `{added, skipped}` |
| GET / POST · PATCH reorder · PUT/DELETE `<uuid:pk>` | `/api/cv/skills/` | **Duplicate add returns the existing skill with 200**, not 400 |
| GET / POST · PATCH reorder · PUT/DELETE `<uuid:pk>` | `/api/cv/projects/` | Same shape |
| GET / POST · PATCH reorder · PUT/DELETE `<uuid:pk>` | `/api/cv/certifications/` | Same shape |
| GET / POST · PATCH reorder · PUT/DELETE `<uuid:pk>` | `/api/cv/languages/` | Same shape |

URL-ordering detail: `skills/search/`, `skills/bulk-add/`, and `skills/reorder/` are registered **before** `skills/` and `skills/<uuid:pk>/` so the literal segments aren't shadowed. Keep that ordering when adding routes.

### Module 1 — job match (keywords + cover letter), built 2026-09-09

| Method | Path | Notes |
|---|---|---|
| GET | `/api/cv/job-match/sources/` | Which CVs this user can match against — their built CV plus any upload that yielded text. Free; also returns the month's allowance |
| POST | `/api/cv/job-match/` | `{jd_text, source_type: profile\|upload, upload_id?}`. **The most expensive call in the product.** Throttled `job_match` (10/hour), capped `AI_JOB_MATCH_MONTHLY_LIMIT` (20/month) |
| GET | `/api/cv/job-match/` | History, without `cover_letter`/`jd_text` |
| GET | `/api/cv/job-match/{id}/` | One result in full. Free — the letter written Monday is wanted Thursday |
| DELETE | `/api/cv/job-match/{id}/` | **Soft delete.** The row survives so the month's count does; a hard delete would make "delete and re-run" an unlimited-usage bypass |

**Three invariants:**

1. **Nothing is written to the CV.** A match is an opinion plus a letter; acting on
   either is the user's own manual edit. Same line the import holds.
2. **The CV is sent whole, never truncated.** `context.build_full_cv_text()` exists
   precisely because the other context builders cap roles and bullets — and here a
   cut CV makes real skills look missing, so the feature would ask the user whether
   they have a skill their own CV lists. Truncation invents gaps.
3. **Keywords come back in three separate buckets** — `matched` / `reworded` /
   `missing`. That is the Evidenced / Ask-first / Never model applied to job
   keywords, and it is the whole reason this is not a tool for lying on a CV.
   `reworded` ("Postgres" → "PostgreSQL") is where most of the real value is.

**`match_score` is keyword alignment, not a prediction of being interviewed** —
nothing here has the applicant pool or the callback history, and the field name and
UI copy both say so. See [docs/job_match_rnd.md](../docs/job_match_rnd.md) §4.

Named `JobMatch`, not `Application`, to leave that word free for the Kanban tracker.

### Upload & AI parse — built 2026-09-07

| Method | Path | Notes |
|---|---|---|
| POST | `/api/cv/upload/` | multipart `file`. 202 `{log_id, status}`. Throttled `cv_upload`; monthly cap checked **before** the file is written |
| GET | `/api/cv/upload/{log_id}/status/` | Polled every 2s. Adds `requires_review`, `parsed_data`, `existing_data` once terminal-successful. `requires_review` is derived per request, never stored |
| POST | `/api/cv/upload/{log_id}/retry/` | Re-runs the AI stage on already-extracted text. 400 if there is none, 409 unless status is `failed`/`partial`. Counts against the cap |
| POST | `/api/cv/upload/{log_id}/apply/` | `{choices: {section: keep\|replace\|merge}, answers: {section: {index: {field: value}}}}`. The only writer. 409 if already applied. Returns `{imported, skipped[], notes[]}` |

### Templates & PDF (built 2026-08-18)

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/cv/templates/` | Registry: id, name, description, columns, ats_safe, photo, max_pages |
| GET | `/api/cv/preview/?template=<id>` | `application/pdf` inline — the rendered CV. Sends `ETag` + `Cache-Control: private, must-revalidate` and `X-CV-Page-Count`; honours `If-None-Match` with a 304 |
| GET | `/api/cv/preview/meta/?template=<id>` | `{page_count, max_pages, overflows}` |
| POST / DELETE | `/api/cv/photo/` | Upload / clear the CV photo (multipart) |

**Preview and download are the same bytes.** `services/pdf_renderer.render_cv_pdf()` is the only
render path; both endpoints return its output from the same Redis cache entry, differing only in
`Content-Disposition`. Never add a second renderer — a browser-side HTML preview would diverge
from the PDF on line breaks and therefore page breaks.

#### The render pipeline (rebuilt 2026-08-19 for the live preview)

The preview now re-renders on every section save, so three things stand between the frontend and
WeasyPrint. All three fail *silently* if broken — no error, just staleness or load — which is why
they have tests (`tests/test_preview_cache.py`, `test_preview_etag.py`, `test_preview_singleflight.py`).

`build_render_plan(cv, template_id)` resolves the template, builds the context and derives a digest
**without rendering**. A view can therefore answer `If-None-Match` from the digest alone.

1. **Content-addressed cache key.** The digest is `sha256(template_id + json(context))`, excluding
   the static `template` dict. It used to hash `content_updated_at`, which is `auto_now` — so the
   `template_id` PATCH the picker fires on every click invalidated the render for *every* template.
   Narrowing that field is not an option: `send_draft_reminder` and `delete_stale_drafts` both read
   it, so a user browsing templates would start getting deletion reminders.
2. **Single-flight lock.** `cache.add(lock_key, ...)` is set-if-absent (atomic in Redis). Losers
   poll for the winner's cache entry for ~2s, then render anyway rather than deadlock. With four
   workers, three rapid saves must cost one render, not three.
3. **ETag / 304.** The digest is the ETag. `Cache-Control` is `private` — this is one user's CV and
   a shared proxy must never hold it.

`resolve_template_id()` in the registry gives the id *after* the default fallback, so an unknown id
and an explicit `minimal` share one cache entry.

Gunicorn runs `--workers 4` (was 2) so preview renders do not contend with the form's own saves.
That lives in `Dockerfile`, not compose — `Dockerfile.dev` uses `runserver`, which is threaded, so
dev concurrency does not resemble prod.

Six templates live in `templates/cv_templates/`, resolved through
[templates_registry.py](apps/cv_builder/templates_registry.py) — **an allowlist, never string
interpolation into a path**. `minimal`, `classic`, `technical`, `compact` are one-column and
ATS-safe; `modern` (two-column sidebar, not ATS-safe) and `executive` (header band, ATS-safe) are
the only two with a photo. `_sections.html` holds the shared body markup; each template supplies
its own CSS for the same class names.

Photo handling in `serializers/photo.py`: validates by decoding, 2 MB cap, re-encodes to 600×600
JPEG which **strips EXIF** (phone photos carry GPS, and a CV gets emailed to strangers). The
context builder passes a `file://` URI, not `photo.url` — `MEDIA_URL` gives a leading-slash path
that resolves against the filesystem root, so WeasyPrint would silently render no image.

Overflow is measured, not estimated: `len(document.pages)` from the laid-out document. Nothing is
ever truncated — the UI warns instead.

**Specified but not implemented:** `POST /api/cv/upload/`, `GET /api/cv/upload/{log_id}/status/`, `POST /api/cv/upload/{log_id}/apply/`, `POST /api/cv/export/pdf/`, `GET /api/cv/export/status/`, `GET /api/cv/export/download/`.

---

## 9. Migrations

| File | Contents |
|---|---|
| `apps/accounts/migrations/0001_initial.py` | `User`, `UserProfile` |
| `apps/cv_builder/migrations/0001_initial.py` | All ten CV tables (swappable dependency on `AUTH_USER_MODEL`) |
| `apps/cv_builder/migrations/0002_cvprofile_photo_alter_cvprofile_template_id.py` | `CVProfile.photo`, template choices |
| `apps/cv_builder/migrations/0004_aisuggestionlog.py` | `AISuggestionLog` |
| `apps/cv_builder/migrations/0003_cvprofile_template_id_default.py` | Backfills NULL `template_id`, then makes it non-null with `default='minimal'` — the live preview always has a template to render, so "none chosen yet" is not a state anything handles |

Ten tables, and no `AddIndex`/`AddConstraint`/`unique_together` operations anywhere. The three other installed apps have no migrations directory (they have no models).

---

## 10. Environment variables

Names only — real values live in `.env`, which is gitignored and must never be committed or pasted into a prompt. Use a vault reference for anything non-local.

**Required** (no default in settings; startup fails without them): `SECRET_KEY`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`.

| Group | Variables |
|---|---|
| Django | `SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS` |
| Postgres (container init) | `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD` |
| Postgres (Django) | `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT` |
| Redis / Celery | `REDIS_URL` *(declared in `.env.example` but never read by settings)*, `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND` |
| Frontend / CORS | `FRONTEND_URL`, `VITE_API_URL`, `VITE_GOOGLE_CLIENT_ID`, `CORS_ALLOWED_ORIGINS` |
| Email | `EMAIL_BACKEND`, `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_USE_TLS`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `DEFAULT_FROM_EMAIL` |
| Google OAuth | `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET` *(currently unused server-side — the backend verifies provider access tokens rather than doing a code exchange)* |
| Compose-injected | `COLLECT_STATIC` (set to `"true"` on the `backend` service only) |

No GitHub OAuth variables are defined even though `/api/auth/github/` is wired up.

---

## 11. Running it

**Docker (dev)**, from repo root:
```bash
cp .env.example .env      # then fill in real values
docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build
```
App at `http://localhost`, API direct at `:8000`, Vite at `:5173`, admin at `/admin/`, health at `/health/`. Postgres is host-mapped to **5433**. Migrations run automatically via `entrypoint.sh`.

**Docker (prod):** `docker compose up --build -d` — gunicorn (2 workers) + the built React bundle served by nginx.

**Required manual post-deploy steps** (the entrypoint does not do these):
```bash
docker compose exec backend python manage.py seed_skills          # 270 canonical skills
docker compose exec backend python manage.py setup_cv_beat_tasks  # 3 periodic tasks
docker compose exec backend python manage.py createsuperuser
```

**Local, no Docker:** a gitignored `backend/venv/` already exists. Activate it, `pip install -r requirements.txt`, point `DB_HOST=localhost` / `DB_PORT=5433` and the Celery URLs at `localhost:6379`, then `python manage.py migrate && python manage.py runserver`, with the worker and beat in separate shells.

**Testing:** there is none. Every `tests.py` is 0 bytes and no runner is configured. The de facto suite is `docs/postman/HireFlow_CV_Builder.postman_collection.json` — ~45 requests in 9 ordered folders covering the Steps 2–6 surface, with a login script that auto-captures `{{access_token}}`. It does not cover register/verify/refresh/social/password flows.

---

## 12. Conventions to follow

1. **Cookie-based refresh, in-memory access token.** The refresh token lives only in an HttpOnly `SameSite=Lax` cookie; the access token goes in the response body and is held in Redux client-side. The refresh endpoint reads no body at all.
2. **Plain `APIView` everywhere** — no ViewSets, no routers, explicit methods, hand-written URL paths. Verbose but legible; match it.
3. **Modular packages over god-files** in `cv_builder`: one model/serializer/view module per domain with an `__init__.py` barrel.
4. **Service layer for business logic.** Scoring, metric extraction, and skill detection are pure functions in `services/`, called from models and serializers — never inline in views.
5. **Ownership by queryset filtering, not object permissions.** Everything funnels through `get_user_cv_profile(user)` or a `cv__user=request.user` filter, so a cross-user ID yields 404 rather than 403. (`permissions.IsCVOwner` was written but is imported nowhere — dead code.)
6. **Read/write serializer split**, with derived fields always read-only and computed server-side.
7. **Signal-driven denormalization** keeps `content_updated_at` and `completion_score` fresh; scoring is never cached.
8. **Centralized message constants** in `accounts/errors.py` instead of inline strings.
9. **Idempotent mutations by design:** profile POST, skill POST, bulk-add, `seed_skills`, and `setup_cv_beat_tasks` are all safe to re-run.
10. **Atomic all-or-nothing reorders** via the shared `reorder_owned_items` helper.
11. **UUID PKs + explicit `db_table`** on every model, to prevent ID enumeration.
12. **Django signed tokens** (`core.signing`, distinct salts) for verification and reset — stateless, max-age enforced at the view.
13. **Non-enumerating auth responses** on register and forgot-password.

---

## 13. Known loose ends

Ordered by impact.

1. ~~**`normalize_profile_url` is dead code for scheme-less input.**~~ **Fixed 2026-09-08.** `SchemelessURLField` in [serializers/cv_profile.py](apps/cv_builder/serializers/cv_profile.py) normalizes inside `to_internal_value()`, before validation, so `"linkedin.com/in/you"` is accepted by the API rather than only by the frontend's own `toAbsoluteUrl`. This also closed a real inconsistency: the CV import already accepted scheme-less URLs, so the same value got two answers depending on the endpoint. `project_url` and `credential_url` still have no normalization — they take the same field if it becomes a problem.
2. **`seed_skills` / `setup_cv_beat_tasks` are not automated** — a fresh deploy has no canonical skills and no beat schedule.
3. ~~**`skill_detector`'s cache is never invalidated**~~ **Fixed 2026-09-08.** A `post_save`/`post_delete` receiver on `SkillCanonical` drops the index, so a freshly seeded skill is detectable immediately rather than up to an hour later.
4. ~~**`celery_worker` / `celery_beat` have no `media_volume` mount**~~ **Fixed 2026-09-08, and it had become a launch blocker.** Low impact while only the cleanup tasks touched files; once Step 7 shipped, `extract_text_from_cv` runs in the worker and opens the uploaded CV from `MEDIA_ROOT`, so without the mount *every upload failed* with a misleading "this PDF could not be read".
5. **No DB-level uniqueness on `CVSkill (cv, name)`** — concurrent adds can slip past the application-level `get_or_create`.
6. **`LogoutView` requires a live access token**, so an expired session cannot clear or blacklist its refresh cookie.
7. **No logging config and no OpenAPI schema.** (Tests now exist for `cv_builder` — see §14.)
8. Deprecated allauth 65 setting names at `settings.py:163-166`.
9. Empty `config/asgi.py`; no `backend/apps/__init__.py` (works only via PEP 420 namespace packages).
10. `apps.applications` / `apps.notifications` exist on disk but are not in `INSTALLED_APPS`.
11. `NotFound` imported but unused in `views/cv_profile.py`; `permissions.py` entirely unused.
12. **`extract_metric` does not read spelled-out numbers** ("a team of four engineers"). Deliberate — parsing English numerals is a separate job, and the AI asking for the figure is the right outcome. Pinned by a test so it stays a decision.
13. **No frontend test harness.** The import modal, the polling hook and the reset UI have no automated coverage; `frontend/node_modules` is currently a root-owned empty directory, so even `npm ci` needs sudo to fix.

### Fixed in the 2026-09-08 audit

Two of these were silently corrupting data on every write and neither had a test:

- **`skill_detector` matched substrings.** 27 canonical skills are 1–2 characters, so every bullet was tagged `R`, most also `C`, and "Managed relationships with 30 enterprise clients" returned `['PS','sh','TS','C','R']`. One mention of PostgreSQL returned four entries. Now identifier-aware boundary matching with alias→canonical de-duplication ([test_extractors.py](apps/cv_builder/tests/test_extractors.py)).
- **`extract_metric` missed most real metrics** — no generic percentage pattern, so "Cut latency by 40%" returned `None`. Because `guardrails.wants_a_metric()` inverts it, the AI was asking users for a number their bullet already contained.

---

## 14. Tests (added 2026-08-19)

This is the repo's first test suite. `pytest` + `pytest-django`, config in
[backend/pytest.ini](pytest.ini), fixtures in [backend/conftest.py](conftest.py), tests in
`apps/cv_builder/tests/`. The other apps still have empty `tests.py` files.

```
docker compose exec backend pytest apps/cv_builder/tests/          # 50 tests, ~30s
docker compose exec backend pytest apps/cv_builder/tests/ -m "not slow"   # 38 tests, ~24s
```

Three things about this harness are load-bearing:

- **`pytest_configure` repoints `CACHES` at Redis db 3** (0 broker, 1 results, 2 app cache). Django
  swaps the *database* name for tests automatically but not Redis, so without this the suite writes
  into the running app's cache and leaks state between tests — and the single-flight test would
  pass for the wrong reason. An autouse fixture flushes the cache either side of every test.
- **`test_preview_singleflight.py` needs `django_db(transaction=True)`.** The default test case
  wraps each test in a transaction other threads cannot see, so a threaded test either deadlocks or
  renders an empty CV. Each worker thread calls `connection.close()` or the post-test truncation
  blocks.
- **Renders cost ~250-360ms each.** The `sample_cv` fixture is deliberately minimal, and the
  six-template sweeps are marked `slow` so they can be deselected. Keep it that way or people stop
  running the suite.

`testpaths = apps` matters too: a checked-out `backend/venv/` sits in the tree and its site-packages
are full of third-party test modules that would otherwise be collected.

---

## 15. Where to look next

- Spec and rationale for everything CV-related: [docs/cv_builder_spec.md](../docs/cv_builder_spec.md) (1263 lines; Steps 7–10 contain the upload/AI-parse/PDF-export designs, including the 5 MB cap, `get_valid_filename` path-traversal guard, scanned-PDF detection, the Claude prompt contract demanding `null` over fabrication, and the diff/overwrite-protection flow so an upload never silently clobbers existing data).
- Frontend counterpart: [frontend/context.md](../frontend/context.md). The CV Builder UI (spec Step 10) is now built against this API — if you change a serializer field, choice value, or route here, update `frontend/src/features/cvBuilder/` in the same change. The frontend mirrors the choice values in `features/cvBuilder/constants.js` and the validation rules in `features/cvBuilder/schemas/cvSchemas.js`; both are the first places to break when the backend contract moves.
