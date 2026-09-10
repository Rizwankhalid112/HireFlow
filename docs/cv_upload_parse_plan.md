# CV Upload & AI Parse — Build Plan

> Spec Steps 7 and 8: upload a PDF/DOCX, extract its text, parse it with Claude, and
> let the user review before it touches their CV.
> Measured against the running app on 2026-09-07 (branch `feat/live-preview-cv`).

---

## 1. Why this is the next piece

It is the last unbuilt part of the 10-step spec, and the cheapest it will ever be:

- **`CVUploadLog` already exists** with the full status machine (`pending → extracting →
  parsing → success/partial/failed/scanned`) and is currently **dead code** — nothing writes
  a row. `delete_orphaned_files` in `tasks.py` already sweeps `media/cv_uploads/`, a
  directory nothing creates.
- **The AI layer the spec assumed you would build from scratch is already there.**
  `services/ai/client.py` runs structured-output calls; `schemas.py` is a working example of
  a closed Pydantic schema; the throttle scope, the metering pattern and the error-mapping
  convention are all established by the suggestions work.
- It is the highest-value feature left for the user: upload a CV rather than typing six
  sections into a form.

---

## 2. What already exists that this reuses

| Piece | Where | How this uses it |
|---|---|---|
| `complete(system, user_content, output_format)` | `services/ai/client.py` | The parse call, with a raised token ceiling (§3.1) |
| Closed, fully-required Pydantic schemas | `services/ai/schemas.py` | Pattern for `ParsedCV` |
| Prompt-as-module-constant, cache breakpoint | `services/ai/prompts.py` | The parse system prompt must follow the same rule |
| `credits_used_this_period`, count-don't-decrement | `models/suggestion_log.py` | Parse metering (§3.4) |
| `ScopedRateThrottle`, `ai_suggest` scope | `config/settings.py` | A new `cv_upload` scope |
| Section serializers | `serializers/` | Validate parsed data on apply, so AI output cannot write what the manual form would reject |
| `sample_cv`, `ai_enabled`, `api` fixtures | `conftest.py` | Test fixtures, no new harness needed |
| `Modal` (Escape + body-scroll lock) | `components/ui/Modal.jsx` | The diff-review sheet |
| Preview invalidation on mutation success | `hooks/usePreview.js` | Apply repaints the live preview for free |

---

## 3. Where this diverges from the spec, and why

### 3.1 Structured outputs replace §8.2 entirely

The spec sketches `clean_json_response()` — regex the markdown fences off, `json.loads`,
catch `JSONDecodeError`. `messages.parse(output_format=…)` makes all of it unreachable. The
API constrains generation to the schema and the SDK returns a validated instance or nothing.

**Deleted from scope by this one decision:** the fence-stripping regex, the `JSONDecodeError`
branch, the "Claude hallucinates extra fields" edge case (a closed schema cannot carry them),
and the "bullets returned as one long string" fallback (`list[str]` is enforced upstream).
The AI R&D doc already recommended this for Step 8; this plan is where it lands.

**Two changes `client.py` needs to serve both callers:**

- `MAX_TOKENS = 2000` is a module constant sized for a three-variant bullet suggestion. A
  full CV is a much larger output — three roles with bullets, education, skills, projects
  will run past 2000 and truncate, and a truncated structured output comes back as
  `parsed_output is None`, i.e. an unexplained failure. Add a `max_tokens=` parameter
  defaulting to the current value so the suggestion path is untouched.
- Every upstream failure is mapped to `SuggestionUnavailable` with the message *"The writing
  assistant is unavailable right now. Your text is unchanged."* — wrong words for a parse.
  Take the user-facing message as a parameter; the exception type stays shared.

### 3.2 `partial` changes meaning, and becomes worth having

The spec reaches `partial` via `extract_partial_valid_data()` after a
`PydanticValidationError`. With structured outputs there is no partially-valid payload —
it validates or it is `None`.

**Redefine it against something real:** the schema validated, but the CV came back thin —
no work experience, or `fields_extracted` below a threshold. That is the honest signal to
the user ("we got your contact details but not your roles — check the file"), and it is the
case that actually happens with an oddly-laid-out CV.

### 3.3 `needs_diff_review` should not be a `parse_status`

