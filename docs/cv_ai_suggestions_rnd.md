# AI Writing Suggestions — R&D and Design

> Per-section AI suggestions in the CV Builder: bullets, summary, skills, project points, title.
> Rendered version: https://claude.ai/code/artifact/334a64f1-e89d-4689-ac0d-25f396a6cccb
> Researched and built 2026-09-03.

---

## 1. What the market ships

| Product | Approach | Notable mechanic | Free limit |
|---|---|---|---|
| **Teal** | Per-bullet, five modes | Automatic · Keywords · Coach Me · Job Description · Custom Prompt; 3 variants per role | 10 bullet + 2 summary credits, one-time |
| **Rezi** | Purpose-tuned writer + ATS score | "Rezi Score" over 23 criteria; names missing keywords by priority and where to put them | Limited credits; $29/mo |
| **Enhancv** | Inline assistant in the editor | Flags weak bullets where they sit; rewrites in place or critiques as a recruiter | Trial |
| **Kickresume** | Per-section generators + re-writer | Section-scoped tools, then a separate AI Re-Writer | Limited; $9/mo |
| **Jobscan** | Match scoring, not writing | Weights **hard skills** far above soft; 75%+ target match rate | Limited scans |

**Five conclusions.** Every serious builder is per-section and the unit is the bullet — nobody
generates a whole CV. Multiple variants, user picks, is the norm. Modes beat one button. Hard skills
outrank soft skills in ATS matching. And everyone meters AI usage.

## 2. Three patterns

- **A — Generate** from a job title alone. **Last resort**: with no user facts, the model must invent.
- **B — Rewrite** what the user wrote. **The default**: their facts constrain the output.
- **C — Critique** without replacing text. **Underrated and cheap** — some of it needs no model.

Leading with A teaches users the AI supplies content and they supply a job title. Leading with B
teaches the opposite. Only the second produces CVs that survive an interview.

## 3. The constraint: fabrication, not generation

72% of recruiters report AI-fabricated applications; Gartner projects 1 in 4 candidate profiles fake
by 2028; 19% of hiring managers think their process would catch one. ATS keyword matching does not
just miss fabrication — it rewards it.

> **The rule everything follows from.** The model may restructure, sharpen, compress and rephrase.
> It may never introduce a fact, number, technology, employer, scope or outcome not present in the
> user's input. Where a fact would strengthen the line, it **asks**.

Every suggestion sorts onto one of three rungs, and this drives the prompt, the schema and the UI:

| Rung | Meaning | Affordance |
|---|---|---|
| **Evidenced** | Traceable to something the user wrote | One-click apply (green) |
| **Ask first** | Would strengthen it, but we lack the fact | A question, never text (amber) |
| **Never** | A figure or claim from nowhere | Not produced at any confidence |

**Content model.** Google's XYZ formula — "Accomplished [X] as measured by [Y] by doing [Z]". Its
value to us is structural: **Y is the slot the model wants to invent**, and naming it lets us detect,
refuse, and ask instead.

## 4. The gap prompt

Input note: *"added redis caching to the api"*.

- **Naive:** "Reduced API latency by **40%** across **12 endpoints** via Redis caching." — two
  invented facts, likely accepted without notice, asked about in an interview.
- **Ours:** "Cut API response latency by introducing a Redis caching layer." plus a chip:
  *"Roughly how much did latency drop?"* → user answers "about half" → regenerate → true and specific.

`services/metric_extractor.py` already existed (7 regexes). Run it on the generated line: **no match
means ask.** Deterministic, free, no model call. Every answered gap is a real fact captured.

## 5. Per-section contracts

| Section | Distinctive input | Output | Guardrail |
|---|---|---|---|
| **Bullets** | Role, company, dates, **the role's other bullets**, the note, skills | 3 variants + gaps | Sibling bullets are shown but are **not** a numeric source (§7) |
| **Summary** | The whole CV — the only true synthesis | 2 variants, 220–420 chars | Every noun traces to CV data |
| **Skills** | All bullet text + all `tech_stack` | Two lists: evidenced / suggested-for-role | Resolved against `SkillCanonical`; no evidence ⇒ demoted, never promoted |
| **Projects** | Name, `tech_stack` (≤10), description | 3–4 independent points + gaps | Never invent users, stars, traffic |
| **Title** | Current title, roles held, skills | 3 normalisations | Never inflate seniority or change discipline |
| **Education/certs** | — | — | Out of scope: purely factual |

