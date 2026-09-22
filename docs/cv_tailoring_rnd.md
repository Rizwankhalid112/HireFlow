# CV Tailoring — R&D

**Status:** built and tested. Phases 1 and 2 are implemented; §12's
remaining open question is decision 4.
**Supersedes:** the `CVVersion` sketch in `job_match_rnd.md` §6, which this settles.

---

## 1. What we are building

The flow, as specified:

1. Read the **exact CV the user uploaded** — not a reconstruction of it.
2. Show the **score**.
3. Next step: show the **keywords**.
4. If the user clicks **Accept**, replace *his wording* with *the job's wording*
   — **the specific words only, never the whole CV**.
5. **Do not change his template.**
6. **Nothing happens until he decides.**
7. Save the **CV and the job description** together.
8. A **storage room**: after applying to 50 jobs he returns, finds the company
   name, and opens the exact CV we tailored for that job to revise before the
   interview.

Two properties carry the whole design. The first is that this is a **surgical
edit, not a rewrite** — the output must be recognisably his document. The second
is that the archive is **per job**, which is the requirement `CVProfile` cannot
express, because it is one row per user and mutable.

---

## 2. What we already have

More than expected. The analysis half is built and tested.

| Piece | Where | State |
|---|---|---|
| Score + keyword analysis | `services/ai/job_match.py` | **Done.** Verified live: 65 for a relevant CV, 0 for an irrelevant one |
| The three keyword buckets | `services/ai/schemas.py` | **Done.** `matched` / `reworded` / `missing` |
| Per-match record | `models/job_match.py` | **Done.** Stores `jd_text`, `job_title`, `company`, `match_score`, all three keyword lists, `cover_letter` |
| Which CV was scored | `services/cv_sources.py` | **Done.** Built CV or any upload, resolved safely per user |
| Original uploaded file | `CVUploadLog.file_path` | **Retained** — this is what makes a surgical edit possible at all |
| PDF rendering | `services/pdf_renderer.py` | **Done.** 6 templates, 5 ATS-safe, content-addressed cache, single-flight lock |
| "Nothing is applied automatically" | `views/job_match.py` | **Done**, and stated in the module docstring |

**`JobMatch` is already most of the storage room.** It records the job title,
the company, the job description text and the analysis, keyed to the user. What
it does not hold is the tailored document itself.

### 2.1 The `reworded` bucket is the feature

This already exists and is the highest-value, lowest-risk edit available:

```python
class KeywordRewrite(BaseModel):
    keyword: str           # "PostgreSQL"  — the job's wording
    current_wording: str   # "Postgres"    — what the CV says
    where: str             # "Skills and Experience sections"
```

Verified live against a real CV and posting: it correctly found
`Postgres → PostgreSQL` and `Amazon Web Services → AWS`. ATS matching is largely
literal, so these cost real interviews, and fixing them **invents nothing** —
which is why this is the bucket we are allowed to auto-apply at all.

`missing` is never applied. It is a question, and applying it would mean writing
a claim the user has to defend in an interview.

---

## 3. The decision that has now been deferred three times

`job_match_rnd.md` §6 is blunt about it: the AI-suggestions R&D parked it, the
applications R&D parked it again, and it "cannot be deferred a third time".

The tension: **the product needs a different CV per job; `CVProfile` is one row
per user and mutable.** Editing `CVProfile` to tailor for a job would corrupt the
master CV and every previously tailored version at once.

**Decision: build `CVVersion`** — a frozen snapshot of CV content plus the job it
was tailored for. The master stays the single source of truth and is never
written to by this feature.

```
CVProfile (master, mutable, one per user — untouched by tailoring)
    └── CVVersion (frozen, one per tailored application)
            ├── the job it was tailored for
            ├── what was changed, and what it was changed from
            └── the document itself
```

This also settles the applications module's open "which CV did I send to this
job" question for free — a good sign it is the right shape.

---

## 4. The hard problem: "replace his wording, don't change his template"

This has three genuinely different answers depending on what he uploaded, and
being honest about the third is the point of this document.