Spec §8.4 has the status endpoint return `status='needs_diff_review'`. `ParseStatus` has no
such member, so following it literally means a migration.

**Do not add it.** `parse_status` describes *the parse*. Whether a review is needed is a
question about *the profile* — and the answer can change between the parse finishing and the
user looking at it, because they can edit in another tab. Return a derived boolean
`requires_review` alongside `status: 'success'`, computed per request from
`cv.work_experiences.exists() or cv.educations.exists() or cv.skills.exists()`. Derived
means it can never be stale. No migration, and the state machine keeps one meaning per field.

### 3.4 Parses must be metered; the spec meters nothing

A parse is a much bigger call than a suggestion — a two-page CV plus a full structured
response lands roughly **5–8× the cost of a single suggestion** (~1¢), so a handful of
re-uploads is a meaningful spend. The suggestions work established that an authenticated
endpoint hitting a metered API with no cap is uncapped billing exposure; an upload endpoint
that *triggers* such a call is the same exposure one step removed.

Two controls, both cheap:

- **DRF throttle scope `cv_upload`**, default `5/hour`, on the upload endpoint. The existing
  `ai_suggest` scope does not cover it.
- **A monthly parse cap**, `AI_PARSE_MONTHLY_LIMIT` (default 5), counted from `CVUploadLog`
  rows that reached a terminal AI status this month — counted, never decremented, for the
  same reason as suggestion credits.

### 3.5 Validate file type by magic bytes, not `content_type`

Spec §7.2 checks `ALLOWED_MIME_TYPES`. `file.content_type` is supplied by the client and is
trivially spoofed. Keep the check, and add a header sniff: `%PDF-` for PDF, `PK\x03\x04` for
DOCX (a zip container). Cheap, and it is the difference between a real check and a polite one.

### 3.6 The stuck-task sweeper must cover `pending` too

The spec's edge case is "status is `extracting` for more than 5 minutes → `failed`". If the
worker is down the row never leaves `pending`, which is the more likely failure and the one
the spec's rule misses. Sweep all three non-terminal statuses (`pending`, `extracting`,
`parsing`) against `uploaded_at`.

---

## 4. Decisions

| # | Decision | Why |
|---|---|---|
| 1 | Two chained Celery tasks, as the spec has it | Extraction and the AI call fail for unrelated reasons; `parse_status` should say which one broke. This is genuinely slow, one-shot work with nobody watching — the case where Celery is right |
| 2 | `pdfplumber` for PDF, `python-docx` for DOCX, including table cells | Spec §7.4–7.5. Table extraction is not optional: two-column CVs are common and put half the content in cells |
| 3 | Scanned detection at `len(text.strip()) < 100`, before any API call | Never spend a metered call on an empty string. Same branch catches an image-only DOCX |
| 4 | Poll `/status/` every 2s, stop on terminal status | Spec §7.6. Add a client-side ceiling (~3 min) so a wedged backend cannot poll forever |
| 5 | Parsed data is **never** written on the parse path | It lands in `ai_parsed_json` and waits for an explicit `POST …/apply/`. Overwrite protection is the whole point of §8.4 |
| 6 | Apply writes through the existing section serializers | The AI must not be able to write a value the manual form would reject |
| 7 | `merge` for skills reuses the `bulk-add` `get_or_create` path | Already handles duplicates by skipping. Do not write a second dedupe |
| 8 | Empty CV skips the diff UI and applies directly | A brand-new user reviewing a diff against nothing is a modal for no reason |
| 9 | Age guard on `delete_orphaned_files` | It goes live the moment uploads exist. Skip files younger than an hour so a file saved seconds before the sweep cannot be deleted out from under a request |

---

## 5. Architecture

