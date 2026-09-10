# Live Preview Across All Sections — Build Plan

> Persistent side-by-side preview in the CV Builder: edit any section, see the CV update.
> Decisions below are settled, with the industry precedent each one follows.
> Measured against the running app on 2026-08-18.

---

## 1. Which industry pattern applies to us

There are two established approaches, and the choice is already forced by our constraints.

**Pattern A — client-side HTML preview, server-side PDF export.** This is the *dominant*
approach among resume builders: reactive form-to-DOM binding, updates as you type, zero server
round-trip. Fast and cheap. It accepts that the preview and the exported PDF are produced by
different code and will drift.

**Pattern B — server renders, client displays that render.** Used where the renderer cannot be
faithfully reproduced in a browser, and where what the user downloads must be exactly what they
saw. Overleaf is the canonical example: a server compile, displayed via pdf.js, with the previous
output kept on screen while a new one is produced. The survey of current practice also notes
server-side processing is preferred for "controlled environments with fewer bugs and consistency
guarantees on what users receive."

**We are Pattern B, and not by preference.** The standing requirement on this project is that the
preview is an exact snapshot of the downloaded PDF. Pattern A cannot deliver that — WeasyPrint and
a browser disagree on font metrics and line breaking, and one different line break shifts
everything after it and can change the page count. We already built Pattern B and it is verified
byte-identical. This plan makes it *live* without abandoning that guarantee.

The cost of Pattern B is that every refresh is a server render, so the whole plan is really about
making that cheap, cancellable, and never visibly slow.

### Where we deliberately diverge from Overleaf

Overleaf ships auto-compile **off by default**, because a LaTeX compile takes seconds. Ours takes
**~360ms**. That difference justifies flipping the default: auto-refresh **on**, with the manual
trigger and the toggle retained. Same pattern, different default, because the economics differ by
an order of magnitude.

---

## 2. Measured baseline

Render cost on a realistic CV (3 roles, 12 bullets, 8 skills, education, project):

| Template | Cold render |
|---|---|
| classic | 213 ms |
| compact | 233 ms |
| executive | 247 ms |
| technical | 306 ms |
| modern | 388 ms |
| minimal | 772 ms (first call, includes warm-up) |

**Mean ~360 ms.** Served from cache: ~4 ms.

The constraint that matters is not the render time — it is that renders land on the **same two
gunicorn workers** that serve the form's own save requests. Unthrottled, a preview render would
make *typing* feel slow. Capacity, not rendering, is the risk.

---

## 3. Two corrections to earlier assumptions

**The render cache is weaker than previously stated.** I claimed returning to a
previously-rendered template would be free. Verified false: `content_updated_at` is `auto_now=True`,
so *any* save bumps it — including a `template_id` PATCH — which busts the cache for every
template.

The obvious fix is to make `content_updated_at` content-only. **Rejected**: two Celery retention
tasks read that field (the 23-day reminder and the 30-day draft deletion). Narrowing its meaning
would mean a user who browses templates without editing still gets their draft deleted. That is far
too much blast radius for a caching problem.

**Adopted instead:** key the server cache on a **hash of the built context plus template id**.
Building the context is a handful of queries and no render — ~5 ms spent to avoid ~360 ms — and
identical content hashes to the same key, so template flipping becomes genuinely free. This is
ordinary content-addressed caching and leaves retention semantics untouched.

**`PdfCanvas` has a hardcoded `scale={1.35}`**, producing a ~1070 px canvas that overflows a
380 px side pane. It must derive scale from measured container width.

---

## 4. Decisions

Each with the precedent it follows.

| # | Decision | Why |
|---|---|---|
| 1 | **Auto-refresh on by default**, debounced **600 ms**, plus a manual "Refresh" button and a persisted auto on/off toggle | Overleaf's auto-compile pattern with the default flipped, justified by 360 ms vs. seconds. The manual trigger is the escape hatch when a render fails or the user wants control. |
| 2 | **Stale-while-revalidate** — keep the current PDF on screen during a refresh, with an "Updating…" pill. Never blank to a spinner | RFC 5861 semantics; React Query's `placeholderData`; how Overleaf behaves. Blanking on every save reads as breakage. |
| 3 | **ETag + `If-None-Match`** on the preview endpoint, ETag = the content hash | Standard REST caching. Turns an unchanged re-request into a 304 with no body and no render. |
| 4 | **Server-side single-flight lock** (Redis `SETNX`) per `(cv, template, hash)`; concurrent duplicate requests await the one render | Request coalescing — Go's `singleflight`, cache-stampede prevention. Essential with few workers: three rapid saves must cause one render, not three. |
| 5 | **Cancel superseded requests** — pass React Query's `signal` through axios | Do not spend a worker on a render nobody will see. Standard `AbortController` practice. |
| 6 | **gunicorn `--workers` 2 → 4** | The preview must not contend with the form's own saves. Cheapest possible mitigation. |
| 7 | **Trigger on mutation success, not keystroke** | Our writes are already explicit per section. Debounce then coalesces bursts (adding five skills quickly), not characters. |
| 8 | **Mobile/tablet: preview behind a toggle**, full-screen sheet | Matches resume-builder convention on small screens. The sidebar is already `hidden md:flex`; a third column does not fit. |
| 9 | **Skip the render entirely for an empty CV**, show a placeholder card | Avoids showing a near-blank PDF that looks like a bug, and costs nothing. |
| 10 | **Do not move rendering to Celery** | Polling overhead and complexity are not justified for a 360 ms job, and it would make the preview feel *less* live. Revisit only if p95 degrades. |

