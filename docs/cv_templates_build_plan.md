# CV Templates — Build Plan

> Supersedes the preview architecture in [cv_templates_rnd.md](cv_templates_rnd.md) §2.
> Hard requirement driving this document: **the live preview and the PDF must be the same
> artifact, not two renders that look similar.**

---

## 1. Why the R&D recommendation changed

The R&D doc proposed shared HTML+CSS with the browser rendering the preview and WeasyPrint
rendering the PDF. **That cannot satisfy "exactly a snapshot."**

Even with byte-identical CSS, a browser and WeasyPrint are separate layout engines and differ in
font hinting and metrics, line-breaking, sub-pixel rounding, and UA defaults. Those differences
are small individually, but a single different line break shifts every line after it and can push
content onto a second page. On a CV, where "does this fit on one page" is the whole question, that
is a visible, meaningful difference. Shared CSS gets you *close*. It cannot get you *identical*.

**There is exactly one way to guarantee identity: render once, and show that render.**

So the preview is no longer HTML. The preview *is* the PDF.

---

## 2. Architecture — one render, two dispositions

```
CVProfile
   │
   ├─► build_cv_context(cv)          one dict, every template consumes it
   │
   ├─► render_to_string(template)    Django template: HTML + CSS
   │
   └─► WeasyPrint .render()  ─────►  Document
                                        │
                    ┌───────────────────┼────────────────────┐
                    ▼                   ▼                    ▼
            len(document.pages)   write_pdf() bytes    cached in Redis
            = overflow truth            │              key: cv+template+
                                        │                   content_updated_at
                        ┌───────────────┴────────────────┐
                        ▼                                ▼
              GET /api/cv/preview/            GET /api/cv/export/download/
              Content-Disposition: inline     Content-Disposition: attachment
                        │
                  PDF.js → <canvas>
```

Preview and download are the **same bytes from the same cache entry**, differing only in an HTTP
header. Identity is structural — there is no matching to verify, because there is nothing to
match. This is the core of the plan.

### What this buys beyond identity

Because we render before showing anything, `len(document.pages)` gives the **real** page count.
That replaces the line-estimation model I proposed in R&D §3 — no more guessing at
`chars_per_line`. We measure the actual document:

```python
document = HTML(string=html, base_url=settings.MEDIA_ROOT).render()
overflows = len(document.pages) > template['max_pages']
```

Ground truth, not a heuristic. The estimator survives only as an optional pre-render hint while
editing, and is not needed for v1.

---

## 3. Stack

| Concern | Choice | Why |
|---|---|---|
| PDF engine | **WeasyPrint 69** | Pure Python, flexbox fully supported since v66, grid since v62. No browser to ship. |
| Template layer | **Django templates** | Already configured (`APP_DIRS: True`); no new dependency. |
| Preview renderer | **`pdfjs-dist`** → `<canvas>` | Renders the actual PDF, so it is faithful by construction. Vector — sharp at any zoom, text selectable. Consistent across browsers, unlike native `<iframe>` PDF viewers with their own chrome. |
| Photo processing | **Pillow** (already installed) | Validate, re-encode, strip EXIF, resize. |
| Render cache | **Redis** | Already running. Keyed by content hash. |
| Thumbnails | **Static SVG** | Six hand-built wireframes. Never rasterize at runtime for a gallery. |

**Rejected:** headless Chrome (~400 MB image, slow cold start — only needed if WeasyPrint fidelity
disappoints, and swapping it later touches only the render function). **Rejected:** server-side
PNG rasterization for preview (needs poppler/pdfium as another system dep, loses text selection).

### Known friction: PDF.js + Vite

`pdfjs-dist` uses a web worker, and Vite's dep pre-bundling is awkward with workers. The worker
version must match the library version exactly. Mitigation:

```js
import * as pdfjsLib from 'pdfjs-dist';
import workerUrl from 'pdfjs-dist/build/pdf.worker.min.mjs?url';
pdfjsLib.GlobalWorkerOptions.workerSrc = workerUrl;
```