```
  POST /api/cv/upload/  (multipart)
        │  validate: type (magic bytes) · size ≤5MB · non-empty · throttle · monthly cap
        │  save → media/cv_uploads/{user_id}/{ts}_{safe_name}
        │  CVUploadLog(parse_status='pending')
        │  extract_text_from_cv.delay(log_id)
        └─► 202 { log_id, status: 'pending' }

  ── worker ─────────────────────────────────────────────
  extract_text_from_cv          status='extracting'
        │  pdfplumber / python-docx (paragraphs + table cells)
        │
        ├─ text < 100 chars ──► status='scanned'   ✗ stop, no API call
        ├─ raises ────────────► status='failed'    ✗ stop
        └─ ok → raw_extracted_text, extracted_at
                 └─► send_to_ai_parser.delay(log_id)

  send_to_ai_parser             status='parsing'
        │  complete(PARSE_SYSTEM_PROMPT, cv_text, ParsedCV, max_tokens=8000)
        ├─ SuggestionUnavailable ──► status='failed' + retry-friendly message
        └─ ok → ai_parsed_json, fields_extracted/total
                 status = 'success' | 'partial'      ← nothing written to the CV yet
  ───────────────────────────────────────────────────────

  GET /api/cv/upload/{id}/status/   (polled every 2s)
        └─► { status, fields_extracted, fields_total, error_message,
              requires_review, parsed_data?, existing_data? }
                                    └─ derived per request, never stored

  POST /api/cv/upload/{id}/apply/
        Body: { personal: replace|keep, work_experience: replace|keep|merge, … }
        └─► writes through section serializers → invalidate → preview repaints
```

---

## 6. Implementation plan

Ordered so each phase is independently verifiable. Tests live inside each phase.
Rough sizing for one person: **~3.5 days.**

### Phase 0 — dependencies and settings (~0.25 day)

- `pdfplumber`, `python-docx` into `requirements.txt`. Both are pure Python
  (pdfplumber pulls `pdfminer.six`; `Pillow` is already present), so the **Dockerfile needs
  no new system packages** — unlike WeasyPrint, which is why that block exists today.
- Settings: `cv_upload` throttle rate, `AI_PARSE_MONTHLY_LIMIT`, `AI_PARSE_MAX_TOKENS`,
  explicit `FILE_UPLOAD_MAX_MEMORY_SIZE`. Mirror the names into `.env.example`.
- `client.py`: add `max_tokens` and `unavailable_message` parameters, defaults unchanged so
  the suggestion path is byte-identical.

*Verify:* existing AI tests still green.

### Phase 1 — upload endpoint and extraction (~1 day)

**1.1** `services/extraction.py` — `extract_pdf`, `extract_docx`, one `ExtractionError`.
Table cells included for DOCX.

**1.2** `serializers/upload.py` — file validation: extension, `content_type`, magic bytes,
size bounds, `get_valid_filename` truncated to 100 chars.

**1.3** `views/upload.py` — `CVUploadView` (202 + `log_id`), `CVUploadStatusView`. Both
scoped to `request.user`'s own profile, like every other view in the app.

**1.4** `tasks.py` — `extract_text_from_cv`, chaining to stage 2; plus `fail_stuck_uploads`
sweeping `pending`/`extracting`/`parsing` older than 5 minutes, registered in
`setup_cv_beat_tasks.py`.

**1.5** Age guard on `delete_orphaned_files`.

*Tests:* `test_upload_validation.py` (oversize, empty, wrong type, spoofed content-type,
traversal attempt in the filename), `test_extraction.py` (a small fixture PDF and DOCX
including a two-column table; a text-free PDF hits the scanned branch).

### Phase 2 — AI parse and normalization (~1 day)

**2.1** `services/ai/schemas.py` — `ParsedCV` and its section models. Closed and
fully-required, same convention as the suggestion schemas. `cgpa` gets a validator that
pulls a float out of `'3.3/4.0'` (spec edge case, still real).

**2.2** `services/ai/prompts.py` — `PARSE_SYSTEM_PROMPT` as a module constant. **The rules
and the shape go in the system prompt; only the CV text goes in `messages`** — an
interpolated value silently breaks prompt caching, which is why `test_ai_prompts.py` exists.

**2.3** `services/ai/parse.py` — `parse_cv_text(text)`, one entry point, mirroring
`suggest.py`.

**2.4** `services/parse_normalize.py` — Layer 2 in full (§7.4), the Languages guard (§7.3)
and `needs_attention` flagging (§7.5). Pure functions over the parsed object, no database
writes, which is what makes it cheap to test exhaustively.

**2.5** `tasks.py` — `send_to_ai_parser`, normalization, `fields_extracted` counting,
`success`/`partial` decision.

*Tests:* `test_cv_parse.py`, `test_parse_normalize.py`, `test_parse_mapping.py` — `complete`
patched, never a real call.

