# CV Templates — R&D

> Design study for template selection, live preview, and PDF export.
> No code written yet. Decisions here feed spec Step 9.
> Researched 2026-08-18 against the current codebase.

> **⚠️ §2 and §3 are superseded by [cv_templates_build_plan.md](cv_templates_build_plan.md).**
> The requirement became "preview and PDF must be pixel-identical." Option C below (browser
> renders the preview, WeasyPrint renders the PDF) cannot guarantee that — two layout engines
> produce different line breaks, which cascade into different page breaks. The build plan renders
> once and shows that render. The template lineup in §4 also changed: six templates with exactly
> two carrying a photo. The rest of this document (ATS reasoning, security findings, phasing
> logic) still stands.

---

## 1. What we're solving

Six selectable templates, shown in a picker tab. The user picks one, and after finishing the
builder we render their CV in it. Each template has a different content capacity, so nothing
overflows or breaks.

Three sub-problems, and they're independent — worth solving in this order:

1. **Where does a template live** (one source of truth for screen and PDF)
2. **How we stop content overflowing** (the "word count" question)
3. **How the picker and preview feel**

---

## 2. The central decision: one template, two renderers

A template has to appear in two places — a live preview on screen, and a PDF. How we split that
is the decision everything else hangs off.

| Option | How | Verdict |
|---|---|---|
| **A. Two implementations** | React components for preview, Django templates for PDF | ✗ 6 templates × 2 = 12 implementations that drift. Every fix lands twice. Reject. |
| **B. Server renders everything** | Preview is a WeasyPrint PDF/PNG in an iframe | ✗ One source of truth, but 200–800 ms per preview and no live feel. Heavy for a picker where users browse. |
| **C. Shared HTML+CSS, two renderers** | One Django template + one stylesheet. Browser renders it for preview; WeasyPrint renders the same files for PDF | ✓ **Recommended** |
| **D. Headless Chrome for PDF** | Playwright renders the same HTML | Perfect parity by construction, but ~400 MB image and slow cold starts. Keep as the escape hatch. |

### Why C is viable now (it wouldn't have been two years ago)

The historic objection to sharing CSS was that WeasyPrint couldn't do modern layout. That's no
longer true:

- **Flexbox is fully supported** — all `flex-*`, `align-*`, `justify-*`, `order`, the `flex` and `flex-flow` shorthands, and `gap` in flex since v65.
- **CSS Grid landed in v62** and covers realistic layouts; subgrid and complex `grid-template-areas` are still partial.
- Current stable is **69.0** (June 2026).

So the browser∩WeasyPrint intersection is now big enough to build real layouts in. The house rule
becomes: **flexbox for layout, grid only for simple row/column cases, no subgrid.**

### How preview works under option C

`GET /api/cv/preview/?template=<id>` returns **HTML, not PDF**. The frontend drops it into a
sandboxed iframe:

```jsx
<iframe srcDoc={html} sandbox="" title="CV preview" />
```

Sized to A4 at 96 dpi (794 × 1123 px) and scaled to the panel with `transform: scale()`. That
gives a true WYSIWYG page at effectively zero server cost — no WeasyPrint call to preview.

**This decouples preview from PDF entirely**, which is the most useful consequence: we can ship
the picker and preview without installing WeasyPrint at all (see §7).

---

## 3. The overflow problem — and why I'd not do what the spec says

Spec §9.2 defines hard caps per template (Minimal: 4 experiences / 12 skills) and says to
slice to that maximum in `build_cv_context()`.

**I'd push back on this.** Two reasons:

**Item counts are a poor proxy for space.** Four roles with eight bullets each overflows badly;
six roles with one bullet each doesn't come close. The thing that consumes a page is rendered
lines, not entries.

**Silent truncation is the wrong default.** Dropping someone's most recent job because they picked
the wrong template is a bad outcome in a job-application product — and it's invisible in a PDF
they're about to send to an employer.

### Proposed instead: a capacity model