### Why 600 ms

Total time-to-fresh-preview is `600 ms debounce + ~360 ms render ≈ 1 s`, which meets the
"updates within ~1 s of any section save" target. 600 ms comfortably exceeds the cadence at which a
person adds a next item — so bursts collapse into one render — while staying inside the ~1 s
threshold where an update still reads as immediate.

---

## 5. Architecture

```
  section save (mutation success)
        │
        ├─► invalidate profile / completion            (already built)
        │
        └─► content stamp changes
                │
          debounce 600 ms  ◄── collapses bursts
                │
        GET /api/cv/preview/?template=…
        If-None-Match: <hash>
                │
        ┌───────┴────────────────────────────────┐
        │ 304 Not Modified          200 + PDF    │
        │ (nothing changed)               │      │
        └─────────────────────────────────┼──────┘
                                          │
                    build_cv_context → hash
                             │
                    cache hit? ──yes──► ~4 ms
                             │no
                    Redis single-flight lock
                             │
                    WeasyPrint ~360 ms
                             │
                    cache + ETag, return
                             │
                    PdfCanvas (stale kept until ready)
```

The render path itself is unchanged — still one `render_cv_pdf()`, still the same bytes as the
download. Everything added is caching, throttling, and presentation.

---

## 6. Implementation plan

Ordered so each step is independently verifiable. Tests are built **inside** each phase rather
than appended as a final phase, because a trailing test phase is the first thing cut when time is
short. Sizing is rough developer-days for one person.

Total: **~3 days.**

### Phase 0 — test harness (~0.5 day)

There is currently no test infrastructure at all: no pytest, no config, and all six `tests.py`
files are 0 bytes. Tests are in scope for this work, so the harness comes first.

- Add `pytest`, `pytest-django` to `backend/requirements.txt`. The CV Builder spec already
  specifies pytest, so this sets the pattern for every module after this one.
- `backend/pytest.ini` with `DJANGO_SETTINGS_MODULE`, and `backend/conftest.py` with shared
  fixtures: an authenticated API client, and a `sample_cv` factory building a realistic profile
  (three roles with bullets, education, eight skills, a project).
- Point `CACHES` at a **separate Redis database** under test and flush it between tests. The app
  now uses real Redis, so without this the suite pollutes the dev cache and leaks state between
  tests — and the single-flight test would be meaningless.
- Convert `backend/apps/cv_builder/tests.py` into a `tests/` package.
- One smoke test to prove the harness runs in the container.

*Verify:* `docker compose exec backend pytest` runs green.

### Phase 1 — foundations (~0.5 day, nothing user-visible)

**1.1 — Content-hash cache key** · `services/pdf_renderer.py`

`_cache_key()` currently hashes `content_updated_at`, which changes on *any* save. Replace with a
hash of the actual content. This requires reordering the function: the context is built *after* the
key is looked up today, so the key must move below `build_cv_context()`.

```
resolve template → build_cv_context() → stable-serialise (json.dumps, sort_keys, default=str)
  → sha256 → key = cv:pdf:{template_id}:{digest}
```

Exclude the `template` dict from the hashed payload — it is static per id, and the id is already in
the key — so the digest reflects user content only.

**1.2 — Single-flight lock** · same file

Wrap the render in `cache.add(lock_key, 1, timeout=30)` as an atomic set-if-absent. If the lock is
not acquired, poll for the cache entry for up to ~2 s, then render anyway rather than deadlock.
Release in a `finally`.

**1.3 — ETag and 304** · `services/pdf_renderer.py` + `views/template.py`

Return the digest alongside the bytes so the view can set `ETag`, and honour `If-None-Match` with a
`304`. Header must be `Cache-Control: private, must-revalidate` — this is user data and must never
enter a shared cache.

**1.4 — Worker count** · `backend/Dockerfile`

`--workers 2` → `4`. This lives in the **Dockerfile**, not `docker-compose.yml`, and affects
production only: `Dockerfile.dev` runs `manage.py runserver`, which is threaded, so dev concurrency
behaves differently from prod. Remember this when load-testing.