### Phase 3 — apply and diff (~0.5 day)

**3.1** `services/apply_parsed.py` — per-section `replace` / `keep` / `merge`, each write
going through the section's own serializer inside a savepoint (§7.6): one bad row is skipped
and reported, an unexpected exception still rolls the whole apply back. Accepts the answers to
any `needs_attention` questions (§7.5) alongside the choices.

**3.2** `views/upload.py` — `CVUploadApplyView`. Rejects unless the log is terminal-success
and belongs to the caller; refuses to apply the same log twice.

*Tests:* `test_apply_parsed.py` — merge does not duplicate skills; `keep` leaves a section
untouched; applying another user's log is 404; double-apply is refused.

### Phase 4 — frontend (~1 day)

- `UploadDropzone` — drag/drop plus a file input, client-side size/type check for a fast
  error, progress while posting.
- `useUploadStatus` — 2s poll, stops on terminal status, on unmount, and at a ~3 min ceiling.
- `DiffReviewModal` — one row per section: what you have, what we found, and the
  keep/replace/merge choice. Reuses `Modal`. Also renders the two things §7 adds: the
  `unmapped_sections` block, and an inline input for every `needs_attention` row, which gates
  that row's import.
- Wire into `CVBuilderPage`: entry point on the contact step and an empty-state prompt, then
  invalidate every CV query on apply so the live preview repaints.

*Frontend tests deferred*, on the same reasoning as the live-preview plan §7 — no vitest
harness exists and that remains its own decision.

---

---

## 7. Mapping a real CV onto our schema

This is the hard part of the feature and the spec does not address it at all. A real CV does
not use our headings, our vocabulary, or our field set. Three layers handle it, and the order
matters — each one catches what the layer above cannot.

```
  Layer 1  the schema constrains generation   → enum drift cannot occur
  Layer 2  services/parse_normalize.py        → shape, length, range, collisions
  Layer 3  the section serializers on apply   → last gate, per-row, never all-or-nothing
```

### 7.1 Layer 1 — headings and enums

**Headings are a solved problem, and that is the reason to use a model at all.** A regex
parser has to know that "Employment History", "Professional Experience", "Career Summary" and
"Where I've Worked" are the same section. A model reads the content. The system prompt states
the target schema and instructs mapping **by content, not by heading text**, with a synonym
list for the common cases only as a hint:

| Our section | Headings seen in the wild |
|---|---|
| `work_experience` | Experience · Professional Experience · Employment History · Career History · Relevant Experience · Work History · Berufserfahrung |
| `education` | Education · Academic Background · Qualifications · Academic Qualifications · Formación |
| `skills` | Skills · Technical Skills · Core Competencies · Technical Competencies · Areas of Expertise · Proficiencies · Tech Stack |
| `projects` | Projects · Personal Projects · Selected Projects · Portfolio · Side Projects |
| `certifications` | Certifications · Licenses & Certifications · Training · Professional Development · Courses |
| `summary` | Summary · Profile · About · Professional Summary · Objective · Career Objective |
| `languages` | Languages · Language Proficiency — **but see §7.3** |

**Enums cannot drift, because the schema forbids it.** Every constrained field is a
`Literal[...]` matching our model's choices exactly, plus `''` for "not stated". Structured
outputs constrain *generation*, so the model cannot emit `"Permanent"` into `employment_type`
— that token sequence is not available to it. The mapping happens inside the model, guided by
the prompt, instead of in a lookup table we would have to keep extending forever.

The exact literal sets, taken from the models:

| Field | Literals | `''` means |
|---|---|---|
| `employment_type` | `full_time · part_time · internship · contract · freelance` | not stated, or something we do not model (volunteer) |
| `location_type` | `onsite · remote · hybrid` | not stated |
| `degree_type` | `bs · ms · phd · diploma · certificate · other` | not stated |
| skill `category` | the seven `SkillCanonical.Category` values | unresolved |
| skill `proficiency` | `beginner · intermediate · advanced · expert` | not stated |
| language `proficiency` | `native · fluent · professional · basic` | not stated |