### 4.1 CV built in HireFlow ✅ solved

We hold structured content and he has chosen a template. Replace the string in
the specific field, re-render through **his existing template**. Template
unchanged, layout unchanged, only the words differ.

No new capability required. `pdf_renderer.py` already does everything.

### 4.2 Uploaded DOCX ✅ solvable

`python-docx` is already a dependency. A Word document stores text in *runs*, and
formatting lives on the run — so replacing the text of a run **preserves font,
size, weight, colour and position exactly**. This is true in-place editing of his
document.

One real complication: **Word splits a word across runs** at any formatting or
spell-check boundary, so "Amazon Web Services" can be stored as three separate
runs and a naive run-level search misses it entirely.

**Proven, not assumed.** Both cases were tested against real `python-docx`
documents before writing this:

| Case | Result |
|---|---|
| Replacement inside one run (`Postgres` → `PostgreSQL`) | **PASS** |
| Replacement spanning three runs (`Amazon ` + **`Web`** + ` Services` → `AWS`) | **PASS** |
| Bold, italic, size and colour after the edit | **PASS** — unchanged |

The algorithm: concatenate a paragraph's run text, find the match on a word
boundary, then write the replacement into the first overlapping run and clear the
matched span from the rest.

```python
def replace_in_paragraph(par, old, new):
    runs = par.runs
    full = ''.join(r.text for r in runs)
    m = re.search(rf'\b{re.escape(old)}\b', full)
    if not m:
        return False
    start, end = m.span()
    pos, done = 0, False
    for r in runs:
        rs, re_ = pos, pos + len(r.text)
        if re_ > start and rs < end:              # this run overlaps the match
            head = r.text[:max(0, start - rs)]
            tail = r.text[max(0, end - rs):] if re_ > end else ''
            r.text = head + ('' if done else new) + tail
            done = True
        pos = re_
    return True
```

Still needs extending to tables, headers and footers, and multiple occurrences
per paragraph — but the mechanism is confirmed to work and to preserve
formatting exactly.

### 4.3 Uploaded PDF ❌ this is the one that does not work cleanly

**No PDF-writing library is installed** — no PyMuPDF, no pikepdf, no reportlab.
`pdfplumber` reads only; WeasyPrint renders HTML *to* PDF and cannot edit one.

Adding PyMuPDF would make it *possible* and still not make it *safe*:

- **Text is not stored as words.** It is positioned glyph runs. "Postgres" may be
  several fragments with explicit kerning between them.
- **Replacement changes width.** "Postgres" (8 chars) → "PostgreSQL" (10) is
  wider, and PDF has no reflow — the longer word overlaps whatever follows it.
- **Fonts are usually subset.** The embedded font often contains only the glyphs
  the document already uses. A replacement needing a glyph that was never
  embedded renders as a blank box or silently falls back to a different face —
  visibly wrong on the one document the user will show an employer.

The redaction-annotation technique (`add_redact_annot` + `apply_redactions`)
works for same-length or shorter replacements and degrades badly otherwise.

**Recommendation: do not attempt in-place PDF editing.** For a PDF upload, offer
the change list plus one of the fallbacks in §8, and say plainly why.

---

## 5. Is the rewrite data precise enough to apply?

Nearly. One schema change is required.

`where` is free text — *"Skills and Experience sections"* — which is fine to show
a human and useless for locating an edit. But **`current_wording` is the exact
string**, so the edit is a literal, word-boundary-anchored find-and-replace. That
is precise enough, with three guardrails:

1. **Verify before applying.** If `current_wording` is not found verbatim in the
   document, skip that rewrite and report it as not applied. Never fuzzy-match —
   a near-miss edit on someone's CV is worse than no edit.
2. **Word boundaries only.** Replacing `Postgres` must not corrupt an existing
   `PostgreSQL` into `PostgreSQLSQL`.
3. **Count and show every occurrence.** The user approves a specific set of
   changes, so the count has to be known before he accepts, not discovered after.

Schema addition: `occurrences: int` and an `applied` / `skipped_reason` result per
rewrite, so the confirmation screen and the stored record agree.