**1.5 — Responsive canvas scale** · `components/preview/PdfCanvas.jsx`

Replace the hardcoded `scale = 1.35` with a measured value: observe the container with
`ResizeObserver`, use `scale = containerWidth / 595` (A4 is 595 pt at scale 1), and skip rendering
until width exceeds zero. Keep the devicePixelRatio backing so text stays sharp.

*Tests:* 1.1–1.3 are covered by the cache, ETag and single-flight tests in §7.

### Phase 2 — desktop live preview (~1 day)

**2.1 — `usePreview` hook** · new `hooks/usePreview.js`

One place owning all preview behaviour, so no step component knows how it works: 600 ms debounce on
the content stamp, auto/manual mode, `placeholderData: (prev) => prev` so the previous PDF stays on
screen, the enabled gate, and `refresh()` for the manual button.

Returns `{ data, isFetching, isStale, error, refresh, auto, setAuto }`.

**2.2 — Request cancellation** · `api/cvApi.js`, `api/cvQueries.js`

Thread React Query's `signal` through `getPreviewPdf(templateId, signal)` into axios, so a
superseded render is aborted rather than completed for nobody.

**2.3 — `PreviewPane`** · new `components/preview/PreviewPane.jsx`

Header: template name, page count, an "Updating…" pill while fetching, Refresh, auto toggle.
Body: `PdfCanvas` or the empty-state card. Never clears on refetch.

**2.4 — Lift the preview up** · `pages/CVBuilderPage.jsx`, `components/steps/TemplateStep.jsx`

Move the preview out of `TemplateStep` (which keeps only the gallery) into `CVBuilderPage`. Grid
becomes `[nav 240 | form minmax(0,1fr) | preview 380]` at `xl`, preview 440 at `2xl`, pane
`sticky top-6` with its own scroll.

**2.5 — Visibility gate**

Do not fire the query when the pane is not rendered. Drive it from the same `matchMedia` breakpoint
that controls the layout, so a narrow viewport never triggers a server render.

### Phase 3 — mobile preview panel (~0.5 day)

Below `xl` there is no room for a third column, so the preview becomes an on-demand panel. This is
first-class work, not polish.

- **Trigger:** a sticky bottom bar with a "Preview" button, showing the current page count when
  known. Sticky rather than a floating circle so it never covers form fields.
- **Panel:** full-screen sheet reusing `Modal`, which already handles Escape and body-scroll lock.
  Contains the PDF, a close button, and Download.
- **The render is not fired until the panel is opened.** This is the whole point of the visibility
  gate in 2.5 — a phone must not pay for a WeasyPrint render it never displays. While open,
  auto-refresh behaves as on desktop; on close, it stops.
- **Zoom:** fit-width by default (`scale = width / 595`), with a tap toggle to 100% and horizontal
  scroll. A4 at 375 px is ~0.63 scale, which is legible for layout but not for reading body text,
  so a zoom affordance is required rather than optional. Allow native pinch via `touch-action`.

Related gap, worth a separate ticket rather than folding in here: the CV Builder's own step
navigator already stacks correctly on mobile, but `AppLayout`'s app-level sidebar is
`hidden md:flex`, so below 768 px there is no navigation between Dashboard and CV Builder. The
builder is reachable via the Dashboard tile, so mobile is usable — but app navigation is missing.

### Phase 4 — polish (~0.5 day)

- Empty-state card, with the render skipped entirely.
- "Download PDF" in the pane header — its natural home now the preview is always present, and it
  currently only exists inside the template step.
- Persist the auto-refresh toggle to `localStorage`.

---

## 7. Test plan

All backend, using pytest-django from Phase 0. These guard invariants that fail **silently** — a
broken cache key, lock, or ETag path produces no error, just staleness or slowness nobody notices
for weeks.

### Two traps that will cost an afternoon if unknown

**The concurrency test needs `TransactionTestCase`** (or `pytest.mark.django_db(transaction=True)`).
Django's default `TestCase` wraps each test in a transaction that other threads cannot see, so a
threaded single-flight test either deadlocks or sees an empty database.

**Renders are ~360 ms each.** A suite that renders six templates across several tests gets slow
fast. Keep the shared fixture CV minimal, pass `use_cache=False` only where the test is actually
about rendering, and mark the full six-template sweep so it can be excluded from a fast local run.

### The tests