Prompt guidance for the judgement calls the literals cannot express: `B.Tech / BSc / BE / BA /
Bachelor → bs`; `M.Tech / MSc / MBA / MA / Master → ms`; `Doctorate / DPhil → phd`;
`A-Levels / FSc / High School / Associate → other`; `Permanent → full_time`;
`Intern → internship`; `Consultant / Temporary → contract`; `Self-employed → freelance`;
CEFR `C2/C1 → fluent`, `B2/B1 → professional`, `A2/A1 → basic`, `Mother tongue / Bilingual →
native`. **`''` is always available and is always better than a wrong guess.**

### 7.2 Sections we have no model for are surfaced, never dropped

Publications · Awards · Volunteering · References · Hobbies · Interests · Patents ·
Conferences · Speaking · Memberships · Extracurriculars.

Silently discarding a user's Publications list is the worst outcome this feature can produce —
they would not find out until they looked at the rendered PDF, if then. So the schema carries
an explicit escape hatch:

```python
class UnmappedSection(BaseModel):
    heading: str      # as it appeared in their CV
    content: str      # the text, truncated
```

The diff modal renders these as *"We found these sections, and HireFlow has nowhere to put
them yet"*, with the text selectable to copy. **Data loss becomes an informed choice.** It is
also the honest backlog signal for which section to model next.

Two placements that look unmapped but are not: **Volunteer Experience** maps to
`work_experience` with `employment_type=''` — it has the company/role/dates shape and users
want it on the CV. **Courses / Training** maps to `certifications`.

### 7.3 The "Languages" collision

The single most damaging mapping error available, and it is not hypothetical:

```
Languages: Python, Java, C++          →  programming languages, belongs in skills
Languages: English, Urdu, Arabic      →  spoken languages, belongs in CVLanguage
```

A CV that heads its programming languages "Languages" would populate the spoken-languages
section with `Python (native)`. The prompt addresses it, but a prompt is not a guarantee, so
there is a **mechanical guard in Layer 2**: every `languages[].language_name` is resolved
against `SkillCanonical`. A hit in the `Languages` (programming) category is moved into
`skills` and out of spoken languages. Deterministic, free, no second model call — the same
shape as the `metric_extractor` guard the suggestions feature uses.

### 7.4 Layer 2 — `services/parse_normalize.py`

What the schema cannot enforce. Every rule here is a real failure mode, not defensive padding:

| Rule | Why |
|---|---|
| **Truncate to `max_length`** on every string | `institution` is 300, `role_title` 200, `full_name` 100. A long institution name raises `DataError` at write time otherwise |
| **Prepend `https://` to bare URLs** | CVs write `linkedin.com/in/name`. Django's `URLValidator` rejects it outright — this alone would fail a large share of imports |
| **Drop `cgpa` outside `0 < x ≤ 10`** | `DecimalField(max_digits=3, decimal_places=2)` maxes at 9.99, so a percentage grade (`85%`) raises. A percentage is not a CGPA; drop it rather than mangle it |
| **Filter bullets under 10 characters** | `WorkBulletSerializer.validate_text` rejects them, which would fail the whole role. Drop the fragment, keep the role |
| **Swap reversed date ranges; drop years outside 1950–now+1** | `2023–2020` and OCR-mangled years like `2O2O` → `0` |
| **`is_current` ⇒ null end date** | Matches what the serializer does anyway; doing it here keeps the diff preview honest |
| **Dedupe skills case-insensitively; resolve `category` via `SkillCanonical`** | Reuses the exact-match-then-alias resolver, including the `Java` / `JavaScript` fix already recorded in the AI R&D doc |
| **Collapse duplicate sections** | "Relevant Experience" + "Other Experience" are one list to us |
| **Never translate values** | Headings are mapped; the user's own words are theirs. A German CV keeps German role titles |

### 7.5 The missing-required-field problem

Two fields are `NOT NULL` with no default, and both are routinely absent from real CVs:

- **`Education.start_year`** — the common CV line is *"BSc Computer Science, MIT, 2019"*. That
  is the **end** year. There is no start year to extract.
- **`WorkExperience.start_year`** — a CV listing a role with no dates at all is unusual but real.

Three bad options and one good one. Dropping the entry is silent data loss. Inferring
"2019 − 4 years" is fabrication, which this project has an explicit rule against. Making the
columns nullable is a migration that changes the manual form's contract for a parsing problem.

