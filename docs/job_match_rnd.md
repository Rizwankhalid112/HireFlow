# Job Match & CV Tailoring — R&D

> Paste a job, pick or upload a CV, see how well it matches, tailor it, get a cover
> letter, download it named after the job.
> Researched 2026-09-08, before any code. This is the argument, not the plan.

---

## 1. The flow, end to end

Six stages. Stage 1 is the one everything else waits on, and it is where the hard
research is (§3).

```
 1  GET THE JOB
    ├─ paste the text            ← always works, no permission needed
    ├─ upload a screenshot       ← always works, needs vision
    ├─ upload a PDF/DOCX of it   ← reuses services/extraction.py as-is
    └─ paste a URL               ← only for sources that allow it (§3)
              │
              ▼   structured output → {title, company, location, seniority,
                                       required_skills[], preferred_skills[],
                                       responsibilities[], raw_text}
 2  PICK THE CV
    ├─ the CV already in HireFlow  (default — this is why the builder exists)
    └─ upload a different one      ← reuses the Step 7-8 upload + parse pipeline
              │
              ▼
 3  SCORE IT
    ├─ Match Score, with its parts shown, not a mystery number  (§4)
    ├─ keywords found / missing / worded differently
    └─ the title-match check — the single heaviest ATS signal   (§4)
              │
              ▼
 4  TAILOR  (optional, user-initiated, per section)
    ├─ reword what is already there to match their language   ← safe, most of the value
    ├─ ask about a missing skill, never insert it             ← the whole ethical line (§5)
    └─ produce a TAILORED VERSION, never overwrite the master (§6)
              │
              ▼
 5  COVER LETTER  (optional)
    └─ grounded in the tailored CV + the job, same anti-invention rules
              │
              ▼
 6  SAVE & DOWNLOAD
    ├─ `ada-lovelace-google-backend-engineer.pdf`
    ├─ the version is kept, so months later you know what you actually sent
    └─ links to the application row once `applications` exists
```

**What the user gets that they cannot get from a spreadsheet:** the same CV scored
against ten jobs in an afternoon, and ten tailored versions they can tell apart.

---

## 2. What this reuses

Almost all of the expensive parts are already built. This module is mostly assembly:

| Existing piece | Used for |
|---|---|
| `services/extraction.py` | A job description uploaded as PDF/DOCX — same code, different content |
| Step 7–8 upload pipeline | "Upload your own CV" is the flow we already shipped |
| `services/ai/` — client, prompts-as-constants, structured outputs | Job parsing, scoring, tailoring, cover letter |
| `guardrails.py` — grounding, `lookup_canonical` | Keyword matching against `SkillCanonical` is the same resolver |
| `AISuggestionLog` metering + `ScopedRateThrottle` | These calls cost real money and must be capped from day one |
| WeasyPrint templates + exact-snapshot preview | The tailored CV renders and downloads through the existing path |
| The three-rung Evidenced / Ask / Never model | §5 is that model applied to keywords |

**The one genuinely new capability is vision** — reading a screenshot (§3.4).

---

## 3. Getting the job description — the real research

The question is not "how do we scrape" but "what are we *allowed* to read, and what
do we do everywhere else". The answer splits into four tiers, and the practical
finding is that **the tier everyone worries about is the one we least need**.

### 3.1 The insight that reorganises this whole problem

**The site showing the job is usually not the site hosting it.** A LinkedIn or
Indeed listing overwhelmingly links out to the employer's applicant tracking
system — Greenhouse, Lever, Ashby, Workable — and *those* publish open APIs.

So the honest framing is: we do not need LinkedIn. We need the posting, and the
posting almost always has a second, permitted home.

### 3.2 Tier 1 — public, documented, no authentication ✅

A small group of ATS platforms expose published jobs through public JSON APIs with
no OAuth, no partner approval, and no per-employer setup:

| Platform | Access |
|---|---|
| **Greenhouse** | `GET https://api.greenhouse.io/v1/boards/{board}/jobs?content=true` — public, documented. No search or filtering, so you need the board token |
| **Lever** | Every Lever customer has a public postings API, no auth |
| **Ashby** | Public posting API |
| **Workable** | Public JSON endpoint per account |
| **SmartRecruiters / Recruitee / Personio** | Same pattern — published JSON or XML feeds |

This is a clean, permitted, free path covering a large share of tech-sector roles.
**Start here.**

### 3.3 Tier 2 — structured data embedded in the page 🟡

Google for Jobs requires `schema.org/JobPosting` **JSON-LD** on the page for a
listing to be eligible, and eligibility drives significant traffic — so a very
large share of job pages carry machine-readable JSON-LD with title, company,
description, salary, location and employment type already structured.

Reading that from a page the user gave us is cheap and needs no parsing heuristics.
The caveat is that it is per-site ToS, not a blanket permission — so this is an
**allowlist**, not a crawler.

The distinction that matters and should be written into the code: a **single
user-initiated fetch of one URL the user is already looking at** is a very
different act from a bulk crawler. We do the former, never the latter.

### 3.4 Tier 3 — prohibited, and not worth arguing about ❌

**LinkedIn. Do not scrape it, and do not buy scraped LinkedIn data either.**

The legal position is widely misreported, so precisely:

- **hiQ won on the CFAA.** The Ninth Circuit held that scraping *public* data is not
  "unauthorized access" — you cannot be criminally liable for reading a public page.
- **hiQ then lost on breach of contract**, in November 2022. LinkedIn's User
  Agreement §8.2 "unambiguously prohibits" scraping — explicitly naming crawlers,
  scripts, browser plugins and add-ons. Outcome: a **$500,000 judgment, a permanent
  injunction, and destruction of the scraped corpus.**
- **This is live, not historical.** In 2026 LinkedIn is pursuing Nubela/Proxycurl —
  a commercial LinkedIn-data API. That is precisely the "we don't scrape, we just
  buy from someone who does" workaround, and it is the thing being litigated.

So "not a crime" and "allowed" are different questions, and only the second one
matters to us. **Indeed** is similarly gated — its API is partner-only.

There is also a data-protection point independent of ToS: the moment we store
personal data of EU or California residents — a named recruiter on a posting, for
instance — GDPR and CCPA obligations attach regardless of how public the source was.

### 3.5 Tier 4 — the fallback, which is really the primary path ✅

**Paste the text, or upload a screenshot.** The user proposed this as the
workaround for blocked platforms. It should be reframed: it is the **default**, and
the tiers above are optimisations on top of it.

Reasons it is the right primary:

- It works for every site on earth, including LinkedIn, with zero legal exposure —
  the user is looking at a page they are entitled to look at and handing us the
  text. We never touch the site.
- It never breaks. An API deprecation or a markup change cannot take it down.
- It is honest with the user about what is happening.

**The screenshot route needs vision, and Claude already provides it.** The research
on OCR is clear enough to settle the choice:

- Tesseract is 4–8× faster and competitive on *clean printed text*, but scores
  near-zero on tables and cannot reason about layout.
- Vision models win decisively on messy input, and — the deciding factor — a job
  page screenshot is typically a **multi-column layout with sidebars, badges and
  navigation chrome**, which is exactly Tesseract's weak case.
- We would then still need a second model call to turn OCR text into structured
  fields.

So: send the image straight to Claude with the same structured-output schema used
for pasted text. **One call instead of two, no new dependency, no OCR tuning.**
Adds an image-token cost per screenshot, which the metering already handles.

### 3.6 Recommendation

```
  Default            paste text  ·  upload file  ·  upload screenshot
  Optimisation       paste a URL → allowlisted ATS API (Tier 1)
                                 → allowlisted page → JSON-LD (Tier 2)
  Never              LinkedIn, Indeed, or any third-party reseller of their data
```

The URL box should say which sources it can fetch and offer paste for the rest,
rather than failing silently on a LinkedIn link — that failure will otherwise be
the single most common support question.

---

## 4. Scoring: what we can honestly claim