## 6. Architecture

```
services/ai/
├── client.py      one Claude call; cache breakpoint, timeout, error mapping
├── prompts.py     constants, one per section — never interpolated
├── context.py     per-section user payload + the fact sources
├── guardrails.py  mechanical grounding, shape, canonical resolution
├── schemas.py     Pydantic structured-output models
└── suggest.py     one entry point per section
```

- **Synchronous, not Celery.** Step 8's CV *parse* is correctly on Celery — slow, one-shot, nobody
  watching. Suggestions are interactive; polling would make them feel worse.
- **Structured outputs.** `messages.parse(output_format=PydanticModel)` returns a validated
  instance. No fence stripping, no `JSONDecodeError` branch. **Step 8 should adopt this too** — it
  deletes several of the edge cases that spec enumerates.
- **Prompt caching.** The system prompt is byte-identical for every user of a section, so the cache
  is shared org-wide. All user data goes in `messages`. `test_ai_prompts.py` guards this, because a
  single interpolated value breaks caching *silently*.

## 7. Two bugs the tests caught during the build

Recorded because both are silent and both would have shipped:

1. **An exact canonical skill name could lose to another skill's alias.** Both were in one `OR`
   query, so the winner was arbitrary. `Java` is a canonical skill *and* a substring of `JavaScript`.
   Fixed: exact match first, aliases only as a fallback, confirmed against the real alias list.
2. **A figure from a sibling bullet licensed a figure in a new one.** The role's existing bullets
   are shown to the model for de-duplication, and were also being treated as fact sources — so a
   "40%" belonging to last year's caching work could silently attach to an unrelated new bullet.
   Fixed: existing bullets stay in the prompt, out of `sources`.

## 8. Cost and quota

Opus 5: $5/MTok in, $25/MTok out, cache read $0.50/MTok, 5-minute cache write $6.25/MTok.

| Request | Cold | Warm (cached prefix) |
|---|---|---|
| Bullets ×3 | $0.0136 | $0.0084 |
| Summary ×2 | $0.0216 | $0.0165 |
| Skills | $0.0181 | $0.0130 |
| Project points | $0.0133 | $0.0082 |
| Title ×3 | $0.0079 | $0.0027 |

**~1¢ per suggestion**; ~20–25¢ for a user who works through a whole CV. Teal's free tier maps to
~12¢ of equivalent inference, so 60 credits/month sits in the right range.

**Throttling was a prerequisite, not polish.** DRF had no throttle configuration at all; an
authenticated endpoint calling a metered API with no rate limit is uncapped billing exposure.
`ScopedRateThrottle` at `20/min` plus a monthly credit count shipped with the first endpoint.

Credits are **counted from `AISuggestionLog` rows**, not decremented from a counter — a drifting
counter is unrecoverable, a count can always be recomputed.

## 9. Deliberately not built

- **Job-description targeting** (the R&D doc's Phase 4). It is the largest piece and it pushes
  against the one-CV-per-user model in `CVProfile`, which is a deliberate design choice. That
  tension is a product decision, not an implementation detail.
- **Education and certification suggestions** — the fields are factual; there is no writing to improve.

## 10. Open questions

- Does the free tier get credits at all? The rest of HireFlow has no billing concept; this feature
  introduces the need for one.
- Per-application tailoring vs. the single master CV.
- Accept rate per section is the honest quality signal. `AISuggestionLog.accepted_index` records it
  from day one — nothing else can reconstruct it later.

## Sources

- [Teal bullet generator](https://www.tealhq.com/tool/resume-bullet-point-generator) · [Rezi](https://www.rezi.ai/ai-resume-builder) · [Enhancv](https://enhancv.com/ai-resume-builder/) · [Kickresume](https://www.kickresume.com/en/ai-resume-summary-generator/) · [Jobscan match rate](https://www.jobscan.co/blog/what-jobscan-match-rate-should-i-aim-for/)
- [Resume.io — XYZ format](https://resume.io/blog/xyz-resume-format) · [Enhancv — STAR method](https://enhancv.com/blog/star-resume-template/)
- [Skillfuel — AI fake resumes](https://www.skillfuel.com/ai-fake-resumes-recruiters/) · [Treegarden — AI resume detection](https://treegarden.io/blog/ai-generated-resume-detection/)
- [Claude API pricing](https://platform.claude.com/docs/en/about-claude/pricing)
