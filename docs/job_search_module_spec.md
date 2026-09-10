# Module 2 — Find Matching Jobs (SPEC ONLY — NOT BUILT)

> Stored 2026-09-09 from the product owner's spec, so the design is not lost while
> Module 1 is built. **Nothing here is implemented and nothing should be built from
> it until it is finalised.**
>
> Module 1 (job match + keywords + cover letter) is being built first and is
> deliberately independent of this — it takes a pasted job description, so it works
> with or without this module ever existing.

---

## 1. The spec as given

**User flow.** User enters a job title + location, or clicks "use my CV to find
jobs" (the smarter option). The backend queries **our own database** — this is the
important part: **we do not scrape live per user request.** We fetch once daily
into our DB and serve from the DB.

```
1. User searches: title="Backend Developer", location="Karachi"
2. Backend queries the `jobs` table with text search + filters
3. For each candidate job, compute a similarity score:
     cosine_similarity(user.cv.embedding, job.embedding)
4. Return the top 20–50 sorted by match score
5. Frontend shows job cards: title, company, location, match score,
   "View" and "Apply on original site"
```

**Two actions per card:**

- **"Tailor CV for this"** → jumps into Module 1 with the job description pre-filled.
- **"Apply"** → opens the source URL in a new tab. We do **not** handle the
  application itself; they apply on rozee.pk / Greenhouse / wherever it originated.

**Exit.** The user either downloads a tailored CV (Module 1 exit) or is redirected
to the original posting (Module 2 exit). The job is done: get them to the interview
stage.

## 2. The daily background job

The jobs table does not fill itself. A daily cron (3am; free tier on an Oracle
Cloud VM or GitHub Actions):

```
1. FOR EACH company in `tracked_companies` (~500):
     - detect ATS platform (Greenhouse / Lever / Ashby / Workable)
     - hit their public JSON endpoint (no auth, free)
     - parse, dedupe by external_id, upsert into `jobs`

2. Adzuna free API (budget: 1000 calls/month)
     - query key titles for target markets, upsert

3. Playwright script for Rozee.pk
     - ~10–20 category pages for Pakistan jobs
     - rate limit: 3 seconds between requests
     - parse and upsert

4. Compute an embedding for each NEW job
5. Delete jobs older than 45 days
```

Roughly 20–30 minutes per run, no paid APIs, thousands of fresh jobs per day.

## 3. Data model as given

```
users             (id, email, name)
cvs               (id, user_id, raw_text, structured_json, embedding)
applications      (id, user_id, cv_id, jd_text, tailored_cv_json, cover_letter, match_score)
jobs              (id, source, external_id, title, company, location, remote_type,
                   description, apply_url, posted_at, embedding, created_at)
tracked_companies (id, name, ats_platform, ats_slug)   ← seeded once
```

---

## 4. Notes to settle before this is built

Recorded now, while the reasoning is fresh. None of these block Module 1.

**The scrape-daily-into-our-DB decision is right**, and for a reason worth writing
down: it is also what keeps us on the right side of the ATS platforms. A few
hundred polite daily requests to documented public endpoints is a completely
different act from per-user live fetching, which would multiply with traffic.

**Rozee.pk needs its own check.** Greenhouse, Lever, Ashby and Workable publish
documented public JSON APIs — that path is clear. Rozee is a Playwright scrape of a
site that has not offered us anything, so its terms need reading before that step
is written, exactly as we concluded for LinkedIn. See
[job_match_rnd.md](job_match_rnd.md) §3.

**Embeddings mean a vector column.** Postgres needs `pgvector`, which is a new
extension in the Docker image and a migration. Worth confirming the free embedding
model's licence and rate limits before committing to it. A cheaper v1: Postgres
full-text search plus the keyword resolution Module 1 already does, with embeddings
added when ranking quality actually demands it.

**`applications` collides with the planned Kanban tracker.** The spec's
`applications` table is "a tailoring attempt"; the tracker module's `applications`
is "a job I applied to and am tracking". These are different things and must not
share a name. Module 1 therefore stores its results as **`JobMatch`** in
`cv_builder`, leaving `applications` free for the tracker.

**`cvs` (plural per user) is the `CVVersion` decision** flagged three times now —
in the AI suggestions R&D, the applications R&D, and
[job_match_rnd.md](job_match_rnd.md) §6. This spec assumes it exists. Module 1 works
around it for now by letting the user pick between their HireFlow CV and any CV
they have previously uploaded, but the decision is still owed.

---

## 5. Split into two days

Divided on the one hard dependency in this module: **you cannot search jobs that
are not in the database yet.** So the pipeline comes first and the user sees
nothing on day one — which is fine, because it is fully testable on its own.

### Day 1 — Fill the database (no UI)

Everything that puts jobs in our own tables, on a schedule.

| # | Work |
|---|---|
| 1 | `Job` and `TrackedCompany` models + migrations. `Job` unique on `(source, external_id)` so re-running the fetch upserts instead of duplicating |
| 2 | One fetcher per ATS — Greenhouse, Lever, Ashby, Workable. All public JSON, no auth, no keys. Each returns a normalised dict; the differences stay inside the fetcher |
| 3 | The daily Celery Beat task: loop tracked companies → fetch → normalise → upsert → delete jobs older than 45 days |
| 4 | Seed `tracked_companies` (name, ats_platform, ats_slug), plus a `fetch_jobs` management command so it can be run by hand |
| 5 | Politeness and safety: request timeouts, rate limiting between calls, one company failing must not kill the run |
| 6 | Tests — all HTTP mocked, no live calls in the suite |

**Done when:** `python manage.py fetch_jobs` fills the table from real companies,
running it twice adds nothing, and the beat entry is registered.

### Day 2 — Let people find and use them (all user-facing)

| # | Work |
|---|---|
| 1 | Search endpoint: title + location + remote/onsite filters, Postgres full-text over title and description, paginated |
| 2 | "Use my CV to find jobs" — rank by the skills already on their CV, reusing the canonical resolver Module 1 uses |
| 3 | Frontend job list + cards: title, company, location, match, posted date |
| 4 | **"Tailor CV for this"** → opens Module 1 with the job description already filled in. This is the join between the two modules and the reason Module 1 was built first |
| 5 | **"Apply"** → opens the original posting in a new tab. We never handle the application |
| 6 | Empty and stale states — no results, nothing fetched yet, job since removed |
| 7 | Tests |

**Done when:** a user can search, see ranked jobs, click through to tailor one, and
click out to apply.

### What is deliberately not in either day

- **Embeddings and `pgvector`.** The spec ranks by cosine similarity, which needs a
  new Postgres extension, a migration, an embedding provider and a cost per job.
  Day 2 ranks with full-text search plus the canonical skill matching we already
  have and have tested. If ranking quality is visibly poor, embeddings become their
  own piece of work with a real before/after to judge it against — rather than
  three new dependencies added on a guess.
- **Rozee.pk.** Its terms need reading first (§4). It is a Playwright scrape of a
  site that has published nothing for us, unlike the ATS platforms. Keeping it out
  of day 1 means the pipeline ships without waiting on that answer.
- **Adzuna.** Needs an account and an API key, which is an action outside the code.
  Slots into day 1 as one more fetcher the moment the key exists.

### Needed before day 1 starts

- The list of companies to track. The pipeline is worth nothing without it, and it
  is a judgement call about the target market rather than a technical one — start
  with 50 real ones rather than a placeholder 500.