Estimate rendered lines rather than counting items:

```
lines(experience) = 1 (role/company) + 1 (dates/location)
                  + Σ ceil(len(bullet) / chars_per_line)
lines(skills)     = ceil(count / skills_per_row)
...
```

`chars_per_line`, `lines_per_page`, and `skills_per_row` are per-template constants derived from
column width and font size — measured once when the template is built, stored in its registry
entry.

Sum every section → estimated lines → compare against `lines_per_page × max_pages`. Then respond
in three tiers:

| Fill | State | Behaviour |
|---|---|---|
| < 85% | 🟢 Fits | "Fits on 1 page" |
| 85–100% | 🟡 Tight | Offer auto-fit: nudge font-size/line-height within a floor (≈9.5 pt) — what commercial resume builders actually do |
| > 100% | 🔴 Overflows | Name exactly what spills, then offer three choices: allow 2 pages · trim suggestions · switch to a denser template |

**Never drop content without the user choosing it.** If we keep caps at all, they warn — they
don't slice.

The capacity numbers live in the template registry, so the frontend can show a live fit meter as
the user edits and the backend can re-check before rendering. One source, two consumers.

Worth remembering that **two-page CVs are normal** for anyone senior. Fighting to one page should
be an option, not a constraint. `break-inside: avoid` on each entry keeps items from splitting
across the page boundary.

---

## 4. The six templates

Templates should differ **structurally**, not just by colour — otherwise they're skins. Proposed
axes: column count, type family, density, emphasis.

| # | Template | Layout | Density | ATS | Photo | For |
|---|---|---|---|---|---|---|
| 1 | **Minimal** | 1 col, generous whitespace | Low | ✓ | ✗ | Early career, 1 page |
| 2 | **Classic** | 1 col, serif, traditional headers | Medium | ✓ | ✗ | Conservative industries |
| 3 | **Modern** | 2 col — contact + skills sidebar | Medium | ✗ | ✓ | Design, product, startups |
| 4 | **Technical** | 1 col, skills grid up top | High | ✓ | ✗ | Engineers with long stacks |
| 5 | **Compact** | 1 col, tight leading, 2-col skills | Very high | ✓ | ✗ | 10+ years onto one page |
| 6 | **Academic** | 1 col, thesis/publications emphasis, multi-page | Medium | ✓ | ✗ | Research, PhD |

### The ATS point matters more than it looks

Two-column layouts (Modern) break many applicant tracking systems: text extraction reads straight
across the page, interleaving sidebar and main content into nonsense. In a product whose whole
purpose is getting people hired — and whose Module 9 scores CV/job match — shipping a
pretty-but-unparseable default would be self-defeating.

Recommendation: **label ATS-safety in the picker**, default to Minimal, and put a quiet warning on
Modern. It's exactly the kind of thing users can't discover on their own.

---

## 5. Two things in the current code to fix first

**`template_id` has no validation.** It's `CharField(max_length=50, null=True, blank=True)` with no
`choices`, and it's freely writable through `CVProfileWriteSerializer`. Combined with the template
path the spec suggests:

```python
template_name = f'cv_templates/{cv.template_id or "minimal"}.html'   # spec §9.3
```

…a client can PATCH `template_id` to a traversal string and steer `render_to_string` at another
template. **Resolve `template_id` through a registry allowlist and never interpolate it into a
path**, and add `choices` to the field. Worth fixing when we touch this regardless of templates.

**WeasyPrint needs system libraries the image doesn't have.** I checked the running backend
container: **zero** pango/cairo libs present. `backend/Dockerfile` installs only `gcc` and
`libpq-dev`. WeasyPrint needs Pango, and adding it means an apt layer:

```dockerfile
libpango-1.0-0 libpangoft2-1.0-0 libharfbuzz0b libffi-dev
```

That's a real infra task, not a `pip install`. It's also the strongest argument for shipping
preview before PDF.

---

## 6. Shape of the implementation