plus `optimizeDeps.include: ['pdfjs-dist']` in `vite.config.js`. Budget half a day for this; it is
the single most likely place to lose time.

---

## 4. The six templates — exactly two with a photo

| # | id | Layout | Density | ATS | Photo |
|---|---|---|---|---|---|
| 1 | `minimal` | 1 col, generous whitespace | Low | ✓ | ✗ |
| 2 | `classic` | 1 col, serif, traditional | Medium | ✓ | ✗ |
| 3 | `technical` | 1 col, skills grid up top | High | ✓ | ✗ |
| 4 | `compact` | 1 col, tight leading, 2-col skills | Very high | ✓ | ✗ |
| 5 | `modern` | **2 col** — photo + contact + skills sidebar | Medium | ✗ | **✓** |
| 6 | `executive` | 1 col, photo in header band | Medium | ✓ | **✓** |

The two photo templates are deliberately different in a way that matters: `modern` is two-column
and **not ATS-safe** (parsers read straight across columns and interleave the sidebar into the
body), while `executive` keeps a single-column flow so it stays machine-readable *and* carries a
photo. That gives users a photo option that will not sabotage their application, which is the
point of the product.

The picker labels ATS-safety on every card, defaults to `minimal`, and shows a quiet caution on
`modern`.

Templates that don't declare `photo: True` ignore the uploaded image entirely — the field is
simply absent from their markup.

---

## 5. The photo

`CVProfile` has no image field today. `UserProfile.avatar` exists but belongs to the accounts app
and serves a different purpose (account avatar vs. professional headshot, different crop).

**Add a dedicated field**, prefilled from the account avatar on first use if present:

```python
# CVProfile
photo = models.ImageField(upload_to='cv_photos/%Y/%m/', null=True, blank=True)
```

One migration. Endpoints:

| Method | Path | Notes |
|---|---|---|
| POST | `/api/cv/photo/` | multipart, replaces any existing photo |
| DELETE | `/api/cv/photo/` | clears it |

### Handling it safely

An image upload is untrusted input, and a CV photo has a specific privacy trap:

- **Strip EXIF.** Phone photos routinely carry GPS coordinates. Publishing someone's home location inside a CV they email to strangers is a real harm. Re-encoding through Pillow drops EXIF as a side effect — do it unconditionally, not just when resizing.
- **Validate by decoding, not by extension.** `Image.open()` + `.verify()`, then re-open to process. Accept JPEG/PNG/WebP only.
- **Re-encode and resize** to a fixed box (600×600 max, JPEG q85). Keeps PDFs small and output consistent across templates.
- **Cap at 2 MB** in the serializer. nginx already allows 20 MB, so the app must enforce the real limit.
- Storage is `MEDIA_ROOT/cv_photos/`, already served and already covered by the existing media volume.

### WeasyPrint and the image

WeasyPrint must resolve the file locally, not over HTTP. Render with
`HTML(string=html, base_url=settings.MEDIA_ROOT)` and reference the relative media path. No
network fetch, no auth problem.

---

## 6. Backend work

```
backend/apps/cv_builder/
├── templates/cv_templates/
│   ├── base.html                shared skeleton + @page rules
│   ├── _sections.html           reusable section partials
│   ├── minimal.html  classic.html  technical.html
│   ├── compact.html  modern.html   executive.html
│   └── static/css/<id>.css      one stylesheet per template
├── templates_registry.py        THE allowlist + capacity metadata
├── services/
│   ├── cv_context.py            build_cv_context(cv) -> dict
│   └── pdf_renderer.py          render_cv_pdf(cv, template_id) -> (bytes, page_count)
├── views/template.py            list / preview / export / photo
└── migrations/0002_cvprofile_photo.py
```

**Registry** — single source of truth, and the security boundary:

```python
CV_TEMPLATES = {
  'minimal': {
    'name': 'Minimal',
    'file': 'cv_templates/minimal.html',
    'columns': 1, 'ats_safe': True, 'photo': False,
    'max_pages': 1,
    'description': 'Clean and spacious. Best for early career.',
  },
  ...
}
```

**Security fix that must land with this work.** `template_id` is currently an unvalidated
`CharField` writable through `CVProfileWriteSerializer`, and spec §9.3 suggests
`f'cv_templates/{cv.template_id}.html'`. That is a path-traversal vector into `render_to_string`.
Never interpolate — always `CV_TEMPLATES[template_id]['file']` with a `KeyError` → 400, and add
`choices` to the model field.

**Endpoints:**

| Method | Path | Returns |
|---|---|---|
| GET | `/api/cv/templates/` | Registry: id, name, flags, max_pages, description |
| GET | `/api/cv/preview/?template=<id>` | `application/pdf`, inline. Falls back to saved `template_id`. |
| GET | `/api/cv/preview/meta/?template=<id>` | `{page_count, overflows, max_pages}` — cheap JSON for the fit banner |
| POST | `/api/cv/export/pdf/` | Persists to `pdf_file`, sets `pdf_generated_at` |
| GET | `/api/cv/export/download/` | `attachment; filename="cv_<name>.pdf"` |
| POST/DELETE | `/api/cv/photo/` | Upload / clear |

**Caching.** Key on `f'cv:pdf:{cv.id}:{template_id}:{int(cv.content_updated_at.timestamp())}'`,
TTL 1 h. Content edits bump `content_updated_at` (existing signals already do this), so the key
rotates automatically. Template switching during browsing hits distinct keys, so flipping back and
forth is free after the first render.

> **`CACHES` is not configured** in `settings.py` — `django.core.cache` currently falls back to
> per-process LocMemCache. That must be pointed at Redis for this cache to work across gunicorn
> workers. It also fixes the stale `skill_detector` cache noted in the backend context doc.

**Sync vs Celery.** A 1–2 page CV renders in roughly 200–500 ms, so preview is fine synchronously
with the cache in front. But gunicorn runs `--workers 2`; concurrent uncached previews will
saturate that. Start synchronous, raise workers to 4, and move the *export* to Celery if p95
suffers. The existing `pdf_file` / `pdf_generated_at` / `content_updated_at` fields already support
the spec's skip-regeneration logic.

**Docker.** WeasyPrint needs Pango, and the image has none of it today (verified: zero pango/cairo
libs in the running container). Add to `backend/Dockerfile`:

```dockerfile
libpango-1.0-0 libpangoft2-1.0-0 libharfbuzz0b libjpeg62-turbo libffi-dev
```

**Fonts.** Self-host two or three families under `static/fonts/` and reference them via `@font-face`.
System font stacks are a trap here: whatever the container has is what the PDF embeds, and it will
differ from a developer's laptop.

---

## 7. Frontend work

```
features/cvBuilder/
├── api/cvApi.js         + getTemplates, getPreviewPdf (responseType:'blob'),
│                          getPreviewMeta, uploadPhoto, deletePhoto, exportPdf
├── api/cvQueries.js     + useTemplates, usePreviewPdf, usePreviewMeta, usePhoto mutations
├── components/preview/
│   ├── PdfCanvas.jsx    pdfjs-dist → <canvas>, page nav, zoom-to-fit
│   └── PreviewPanel.jsx blob lifecycle, loading + error states
└── components/steps/
    ├── TemplateStep.jsx gallery + ATS badges + photo uploader + fit banner
    └── PhotoUploader.jsx drag/drop, client-side preview, 2 MB guard
```

`TemplateStep` becomes a seventh entry in `STEPS`, reusing `SectionShell`, `Badge` and the existing
`template_id` PATCH — no new save path, and it inherits the "Saves automatically" affordance
already built.

The photo uploader renders **only** when the selected template has `photo: true`, so it never
appears as a dead control on the four text-only templates.