**Adopted: flag, ask, then write.** Normalization marks such an entry `needs_attention` with
the field named. The diff modal renders that row with a single inline input — *"Which year did
you start at MIT?"* — and **apply is blocked on that row until it is answered**; the rest of
the import proceeds. No fabrication, no data loss, and the user answers one small question
instead of re-typing a degree.

This is deliberately the same mechanism as the AI suggestions' gap questions: **where a fact
is missing, ask for it — never invent it.** Consistent with the rule the module already runs on.

### 7.6 Layer 3 — apply is per-row, never all-or-nothing

Each row is written through its section serializer inside a savepoint. A row that still fails
is collected and reported; it does not roll back the roles that imported fine. The response
carries `{ imported: 14, skipped: [{section, reason}] }`, so a partial import is a visible
outcome rather than a mystery. The transaction wraps the whole apply so an *unexpected*
exception cannot leave a half-imported CV, but an expected per-row rejection is caught inside.

---

## 8. Edge cases

Spec §7 and §8, plus everything the decisions above change.

### Upload and extraction

| Case | Behaviour |
|---|---|
| Upload interrupted | Django's multipart parser raises on a truncated body; delete the partial file, 400 |
| Corrupted PDF | `ExtractionError` → `failed`, "File appears corrupted. Try re-exporting your CV as PDF." |
| Scanned PDF / image-only DOCX | Both land under 100 chars → `scanned`, **no API call spent** |
| Password-protected PDF | `pdfplumber` raises `PDFPasswordIncorrect` → `failed`, "This PDF is password protected. Remove the password and re-upload." |
| `.doc` (old binary Word) | Rejected at validation — `python-docx` cannot read it. "Save as .docx or PDF and try again." |
| Zero-byte / whitespace-only file | Caught by the size check and the 100-char check respectively |
| 40-page PDF | Cap extraction at ~30 pages and ~60k characters; a CV is never longer and an unbounded input is an unbounded bill |
| Two-column PDF | `pdfplumber` returns layout order, which interleaves columns. The model tolerates it; this is the main cause of a thin parse and the reason `partial` exists |
| Worker crash mid-task | `fail_stuck_uploads` moves `pending`/`extracting`/`parsing` older than 5 min to `failed` |
| Second upload before the first finishes | Allowed; second log row; most recent success wins; earlier rows kept |
| Path traversal in the filename | `get_valid_filename` strips separators; the path is always under `cv_uploads/{user_id}/` |
| Spoofed `content_type` | Magic-byte sniff (`%PDF-`, `PK\x03\x04`) is the real check |

### Parsing and mapping

| Case | Behaviour |
|---|---|
| Malformed JSON from Claude | **Not reachable** — structured outputs return a validated instance or `None` |
| Extra hallucinated fields | **Not reachable** — closed schema |
| Wrong enum value (`"Permanent"`) | **Not reachable** — `Literal` constrains generation (§7.1) |
| Truncated response | `parsed_output is None` → `failed`. The token ceiling in §3.1 is what prevents it |
| Unfamiliar section heading | Mapped by content, not heading text (§7.1) |
| Section we do not model | Returned in `unmapped_sections` and shown to the user (§7.2) |
| "Languages" holding programming languages | Mechanically re-routed to skills (§7.3) |
| Missing `start_year` | Row flagged `needs_attention`, one inline question in the diff modal (§7.5) |
| CGPA as `'3.3/4.0'` | Validator extracts `3.3` and `4.0`; a percentage is dropped (§7.4) |
| Bare `linkedin.com/in/x` | `https://` prepended (§7.4) |
| Institution name over 300 chars | Truncated (§7.4) |
| Bullet shorter than 10 chars | Dropped; the role still imports (§7.4) |
| Non-English CV | Headings mapped, values kept in the original language (§7.4) |
| No headings at all | Model infers from content; a thin result is `partial`, not a failure |
| Empty section under a real heading | `[]`, never a fabricated entry |
| Claude down / timeout | `failed`, "AI service temporarily unavailable. Your file is saved — try parsing again later." Retry re-runs stage 2 only, so the user does not re-upload — but it **does** count against the cap, because it is a real metered call. Counted via `CVUploadLog.parse_attempts`, summed not counted |
| Monthly parse cap reached | 429 with used/limit, **before** the file is saved |

### Applying