**Registry** — one dict, the single source of truth, exposed to the frontend:

```python
CV_TEMPLATES = {
  'minimal': {
    'name': 'Minimal',
    'file': 'cv_templates/minimal.html',
    'columns': 1, 'ats_safe': True, 'photo': False,
    'capacity': {'lines_per_page': 46, 'chars_per_line': 96,
                 'skills_per_row': 4, 'max_pages': 1},
  },
  ...
}
```

`GET /api/cv/templates/` returns it. The frontend renders the gallery and the fit meter from that
response, so adding a template is backend-only.

**Data contract** — one `build_cv_context(cv)` producing a flat dict every template consumes.
Templates never touch the ORM. Adding a template = HTML + CSS + registry entry, **zero Python**.

**New endpoints:**

| Method | Path | Returns |
|---|---|---|
| GET | `/api/cv/templates/` | Registry (name, flags, capacity, thumbnail) |
| GET | `/api/cv/preview/?template=<id>` | Rendered HTML for the iframe |
| PATCH | `/api/cv/profile/` | Already exists — `template_id` is already writable |
| POST | `/api/cv/export/pdf/` | Phase 2 — Celery + WeasyPrint |

**Thumbnails** — don't screenshot at runtime. Commit six static SVG wireframes; they're smaller,
theme-able, and never go stale in a way that matters.

**Frontend** — a seventh step, `TemplateStep`, plus a preview panel:

```
features/cvBuilder/
├── api/          + getTemplates, getPreview
├── components/steps/TemplateStep.jsx    gallery + ATS badges + fit meter
└── components/preview/CVPreview.jsx     sandboxed A4 iframe
```

Reuses `SectionShell`, `Badge`, and the existing `template_id` PATCH — no new save path.

---

## 7. Suggested phasing

**Phase 1 — Templates + preview (no PDF).** Registry, `build_cv_context`, six HTML/CSS templates,
preview endpoint, picker tab, iframe preview, capacity meter. Touches no Docker config and no new
Python dependency. Ships the entire visible feature: the user picks a template and sees their CV.

**Phase 2 — PDF export.** Dockerfile system libs, WeasyPrint, Celery task, `/export/pdf/` +
status + download, skip-regen via the existing `pdf_generated_at` vs `content_updated_at` fields
(already on the model).

**Phase 3 — Fit refinement.** Auto-fit typography, per-section overflow hints, "what if I switched
template" comparison.

Phase 1 is the bulk of the user-visible value and carries almost none of the infra risk. If
WeasyPrint fidelity later disappoints, swapping in Playwright (option D) changes only Phase 2 —
the templates themselves are untouched, because they're just HTML and CSS.

---

## 8. Open questions

- **Photo support** (Modern) — no avatar field exists on `CVProfile`. `UserProfile.avatar` does exist; reuse it or add one?
- **Fonts** — Google Fonts need embedding for PDF. Ship 2–3 self-hosted families, or stay with system stacks?
- **`max_pages`** — enforce, or advisory only? I lean advisory, per §3.
- **Do we persist the chosen template before the CV is complete?** `template_id` is already writable, so picking early is free — probably let them browse from day one.

---

## Sources

- [WeasyPrint API reference (69.0)](https://doc.courtbouillon.org/weasyprint/stable/api_reference.html)
- [WeasyPrint changelog — flexbox/grid version history](https://doc.courtbouillon.org/weasyprint/stable/changelog.html)
- [WeasyPrint flexbox layout internals](https://deepwiki.com/Kozea/WeasyPrint/3.4-flexbox-layout)
- [WeasyPrint vs wkhtmltopdf, 2026](https://pdf4.dev/blog/weasyprint-vs-wkhtmltopdf)
- [Tips and tricks for generating PDFs with WeasyPrint](https://www.naveenmk.me/blog/weasyprint/)
- [Avoiding page breaks inside elements (Kozea/WeasyPrint #683)](https://github.com/Kozea/WeasyPrint/issues/683)