---

## 6. Storage — a blocker that also affects the feature we already shipped

`MEDIA_ROOT = BASE_DIR / 'media'`, i.e. **local disk**. Render's free tier
filesystem is **ephemeral**: it is wiped on every deploy and restart.

Consequences:

- **Today:** uploaded CV files are already being lost. The current upload flow
  survives it only because it extracts the text immediately into the database and
  never reads the file again.
- **For tailoring:** we must re-open the original file to edit it, so the file
  genuinely has to persist.
- **For the storage room:** a user returning after 50 applications to find his
  tailored CVs missing is the feature failing at exactly the moment it matters.

**This must be fixed before the storage room is worth building.** Options:

| Option | Cost | Notes |
|---|---|---|
| Cloudflare R2 | Free to 10 GB | S3-compatible, no egress fees. **Recommended** |
| Backblaze B2 | Free to 10 GB | S3-compatible |
| Render persistent disk | Paid tier | Simplest change, but not free and ties storage to one host |
| Store the DOCX bytes in Postgres | Free | Works at our size; unusual, and bloats the database |

With `django-storages` this is a settings change, not an application change.

---

## 7. What changes

### 7.1 Data model

**New — `CVVersion`** (the frozen tailored CV):

| Field | Purpose |
|---|---|
| `cv` → CVProfile | Owner |
| `job_match` → JobMatch | The analysis it came from |
| `company`, `job_title` | Denormalised so the storage room lists without a join |
| `source_type` | `profile` / `upload` — how it was produced |
| `content_json` | Frozen content, for a CV built in HireFlow |
| `template_id` | The template *he* chose, frozen with it |
| `file` | The tailored DOCX/PDF, for an uploaded CV |
| `applied_rewrites` | Exactly which words were changed, and from what |
| `created_at` | Ordering for the storage room |

**Changed — `JobMatch`:** add `cv_version` (reverse pointer) and keep everything
else. `jd_text` is already stored, which is half of requirement 7.

**Unchanged — `CVProfile`.** Tailoring never writes to the master.

### 7.2 New service

`services/tailor.py` — one entry point per source type:

- `tailor_profile(profile, rewrites)` → frozen content JSON + PDF via his template
- `tailor_docx(upload, rewrites)` → edited DOCX preserving all formatting
- `tailor_pdf(...)` → **not implemented**; returns the change list (§4.3)

Shared: the verify-then-replace guardrails from §5.

### 7.3 API

| Endpoint | Purpose |
|---|---|
| `POST /api/cv/job-match/{id}/tailor/` | Accept a chosen subset of rewrites, produce a `CVVersion` |
| `GET /api/cv/versions/` | The storage room — company, job title, date, score |
| `GET /api/cv/versions/{id}/` | One tailored CV with its change list and its job description |
| `GET /api/cv/versions/{id}/download/` | The file |
| `DELETE /api/cv/versions/{id}/` | Remove one |

Tailoring costs **no AI call** — the analysis already happened. It is a text
operation, so it is not metered and not throttled. Worth stating because it means
the storage room is cheap to use.

### 7.4 Frontend

- **Job Match result** — the `reworded` list becomes a checklist, each row
  showing `Postgres → PostgreSQL`, where it appears, and how many times. All
  checked by default, every one unticking individually. One **Accept & tailor**
  button. This is step 4 of §1 and the "until he decides" requirement.
- **New — Storage room** (`/my-cvs`): cards by company, showing job title, score,
  date, and the number of changes applied. Opens to the tailored CV, its change
  list, and the job description it was tailored for.

---

## 8. PDF uploads — the options, to be decided

Since §4.3 rules out in-place PDF editing, one of these is needed:

1. **Ask for the DOCX.** "Upload the Word version and we'll tailor it directly."
   Most people have it. Honest, zero risk, no new dependency.
2. **Offer the change list.** Show exactly what to change and where; he edits his
   own file. Always available, useful as the universal fallback.