| Case | Behaviour |
|---|---|
| Empty CV | Diff skipped, applied directly |
| `merge` with duplicate skills | `get_or_create`, duplicates skipped not errored |
| `keep` on every section | No writes; the log is still marked applied |
| Applying the same log twice | Refused — 409, "This import has already been applied." |
| Applying another user's log | 404, same as every other object in the app |
| User edits the CV between parse and apply | `requires_review` is derived per request, so it is correct at the moment they look (§3.3) |
| A row fails serializer validation | Collected into `skipped[]`; the rest imports (§7.6) |
| Profile deleted mid-flow | CASCADE removes the log; apply 404s |

---

## 9. Data handling

Uploaded CVs are personal data — name, email, phone, address, employment history — and this
feature adds two new places it lives: the file under `media/cv_uploads/` and
`raw_extracted_text` on the log row. Both are already covered by the existing retention path
(`CVUploadLog` CASCADEs from `CVProfile`, `delete_stale_drafts` removes 30-day-old drafts,
`delete_orphaned_files` sweeps the directory), so the work here is confirming that path
actually runs rather than inventing a new one. One test asserts that deleting a profile
removes its upload rows and their files.

Worth deciding separately: `raw_extracted_text` keeps a full copy of the CV indefinitely.
Clearing it once the parse succeeds would cost nothing except the ability to re-parse without
re-uploading. Left as-is for now, flagged here so it is a decision rather than an oversight.

---

## 10. Test plan

Every AI test patches `complete` — the suite never spends money, following `ai_enabled`.

| File | Asserts |
|---|---|
| `test_upload_validation.py` | Oversize, empty, `.doc`, spoofed `content_type`, traversal in the filename, throttle, monthly cap |
| `test_extraction.py` | Fixture PDF and DOCX; a two-column DOCX table yields both columns; a text-free PDF hits `scanned`; page/char caps hold |
| `test_cv_parse.py` | Prompt constant carries no interpolation (caching); thin result ⇒ `partial`; `SuggestionUnavailable` ⇒ `failed` with the retry message; **nothing is written to the CV on any parse path** |
| `test_parse_normalize.py` | The whole of §7.4 and §7.5: truncation, URL scheme, cgpa range, short bullets, reversed dates, dedupe, `needs_attention` flagging |
| `test_parse_mapping.py` | §7.2 and §7.3: unmapped sections survive to the payload; programming languages under a "Languages" heading land in skills, spoken ones do not |
| `test_apply_parsed.py` | `merge` does not duplicate; `keep` leaves a section untouched; another user's log is 404; double-apply is 409; one bad row is skipped, not fatal |
| `test_upload_retention.py` | Deleting a profile removes its upload rows and files |

**Fixtures**: small real PDF/DOCX files generated at test time rather than committed binaries —
WeasyPrint is already available to produce a PDF, and `python-docx` to produce a DOCX, so the
suite builds its own inputs and there are no opaque blobs in the repo.

---

## 11. Deliberately out of scope

- **Re-parsing an old upload from a history list.** Retry re-runs stage 2 for the most recent
  log; a full upload history UI is its own feature.
- **OCR for scanned PDFs.** Adds Tesseract to the image plus a large accuracy question. The
  `scanned` status exists so this can be declined cleanly.
- **Modelling the unmapped sections** (Publications, Awards, Volunteering). §7.2 surfaces
  them; adding models for them is a product decision with its own template work.
- **Parsing into a second CV.** `CVProfile` is one-per-user by design.
- **A frontend test harness** — unchanged from the live-preview plan.

---

## 12. Risks

**The prompt is the feature.** Plumbing is predictable; parse quality on a real, badly
laid-out CV is not. Budget iteration against several genuinely different CVs — one-column and
two-column, one-page and three-page, at least one non-English — not a single well-behaved one.

**Structured outputs move the failure mode rather than removing it.** No malformed JSON, but a
truncated response is `parsed_output is None` with nothing explaining why, which is what makes
the token ceiling a correctness fix rather than a tuning knob.

**§7.5 is the most likely thing to be got wrong under time pressure.** The tempting shortcut is
to infer a start year and move on. That silently fabricates a fact on a document the user will
be judged on, which is exactly what this module has a rule against.

**This is the first user-supplied-file path in the app.** Every other endpoint takes JSON. The
validation in Phase 1.2 is the entire security surface of the feature.