Two details worth getting right:

- **Revoke blob URLs** in a `useEffect` cleanup. Preview blobs leak memory fast when switching templates repeatedly.
- **Debounce preview refetch** ~500 ms after `content_updated_at` changes, so autosave in Contact & Summary doesn't trigger a render per keystroke.

---

## 8. Overflow UX

Driven by real `page_count` from `/preview/meta/`:

| Condition | Banner |
|---|---|
| `page_count <= max_pages` | 🟢 "Fits on 1 page" |
| `page_count > max_pages` | 🟡 "Your CV runs to 2 pages on Minimal" + three actions |

The three actions: **keep 2 pages** (fine, and normal for senior candidates) · **switch to Compact**
(with its predicted page count shown) · **see what to trim** (longest bullets, oldest roles).

**Nothing is ever silently dropped.** This is a deliberate departure from spec §9.2, which slices
content to a per-template maximum. Truncating someone's most recent role inside a PDF they are
about to send an employer is the wrong default for a hiring product, and it is invisible at exactly
the moment it matters.

---

## 9. Phasing

| Phase | Scope | Risk |
|---|---|---|
| **0** | Dockerfile system libs, WeasyPrint pinned, `CACHES` → Redis, registry, `template_id` allowlist + `choices` | Infra only, no UI. Unblocks everything. |
| **1** | `build_cv_context`, `base.html`, **`minimal`** only, `/preview/`, `PdfCanvas`, `TemplateStep` with one card | Proves the whole pipeline end to end on one template |
| **2** | `classic`, `technical`, `compact` — three text-only templates | Pure content work once Phase 1 lands |
| **3** | `photo` field + migration + upload endpoint + EXIF stripping + `PhotoUploader` | Isolated; only touches the two photo templates |
| **4** | `modern`, `executive` | The two photo templates |
| **5** | `/export/pdf/`, download, skip-regen, overflow banner | Polish |

Phase 1 is the real milestone — once one template renders identically in preview and download,
every remaining template is HTML and CSS with zero Python.

---

## 10. Testing

There is no test suite in this project at all, and six templates × a rendering pipeline is exactly
where regressions hide silently. Minimum worth adding alongside:

- **Golden-file test per template** — render a fixture CV, assert `page_count` and hash the extracted text. Catches "template silently stopped showing education."
- **Overflow test** — a deliberately oversized fixture must report `page_count > max_pages` rather than truncating.
- **Photo test** — upload a JPEG carrying EXIF GPS, assert the stored file has no EXIF.
- **Traversal test** — `template_id = '../../../etc/passwd'` must 400, not render.

Identity itself needs no test: preview and download return the same cache entry, so there is
nothing that can drift.

---

## 11. Decisions still needed from you

1. **Photo shape** — circle (softer, modern) or square/rounded-rect (more formal)? Affects both templates' CSS.
2. **Prefill from account avatar?** `UserProfile.avatar` exists. Copy it on first open, or always require an explicit CV photo upload?
3. **Font families** — happy with a serif (Classic/Executive) + sans (the rest) pairing, self-hosted? Any brand preference?
4. **Two pages** — allow as a first-class option, or push hard toward one page?

---

## Sources

- [WeasyPrint API reference (69.0)](https://doc.courtbouillon.org/weasyprint/stable/api_reference.html)
- [WeasyPrint changelog — flexbox v66, grid v62](https://doc.courtbouillon.org/weasyprint/stable/changelog.html)
- [WeasyPrint tutorial — `.render()` and `document.pages`](https://doc.courtbouillon.org/weasyprint/stable/api_reference.html)
- [pdfjs-dist with React and Vite](https://www.nutrient.io/blog/how-to-build-a-reactjs-viewer-with-pdfjs/)
- [Vite + pdfjs worker resolution issue](https://github.com/wojtekmaj/react-pdf/issues/1148)
- [Avoiding page breaks inside elements](https://github.com/Kozea/WeasyPrint/issues/683)