3. **Rebuild through a HireFlow template.** We already parse uploaded CVs into
   structured content, so we can produce a tailored CV — but in *our* template,
   which **contradicts requirement 5**. Only acceptable if offered explicitly as
   a different thing, never silently.

**Recommendation: 1 and 2 together.** Ask for the DOCX, always show the change
list. Offer 3 only as a clearly-labelled choice.

---

## 9. Risks

- **A wrong edit on a CV is worse than no edit.** Verify-then-replace, word
  boundaries, and a visible change list before and after are not optional.
- **DOCX run-splitting** is the main source of silent misses. Needs tests with
  real-world files, including tables and headers.
- **Storage cost grows per application**, not per user. 50 applications is 50
  documents. R2's free tier is ample, but retention should be a decision.
- **The master CV must never be written to.** Worth an explicit test.
- **Scope adjacency:** the applications module (`applications_build_plan.md`)
  overlaps this. `CVVersion` is deliberately shaped to serve both.

---

## 10. Phasing

**Phase 1 — tailoring end to end ✅ built**
`CVVersion`, `services/tailor.py` for profile + DOCX, the accept checklist, the
tailor and preview endpoints. PDF uploads get the change list.

**Phase 2 — the storage room ✅ built**
Documents stored in Postgres (§6 decision), list/detail/download/delete
endpoints, the `/my-cvs` page, 45-day retention enforced on read and by
`purge_cv_versions`.

**Phase 3 — remaining**
The prompt fixes in §11, decision 4 in §12, and re-tailoring an existing version
against a new posting.

### 10.1 Verification

| Layer | Result |
|---|---|
| Tailoring primitives (`test_tailor.py`) | 21 passed |
| Endpoints and storage room (`test_tailor_api.py`) | 15 passed |
| Whole backend suite | **436 passed, 0 failed** |
| Production image, full journey over HTTP | **25 checks passed** |
| Real browser, match → accept → storage room | **18 passed, 0 JS errors** |

The properties that matter, each covered by a test that fails without the guard:
the master CV is never written to, another user's tailored CV is unreachable, an
expired CV is gone before the purge runs, a rewrite we never offered is refused,
and formatting survives the DOCX edit.

---

## 11. Prompt-level defects found in testing

Both are model-behaviour issues, not architecture. Neither blocks the feature —
the second is now guarded in code — but both belong in the JOB_MATCH prompt.

**Abbreviations land in the wrong bucket, intermittently.** A CV saying **"DRF"**
against a job saying **"Django REST Framework"** was classified `matched` on one
run and `reworded` on another. For a human reader `matched` is correct; for a
literal ATS it is a missed keyword and the user is never told to spell it out.
The inconsistency is the real problem — the prompt should state that an
abbreviation of a required term is always a rewording.

**The model sometimes rewrites prose, not terms.** Alongside `Postgres →
PostgreSQL` it proposed `Optimised Postgres queries → query optimisation`.
Applying both would have produced *"query optimisation, cutting a report endpoint
from 4.2s to 310ms."* It was skipped only because the earlier rewrite changed the
text out from under it — order deciding whether a CV is mangled is not a
guarantee, so `_drop_overlapping` now refuses overlapping rewrites outright
(§tailor.py). The prompt should still be told to propose term renames only.

---

## 12. Decisions needed before Phase 1

1. ~~**Storage backend**~~ — **decided: Postgres.** Documents are stored as
   `bytea` on `CVVersion`, and the original DOCX on `CVUploadLog`, because the
   host filesystem is wiped on deploy. Bounded by the 45-day retention.
2. ~~**PDF uploads**~~ — **decided: ask for the DOCX, always show the change
   list.** Implemented.
3. ~~**Retention**~~ — **decided: 45 days**, matching `JOBS_RETENTION_DAYS`.
4. **Template for uploads — still open.** When a user uploads a PDF we cannot
   edit it, but we already parse it into structured content, so we *could*
   rebuild a tailored CV in a HireFlow template. It would be a real tailored CV
   that **does not look like the one they uploaded**. Built without it for now:
   PDF uploads get the change list only. Offering it later is additive.