| File | Asserts |
|---|---|
| `test_preview_cache.py` | A content edit changes the cache key; switching template and back yields a cache hit; the content digest is stable across a `template_id` PATCH (the bug that motivated this change) |
| `test_preview_etag.py` | First GET returns 200 with an `ETag`; a repeat with `If-None-Match` returns 304 with an empty body; after a content edit the same `If-None-Match` returns 200 and a new `ETag` |
| `test_preview_singleflight.py` | Two concurrent identical requests cause exactly one WeasyPrint render (patch and count) |
| `test_preview_matches_download.py` | Preview bytes equal export-download bytes — the snapshot guarantee, the single most important test here |
| `test_template_security.py` | `?template=../../../etc/passwd` returns 400; an unknown template returns 400; one user cannot reach another user's preview |
| `test_templates_registry.py` | Every registry entry's file exists and renders with sample data; **exactly two** templates have `photo: True`; every registry id is a valid model choice |
| `test_photo_upload.py` | EXIF is stripped; the image is resized to ≤600 px; a non-image is rejected; over 2 MB is rejected |
| `test_empty_cv.py` | A CV with no sections renders without error on all six templates, and `template_id` is never null after creation |

### Frontend tests — deliberately deferred

Adding a frontend suite means vitest, jsdom and testing-library plus config, and the riskiest logic
in this change is the server-side invariants above. The frontend behaviour that could regress
(debounce timing, stale-while-revalidate, the visibility gate) is cheap to verify by hand and
awkward to test meaningfully in jsdom, which does not implement `ResizeObserver` or canvas
rendering.

Recommendation: ship backend tests now, treat the frontend harness as its own decision. Reversible
— say the word and it goes into Phase 0.

---

## 8. Edge cases

| Case | Behaviour |
|---|---|
| Empty CV | Placeholder card, no render fired |
| Save lands mid template-switch | Safe already: the query key carries template + stamp and the server renders from database truth. Brief stale frame, absorbed by the debounce |
| Render fails (503) | Keep the stale PDF, show an inline retry. Never replace good output with an error state |
| Rapid edits across sections | Debounce coalesces; single-flight guarantees one render even if requests race |
| Two-page CV | Pane scrolls; page count already reported by `/preview/meta/` |
| Photo removed while on a photo template | Already verified renders fine — the `<img>` is conditional, no blank box |

---

## 9. Deliberately out of scope

- **Scroll-syncing the preview to the section being edited.** Genuinely nice, and Overleaf does it
  for LaTeX via SyncTeX. We have no equivalent: the PDF is rasterised, so there is no DOM to anchor
  to, and it would mean mapping sections to page offsets. Separate piece of work.
- Client-side HTML preview as a "fast path" — reintroduces exactly the drift this architecture
  exists to prevent.
- Per-field live preview as you type. Our saves are per-section by design; character-level preview
  would mean per-keystroke renders.
- **A frontend test harness** (vitest/jsdom/testing-library). Backend tests are in scope and
  specified in §7; the frontend harness is a separate decision with its own dependency cost —
  reasoning in §7.
- **Mobile app-level navigation.** `AppLayout`'s sidebar is `hidden md:flex`, so below 768 px there
  is no Dashboard ↔ CV Builder nav. The builder is reachable via the Dashboard tile and the step
  navigator stacks correctly, so mobile is usable. Own ticket.

---

## 10. Risks

**The 360 ms figure is one CV on an idle machine.** It will be worse for a two-page CV and under
concurrency. This is why the worker bump belongs in Phase 1 rather than as a follow-up.

**Render load scales with active editors, not total users.** Single-flight and the content hash cap
the damage, but if concurrent editing grows, the next lever is a dedicated render worker pool —
not Celery-for-preview.

**This is the repo's first test suite, so Phase 0 is real work, not a formality.** No pytest, no
config, and all six `tests.py` files are empty. Budget the half day honestly — the fiddly parts are
the Redis-under-test isolation and the `TransactionTestCase` requirement for the concurrency test
(§7), both of which silently produce meaningless passes if got wrong.

**Test-suite runtime.** Each render is ~360 ms, so a careless suite becomes slow enough that people
stop running it. Keep the shared fixture minimal and mark the six-template sweep as excludable.

**Mobile now fires renders too.** Once the panel exists, a phone opening it costs a full render. The
visibility gate means it costs nothing until opened, but "mobile is free" stops being true — worth
watching if mobile usage is significant.

---

## Sources

- [Overleaf — recompiling your project](https://docs.overleaf.com/getting-started/recompiling-your-project)
- [Overleaf — auto-compile behaviour](https://www.overleaf.com/blog/642-tip-of-the-week-overleaf-v2-autocompile)
- [Overleaf — manual vs auto compile modes](https://www.overleaf.com/blog/74-new-feature-toggle-between-auto-compile-and-manual-compile-modes-in-writelatex)
- [Resume builder architectures, client-side preview norm](https://github.com/besttoolsforever/resume-generator)
- [React PDF Renderer based builders — live preview + export](https://github.com/sambhu431/react-resume-builder)
- [Resume Builders Using The MERN Stack (IJCRT)](https://www.ijcrt.org/papers/IJCRT2504652.pdf)