The request was "out of 10, what is your percentage to get an interview". **We
cannot answer that, and should not pretend to.**

The evidence is unambiguous. Match score correlates with callback rate, but it
measures *keyword alignment, not job readiness or interview probability*. Better
parsing "increases accuracy at reading resumes; it does not increase accuracy at
predicting performance." We have no callback data, no visibility of the applicant
pool, and no idea who else applied. A number like "7/10 chance of interview" would
be exactly the kind of invented figure this project already refuses to put in a
bullet point — and it would be inventing it about the user's livelihood.

**Score the match, not the outcome. Show the parts, not a mystery number.**

| Component | Why |
|---|---|
| **Required skills matched** — n of m, listed | Hard skills are weighted far above soft skills by real matching |
| **Preferred skills matched** | Secondary, shown separately |
| **Title alignment** | The heaviest single ATS signal: a candidate whose current title matched the posting ranked ~12 positions higher than an equally qualified one whose did not |
| **Terminology gaps** | Skills you *have* but worded differently — the highest-value fix (§5) |
| **Recency** | How recent the relevant experience is |

**Two things to tell the user that most tools do not:**

1. **Aim for roughly 75–85%, not 100%.** Callback rates climb steeply between 60
   and 85 and then flatten above 90. Effort spent past that point buys nothing.
2. **A suspiciously perfect match can be flagged as keyword stuffing.** Pushing to
   100% is not just wasted, it can be actively harmful.

Framing it as a Match Score with visible components is also simply *more useful*: a
breakdown tells you what to fix, a single predictive number tells you nothing you
can act on.

---

## 5. Tailoring: where this module could do real harm

"Update the CV with new keywords so he passes the AI" is the feature, and it is one
step away from writing lies onto a document the user has to defend in an interview.

The rule is the one this codebase already runs on, applied to keywords:

| Case | What we do | Affordance |
|---|---|---|
| **The skill is there, worded differently** — CV says "Postgres", posting says "PostgreSQL"; CV says "led a team", posting says "people management" | **Rewrite to their wording.** No new claim, purely terminology | One-click apply |
| **The skill is absent** | **Ask.** "The posting wants Kubernetes — have you used it?" If yes, ask where, and write it grounded in their answer | A question, never text |
| **The user says no** | Show it as a genuine gap. Do not write it. Optionally suggest how to address it | Listed, not inserted |

The first row is not a consolation prize — it is most of the value. A 2021 Harvard
Business School / Accenture study found **88% of executives believe their own ATS
rejects qualified candidates purely because the résumé does not use the exact
terminology the system was configured to match.** Those people ("hidden workers")
are not unqualified; they are mis-worded. Fixing wording is legitimate, high-impact,
and involves inventing nothing.

**This is the module's equivalent of the fabrication rule**, and it should be as
prominent in the prompt as the anti-invention rule is in the bullets prompt.

---

## 6. The architecture collision — and this is the third time

The whole point of this module is **a different CV per job**, downloaded with the
job's name so the user knows which one they sent. `CVProfile` is **one per user and
mutable**.

This exact tension has now been parked twice:

- The AI suggestions R&D deferred job-description targeting, noting it "pushes
  against the one-CV-per-user model in `CVProfile`, which is a deliberate design
  choice" and calling it a product decision.
- The applications R&D hit it again as "which CV did I send to this job", with the
  same three options and no decision.

**It cannot be deferred a third time — this module is entirely made of it.**

Sketch: the master CV stays the single source of truth, and a tailored CV is a
**frozen version** — a snapshot of the content plus the job it was tailored for.

```
CVProfile  (master, mutable, one per user — unchanged)
    └── CVVersion   (frozen content JSON, job_title, company, created_at, pdf)
            └── used by:  this module's download
                          the applications module's "which CV did I send"
```

Deciding it here settles the applications module's open question for free, which is
a good sign it is the right shape rather than a workaround.

---

## 7. Cost — this module is the expensive one

Every stage is a model call, and one job can be several. Rough per-job, using the
suggestion-module figures as a base (~1¢ per short call, ~7¢ per whole-CV parse):

| Stage | Note |
|---|---|
| Parse the job description | Text: cheap. **Screenshot: image tokens on top** |
| Parse an uploaded CV | Only if they upload rather than use ours — reuses Step 8 |
| Score | Whole CV + whole job in context; not cheap |
| Tailor | Per section, several calls if they work through it |
| Cover letter | One call, longer output |

A user doing ten jobs properly could run **an order of magnitude above** what a
heavy CV-builder user costs today. Consequences:

- Metering is a **prerequisite**, not polish. It gets its own limit, separate from
  `AI_MONTHLY_CREDITS` and `AI_PARSE_MONTHLY_LIMIT`.
- **Score should be cheap and re-runnable; tailoring should be explicit and
  counted.** Users will re-score constantly and tailor rarely.
- Much of scoring is mechanical — keyword resolution against `SkillCanonical` needs
  no model at all. Do the deterministic part first and only spend a call on the
  judgement.

---

## 8. Open questions

1. **`CVVersion` — decide it now** (§6). Everything else depends on the shape.
2. **Does scoring need a model at all,** or is canonical-resolution plus title
   comparison enough for v1? Cheaper, faster, fully explainable.
3. **How many tailored versions can a user keep?** Storage and UI both degrade.
4. **Cover letter: in v1 or v2?** It is the most self-contained piece and the
   easiest to cut.
5. **Which URL sources go on the allowlist first** — Greenhouse and Lever cover the
   most ground for the least work.
6. **Do we show the score before or after asking them to tailor?** Before is honest;
   it also means some users leave at "42%".

---

## 9. Deliberately out of scope

- **Any LinkedIn or Indeed scraping**, and any third-party reseller of it (§3.4).
- **Bulk job ingestion / a job search inside HireFlow.** A different product, and
  the point where per-site ToS stops being a single-fetch question.
- **Auto-apply.** Simplify's territory, needs a browser extension, and it is the
  feature most likely to get a user's accounts banned.
- **Predicting interview probability** (§4) — not deferred, refused.

---

## Sources

- [hiQ v. LinkedIn — user agreements and scraping](https://www.metaverselaw.com/hiq-v-linkedin-user-agreements-in-the-age-of-data-scraping/) · [Is web scraping legal in 2026](https://www.datashake.com/blog/is-web-scraping-legal-what-you-need-to-know-in-2026) · [LinkedIn scraping legal guide 2026](https://sociavault.com/blog/linkedin-scraping-legal-guide-2026) · [LinkedIn API reality check 2026](https://www.socialcrawl.dev/blog/linkedin-data-api-2026)
- [ATS platforms with public job APIs](https://fantastic.jobs/article/ats-with-api) · [6 ATS platforms with public APIs (2026)](https://cavuno.com/blog/ats-platforms-public-job-posting-apis) · [Greenhouse/Lever/Ashby in one call](https://dev.to/quantoracle/scrape-any-companys-job-postings-greenhouse-lever-ashby-with-one-api-call-4db)
- [JobPosting schema for Google Jobs](https://www.jobboardly.com/blog/google-jobs-schema-markup-guide) · [JobPosting JSON-LD required fields](https://schemavalidator.org/guides/job-posting-schema-guide)
- [How ATS systems rank resumes](https://resumeoptimizerpro.com/blog/how-ats-systems-rank-resumes) · [Keyword matching and scoring](https://jobwizard.ai/blog/ats-resume-optimization-part-2-keyword-matching-deep-dive-and-scoring-algorithm-explained) · [The match-score trap](https://blog.theinterviewguys.com/the-match-score-trap-in-2026-your-resume-gets-a-number-before-a-human/) · [Resume matching explained](https://resumeoptimizerpro.com/blog/resume-matching-explained)
- [Vision models vs Tesseract for OCR](https://dev.to/gabrielanhaia/vision-models-for-ocr-when-they-beat-tesseract-and-when-they-dont-54a6) · [OCR accuracy benchmarks 2026](https://fastocr.org/blog/ocr-accuracy-comparison-benchmarks)
