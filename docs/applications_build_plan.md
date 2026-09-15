# Applications Module — Complete R&D

> The job application tracker. This is the build-ready design.
> Rewritten 2026-09-15 after a five-agent parallel research pass.
> Supersedes the earlier draft of this file. Background survey:
> [applications_rnd.md](applications_rnd.md).

---

## 0. Read this part if you read nothing else

Two findings reframe the whole module, and both argue against the obvious plan.

### The board is not the product

From a 294-comment Hacker News thread on job trackers:

> *"The hard part of job interviewing is learning all the useless Leetcode and
> preparing the stories… Not the tracking."*

And on who pays:

> *"As a currently not employed person… I have no income."*

**A tracker's value is orthogonal to the user's actual suffering, and its buyer is at
their least able to pay.** Building a prettier Kanban board competes on the axis users
say they do not care about. Every competitor has a good board already; none of them is
loved for it.

The defensible ground is **capture quality, automatic state detection, and honest
handling of money and data**. That is where every competitor is weak, and two of the
three we are already positioned for.

### Nobody in the category does the obvious things

| Gap | State of the market |
|---|---|
| **Reading your email** | No major tracker does. The entire email-parsing category is indie and open-source |
| **A clock on ghosting** | Ghosting is the defining experience of a 2026 search. Huntr, Teal, Simplify and Careerflow have **no staleness detection**. Only indies do — Ghoster at 10 business days, JobSnap at 14. *One partial exception:* a user review reveals **Eztrackr auto-moves ghosted cards after 30 days** — undocumented anywhere on their site |
| **Resume version → outcome** | They store the resume *and* the outcome on every record and **never join them**. Huntr's own cohort data proves tailoring takes interview rate from **2.07% to 4.23%** — and no product tells you your own number |
| **Importing your spreadsheet** | Only Careerflow has it. Huntr, Teal and Simplify can all export and none can import |
| **Assessments / take-homes** | A universal step in tech hiring. Nobody models it |
| **Analytics** | **Teal ships none.** Careerflow ships two charts. Marketing at both promises "response rates and more" |

---

## 1. Corrections to what this document previously said

Three things I had wrong. They are recorded rather than quietly edited, because each
was stated confidently.

### ❌ "Referrals convert ~30%" — wrong by about 4×

The 30% figure is the referral **share of hires**, not a referred applicant's chance of
being hired. Computed from Jobvite's own table (13.0M applications, 212K hires):

| Source | Apply → hire | Apps per hire |
|---|---|---|
| Job boards | **0.65%** | 154 |
| Company career site | 1.39% | 72 |
| Agency | 4.68% | 21 |
| **Referral** | **7.82%** | 13 |
| **Recruiter-sourced** | **11.10%** | 9 |

Confirmed independently by [Brown, Setren & Topa, *Journal of Labor Economics* 2016](https://www.journals.uchicago.edu/doi/10.1086/682338)
(62,127 applications, 315 positions): referrals are **6.1% of applicants but 27.3% of
offers** — which is exactly where the myth is born. Per-applicant, a referral is
**+7.3pp on interview** and **+2.4pp on offer**, both p<0.01.

**Honest claim: a referral roughly doubles interview odds and triples offer odds, from a
low base.** Never "30%".

Two riders: **recruiter-initiated outreach (11.1%) beats referrals**, and the referral
effect is *stronger for executives* and sometimes reversed for junior staff — so no
uniform multiplier.

### ❌ "The reliable email filter is the ATS sender domain" — backwards

I claimed we were well placed because `@greenhouse.io`, `@lever.co`, `@ashbyhq.com` and
`@workable.com` are the four platforms we ingest. In fact:

- **Greenhouse requires domain verification** and then sends under the *customer's*
  domain via a `gh-mail` subdomain
- **Ashby** recruiters send from their own company address via Email Sharing
- **Workable** sends through the company's Google/M365

Only *machine-generated* mail carries the ATS domain. **The rejections, interview invites
and offers — the emails that matter — come from the employer's domain.** A sender-domain
filter catches the worthless confirmations and misses every stage transition.

**But the research found something better** (§6): we hold `Job.apply_url`, and ATS emails
contain a link to the posting. **URL → exact `(source, external_id)` match**, where every
competitor does fuzzy company+title guessing. Nobody else can do this, because nobody
else holds the job rows.

### ❌ "Email integration is out of scope — OAuth, privacy, its own project"

Wrong because I assumed OAuth was the only mechanism. **Forwarding needs no inbox access
at all** and avoids Google's restricted-scope CASA security assessment entirely. It moves
to phase 2 (§6).

---

## 2. What the market actually ships

| | Huntr | Teal | Simplify | Careerflow |
|---|---|---|---|---|
| **Stages** | Wishlist, Applied, Interview, Offer, Rejected — **fully customisable** | Bookmarked → Applying → Applied → Interviewing → Negotiating → Accepted, + 5 close sub-statuses — **fixed** | Saved, Applied, Interviewing, Offer, Rejected — **fixed** | 5 fixed + **up to 5 custom lanes** |
| **Capture** | Chrome only | Chrome only, desktop only | Chrome/Edge/Brave/Arc, Firefox beta | Chrome only, 77 named boards |
| **Import** | ❌ | ❌ | ❌ | ✅ Excel template |
| **Interview rounds** | Activities | ✅ Real model: date, type, format, interviewer, round | ❌ | ❌ |
| **Reminders** | **Daily/weekly email digest only** | Date fields, no documented delivery | — | Email on follow-up date |
| **Analytics** | Funnel + conversion %, cohort benchmarks | **None** | Flow chart | Two charts |
| **Price** | $40/mo | $13/wk · $29/mo | $19.99/wk · $39.99/mo | $8.99/wk · $23.99/mo |

**Everyone's marketing contradicts their own documentation on auto-apply.** Teal's page
says "automatically populate and submit"; its knowledge base says "Teal does not submit
job applications on your behalf." Same split at Simplify.

**Mobile is abandoned across the category** — Huntr's iOS app last updated September 2024,
Teal has none, Teal's extension last updated June 2025.

---

## 3. The decisions

### 3.1 Stages — five, fixed, and this is a constraint not a default

```
saved → applied → screening → interview → offer
                                   ↓
                    rejected  ·  withdrawn        (terminal)
```

The evidence for holding the line:

> *"Creating 15 statuses leads people to stop updating them accurately."*
> *"Trackers fail when there's no next action — people need clear direction, not just records."*
> *"The best job tracking system isn't the one with the most features — it's the one you actually use."*

**Every analytic we plan depends on data the user keeps maintaining**, so adoption is
upstream of everything. Pressure to add stages should be refused.

**The granularity that funnel analysis needs lives in `Interview` child rows, not board
columns.** A recruiter screen, a take-home assessment, a hiring-manager call and an onsite
are four `Interview` records against one application in the `interview` stage. This also
fills the **assessment gap nobody in the market covers** — an OA is an interview round of
type `assessment` — without a sixth column.

### 3.2 Ghosting — derived, never stored

97% of applications never reach interview and most go silent. Users will never drag those
cards themselves, so a tracker that waits for them fills with stale rows.

Thresholds found: Ghoster **10 business days**, JobSnap **14 days**, practitioner guides
**21 days**. The hard evidence is stronger than any of them: employer contact hazard is
**essentially exhausted by 30 days**, with most contact inside 14 ([Kline, Rose & Walters,
*QJE* 2022](https://www.nber.org/papers/w29053) — 83,000 applications, 108 Fortune 500
firms), and Ashby's 54M-application dataset shows the **median non-interviewed candidate
archived at 6 days, 58% within 9**.

**Decision: `is_ghosted` computed at 21 days in `applied` with no inbound contact,
configurable.** Derived values cannot go stale and cost the user nothing to maintain.

**The honesty point that matters:** only **4% of companies contact all rejected
applicants** ([Greenhouse, 2024](https://www.greenhouse.com/blog/greenhouse-2024-state-of-job-hunting-report)).
Absence of rejection is not evidence of life. A tracker showing "in progress" on a 40-day-old
application is lying to the user.

### 3.3 Which CV was sent — attach the document

Both Teal and Huntr attach the actual file per application; neither versions the CV. That
is what users want — the PDF they sent, to re-read before the interview.

We already render exact-snapshot PDFs, so this is storing a file we produce anyway. It
also avoids reopening the one-CV-per-user design the builder rests on.

**And it unlocks the gap nobody fills.** Huntr's cohort data proves tailored resumes
interview at **4.23% vs 2.07%** — yet no product tells a user *their own* rate by resume
version, despite storing both halves. With `ApplicationDocument` linked to `JobMatch`, we
can — subject to §5's sample-size rules.

### 3.4 No AI in this module

Creating, moving and querying applications is CRUD; the analytics are counting. Module 1
already covers the AI-shaped work. A model call here would cost money per action and buy
nothing.

---

## 4. Schema

> **Every stage change is an append-only row with a timestamp, from day one.**

**A competitor demonstrates precisely why.** Careerflow's job timeline carries a limit
visible only in their shipped JavaScript and documented nowhere:

> *"Timeline supported for jobs created after 26 May 2023."*

They added history late. Every older card has a **permanently blank timeline** — the
events were never written, and cannot be reconstructed. Careerflow also stores a
**separate timestamp column per stage** (`appliedDate`, `interviewingDate`…), which cannot
represent a stage being re-entered and is why their analytics is two charts.

```
Application
    user, job (FK → Job, nullable, SET_NULL), job_match (FK, nullable)
    company_name, role_title, location, job_url
    source                      cold / career_site / referral / recruiter / agency
    referral (bool) + referral_contact          ← §5: highest-value analytic field
    stage, applied_at, salary_text, notes
    next_action, next_action_at                 ← §5.3
    created_at, updated_at

ApplicationEvent            append-only. never updated, never deleted.
    application, from_stage, to_stage, note, created_at (indexed)

ApplicationDocument         the CV/cover letter actually sent
    application, kind (cv|cover_letter), file, job_match, created_at

ApplicationContact          name, role, email, linkedin
Interview                   round, kind (screen|assessment|technical|hm|onsite|final),
                            scheduled_at, format, outcome, notes
```

`job` is **nullable and `SET_NULL`** — the jobs table purges after 45 days and a closed
listing must never delete the user's record of having applied. Denormalised
`company_name` / `role_title` are what survive and what we display.

**Enforcing append-only** — three levels, and the middle one is the best value:

| Level | Cost | Guarantee |
|---|---|---|
| Application discipline | zero | **Zero.** `queryset.update()`, admin, migrations all walk past it |
| **Restricted DB role** (INSERT+SELECT, no UPDATE/DELETE) | a second role in settings/CI/dev | Strong; owner still bypasses |
| `django-pgtrigger` `Protect(Update\|Delete\|Truncate)` | ~0.4–4% on writes | Tamper-**evident**, not tamper-proof — the owner can `DISABLE TRIGGER` |

Include `Truncate` explicitly: BEFORE UPDATE/DELETE triggers **do not fire on truncate**.

---

## 5. Analytics, and the honesty rules that constrain them

### 5.1 The number that governs the whole surface

> **A perfectly average candidate has a 42% chance of zero interviews after 12
> applications.**

At 0 of 12, the 95% confidence interval on the true rate is **0% – 26.5%** — an interval
that contains both the 7% benchmark and the 24% experimental ceiling. There is no finding.

| Observed | 95% CI |
|---|---|
| 0 / 12 | 0.0% – **26.5%** |
| 0 / 30 | 0.0% – 11.6% |
| 0 / 50 | 0.0% – 7.1% |
| 7 / 100 | 2.9% – 13.9% |

### 5.2 Hard thresholds

| Claim | Minimum n |
|---|---|
| "Your rate is below the 7% benchmark" | **42 applications** with 0 interviews |
| Report a personal rate to ±5pp | **~100 applications** |
| A/B two CV versions, detect a *doubling* at 80% power | **600 applications** |

**Consequences, to be enforced in code:**

1. **Suppress every conversion rate below n = 30.** Show raw counts and pipeline age.
2. **Never show a personal rate without its interval.** "0% (0 of 12)" is a lie of
   precision. "0 of 12 — too few to tell; average candidates hit this 42% of the time" is
   true and is also *reassuring*, which matters (§5.4).
3. **Do not build CV A/B testing.** An individual will never reach 600 applications.
   Flagged by the research as "the most tempting and most dishonest feature you could
   build". We can still report §3.3's per-version counts — as counts, not as a verdict.
4. **Below threshold, report behavioural inputs, not outcomes** — source mix, referral
   rate, stage age, fit gap. All readable at n = 1, and all things the user controls.

### 5.3 What to measure instead

**Source mix and referral rate are the highest-value fields in the module**, because the
measured spread between channels (0.65% → 7.82% → 11.10%) dwarfs every other lever, and
both are behavioural inputs readable immediately.

**`next_action_at` is load-bearing, not a convenience.** It is what stops abandonment —
*"trackers fail when there's no next action"* — and following up carries a **~2.5×
response lift**. It is also exactly the input the `notifications` module needs, turning
that module from "invent a reminder policy" into "read this column".

### 5.4 Do not tell users to apply less

There is **no rigorous evidence that volume hurts outcomes.** The best data is a
meta-analysis of **378 samples, N = 165,933** ([van Hooft et al., *JAP* 2021](https://api.semanticscholar.org/graph/v1/paper/DOI:10.1037/apl0000675)):
search intensity predicts interviews at r = **.23** (~5% of variance) and predicts
employment *quality* at **zero**. Volume buys a little; it does not hurt.

Huntr's own cohort data shows interview rate *falling* with volume (9.25% at 11–20
applications → 2.58% at 100+) — but that is almost certainly **reverse causality**: people
apply more *because* they are not getting responses. Do not ship that claim.

**And feedback that lowers confidence measurably reduces action.** Job-search
self-efficacy moderates the intention→behaviour link — slope **0.508** for high-efficacy
seekers versus **0.201** for low. Rejection counts, declining-rate charts and
"you're below average" comparisons attack the one variable that predicts whether the user
keeps going — and at realistic sample sizes those comparisons are not even valid.

---

## 6. Email capture — phase 2, rejection detection first

**The forwarding model needs no inbox access.** The user sets one mail filter forwarding
job mail to an address we own. No OAuth token, no Gmail scope, and therefore **no CASA
security assessment**.

### Architecture

**AWS SES → S3 → EventBridge → Celery.** ~$0.10 per 1,000 emails, no monthly minimum,
raw unmodified MIME, envelope-`RCPT TO` matching (correct for forwarded mail),
`Authentication-Results` verdicts, EU receiving regions — and **S3 is durable**, so a bad
deploy delays processing instead of destroying mail.

**Do not use SendGrid Inbound Parse.** On failure it drops mail after 72h with **no bounce
to the sender and no dashboard notification**. Silent loss is disqualifying for a feature
whose entire pitch is "we catch what you'd miss".

### Matching, in descending reliability

1. **ATS job URL in the body → `(source, external_id)`.** Exact. Unique to us.
2. **`In-Reply-To` / `References` → a `Message-ID` we have seen.** Survives auto-forward.
3. **Per-application reply addresses** (`<id>@inbound.workablemail.com`).
4. **Sender registrable domain → company.** Now the *primary* company signal (§1).
5. Company + normalised title fuzzy match — last resort, and **never auto-creates**.

### What to attempt, in order

**Rejections only, first.** Extraction reliability is highest (predictable phrasing:
"unfortunately", "regret to inform", "not selected"), it is the transition users never
record themselves, and it fixes the stale-board problem that kills trackers. Published
classifiers reach ~80%; a two-stage prompt beats a single call.

**Never auto-create, only auto-update, and only on an exact match.** Everything else goes
to a review queue.

### Known blockers, stated in the UI rather than discovered

- **Corporate Microsoft 365 users are largely unservable** — external forwarding has been
  off by default for new tenants since 2021, and the rule still *looks* enabled in Outlook
  while the server ignores it.
- **Gmail auto-forwarding excludes spam**, so a rejection in the spam folder is invisible
  to us and we cannot detect the gap.
- **Gmail requires verifying the forwarding address.** We own the destination, so we can
  auto-confirm server-side — the `vf-` link needs a **POST**, not a GET. This turns a
  7-step setup into ~4 and is the highest-leverage UX decision in the feature.
- **Job-alert newsletters must be denylisted before any model call**, or the tracker fills
  with jobs the user never applied to. Never create from a message carrying
  `List-Unsubscribe`.
- **The inbound address is a bearer secret.** High-entropy local part, and require
  `X-Forwarded-For` plus a passing DKIM signature before auto-updating anything.

### Privacy — this needs real work, not a checkbox

We would be a **controller**, not a processor. Recruiter names in forwarded mail are
personal data of people who never consented, so:

- **Lawful basis is Art. 6(1)(f) legitimate interests** for the recruiter's data, and the
  balancing test must be **written down before launch**, not reconstructed after a complaint.
- **Art. 14 applies** — data not obtained from the subject. We will not email every
  recruiter, so the shelter is Art. 14(5)(b) disproportionate effort, which **requires
  compensatory measures**: a findable public notice page explaining what we receive and how
  to object.
- **The household exemption does not help us** — it covers the user's personal activity,
  never the platform.
- **Special-category risk is live.** Recruitment mail routinely carries accommodation
  requests, health disclosures and EEO monitoring (Art. 9).
- **Retain raw MIME ≤30 days**, extracted fields beyond that — and say so. Competitors set
  a low bar here: Huntr retains "as long as necessary"; Careerflow has **no self-serve
  account deletion** and batches deletions monthly, which one reviewer called "borderline
  negligent".

A DPIA is likely required and is cheap insurance; it also forces the retention decision.

---

## 7. Engineering choices

| Area | Decision | Why, and what we accept |
|---|---|---|
| **Card ordering** | Postgres **`NUMERIC` position**, server computes the midpoint from neighbour ids the client sends | A 64-bit float survives only **~50 successive midpoints** before neighbours become equal — and "drag to top of Screening" fifty times is not hypothetical. `NUMERIC` is arbitrary-precision, sorts natively, and needs none of LexoRank's machinery. Accepted: no offline key generation, which a single-user board does not need. **Do not** unique-constrain `(stage, position)` — swapping two rows then needs a deferrable constraint |
| **Drag and drop** | **`@dnd-kit/core` v6, pinned, behind a one-file adapter** | `react-beautiful-dnd` was **archived August 2025**. Atlassian's replacement ships **no keyboard dragging by design**, and retrofitting accessibility is the most expensive thing to add later. Accepted: dnd-kit v6 is frozen at Dec 2024 and its successor is 0.x with the roadmap question unanswered — hence the adapter |
| **Optimistic updates** | Write in `onMutate` only. **Never reconcile from `onSuccess`.** No per-mutation snapshot. Invalidate in `onSettled` **gated on `isMutating(key) === 1`** | An earlier mutation's invalidation returns board state without the later move and reverts it. Snapshot rollback is actively wrong under concurrency — restoring A's snapshot wipes B's unrelated move. Careerflow ships a stale-board recovery path, so this race is real in production |
| **Stage machine** | `django-fsm-2` for `protected=True`, inside `transaction.atomic()` **plus `select_for_update()`** | `django-fsm` was **archived October 2025**. `atomic()` alone is not enough: Django runs at Read Committed, so two transitions can both read `screening` and both write. Note a `@transition` changes the field **in memory only** — you must still `save()` |
| **Rendering** | **No virtualisation.** `React.memo` + a single `DragOverlay` + per-column cap | Virtualisation fights the drag layer — rows **unmount mid-drag** when scrolled out. Revisit only past ~1,000 cards in one column |

---

## 8. Build plan

**Day 1 — the spine** (no UI)
1. `Application` + `ApplicationEvent`, the event written in the same transaction as any
   stage change, with `select_for_update()`
2. CRUD API plus a **dedicated stage-change endpoint** — moving stage is not a generic
   PATCH, it is the thing that writes history
3. Creation from a `Job` and from a `JobMatch` — the one-click paths Module 2 unlocked
4. Derived `is_ghosted`, filters, pagination
5. Append-only enforcement: restricted role + `pgtrigger.Protect`
6. Tests

**Day 2 — the board**
7. Kanban over the five stages, `dnd-kit` behind an adapter, optimistic move
8. Table view with sort and filter — *"please remove sorting before re-ordering"* is a
   real constraint Careerflow ships; decide it deliberately
9. Application drawer: details, documents, contacts, interviews, event timeline
10. "I applied to this" on `/jobs` and on a job match

**Then, in value order**
Documents (§3.3) → **CSV import** (the whole market lacks it) → contacts and interview
rounds → `notifications` reading `next_action_at` → `analytics` reading
`ApplicationEvent`, under §5's rules → email capture (§6).

---

## 9. Out of scope

- **OAuth inbox access** — permanently. Forwarding gets most of the value for a fraction
  of the privacy surface.
- **Auto-apply.** Teal acquired Ramped in Dec 2025 and has not shipped it 9 months later;
  the bot-led version generated exactly the relevance complaints that predicts.
- **CV A/B testing** — statistically impossible at individual scale (§5.2).
- **Offer comparison, referral sourcing, mobile apps** — each a separate category.

---

## 10. What still needs a human decision

1. **Ghosting threshold** — 21 days recommended; the evidence spans 10–30.
2. **Is email capture in the roadmap at all?** It is the largest gap in the market and the
   thing we are best positioned for, but it carries the GDPR work in §6.
3. **`.docx` export.** Teal's most-cited product complaint is PDF-only — *"I couldn't fix
   them"* — and we are PDF-only too.
4. **Do we publish cohort benchmarks** the way Huntr does? It is their most defensible
   asset, and we would need a user base first.

## Sources

Compiled from five parallel research passes. Principal primary sources:
[Jobvite 2019 Benchmark Report](https://web.jobvite.com/rs/328-BQS-080/images/2023-01-2019RecruitingBenchmarkReport.pdf) ·
[Kline, Rose & Walters, QJE 2022](https://www.nber.org/papers/w29053) ·
[Brown, Setren & Topa, JLE 2016](https://www.journals.uchicago.edu/doi/10.1086/682338) ·
[van Hooft et al., JAP 2021](https://api.semanticscholar.org/graph/v1/paper/DOI:10.1037/apl0000675) ·
[Ashby Talent Trends](https://www.ashbyhq.com/talent-trends-report/reports/recruiting-operations-benchmarks-talent-trends) ·
[Greenhouse 2024 State of Job Hunting](https://www.greenhouse.com/blog/greenhouse-2024-state-of-job-hunting-report) ·
[Figma — realtime editing of ordered sequences](https://www.figma.com/blog/realtime-editing-of-ordered-sequences/) ·
[TkDodo — concurrent optimistic updates](https://tkdodo.eu/blog/concurrent-optimistic-updates-in-react-query) ·
[Charemza — transaction.atomic is not as atomic as you think](https://charemza.name/blog/posts/django/postgres/transactions/not-as-atomic-as-you-may-think/) ·
[django-pgtrigger](https://django-pgtrigger.readthedocs.io/en/stable/cookbook/) ·
[GDPR Art. 14](https://gdpr-info.eu/art-14-gdpr/)

---

## 11. Late findings from the wider sweep

Added after the last three research passes reported.

### The category has a ~20% mortality rate inside 18 months

Of nine Show HN trackers launched 2024–2026, **four are already gone**: `applyboop.com` and
`track-j.com` no longer resolve, `runmagi.com` ("Fully Automatic Job Application Tracker via
Gmail") is now a Chinese sports-streaming site, and `didtheyghost.me` pivoted away. Sonara
shut down in February 2024 and took paying users' application queues with it.

**Design consequence:** durability is a feature. Users say so directly — *"a `.xlsx` does not
shut down"*. Self-serve export must ship with the module, not after it.

### The single best analytic in the category comes from a 6-point Show HN

**Seisin** ships "Response rate by source" — Referral 75% · Company site 57% · LinkedIn 55% ·
Indeed 52% — plus a conversion funnel, per-round interview outcomes, and an offer-comparison
matrix with currency- and relocation-adjusted salary. Their positioning line is the whole
category's gap in one sentence:

> *"Most trackers file your applications away. Seisin keeps them, connects them, and shows you
> what is actually working."*

Treat their *numbers* as illustrative UI rather than data — they are mockup figures and sit far
above the rigorous benchmarks in §5 — but the **shape** is right and nobody funded is doing it.

### Open source is where the interesting work is

**JobOps** — self-hosted, local LLM, AGPLv3 + Commons Clause — went from its Show HN to **3,940
GitHub stars in nine months**. It derives status from Gmail, snapshots job descriptions against
link rot, tracks resume versions, and **explicitly refuses to auto-apply**: *"Recruiters can
tell when applications are automated and it gets you blacklisted."*

Its top open feature request is the gap in §0: *"does it give you some insight into which
variations are the best performers?"* — resume-variant performance, unbuilt everywhere.

### Trust and billing hygiene is the incumbents' soft underbelly

The correlation between Trustpilot score and billing behaviour is stark:

| Product | Score | 1-star share |
|---|---|---|
| Jobright.ai | 4.8 | 1% |
| Huntr | 4.5 | 0% |
| Teal | 4.2 | **14%** |
| Careerflow | 3.6 | **29%** |
| Simplify | **3.2** | **45%** |
| Final Round AI | 2.9 | 27% |
| LazyApply | **2.1** | **58%** |
| Massive | **1.7** | **77%** |

In every low-scoring product the top complaint is **charging behaviour, not features**: refunds
refused against an advertised guarantee, cancellation friction, review-gated refunds, no
self-serve account deletion. Meanwhile **weekly pricing is now the norm and is resented**
(Careerflow $8.99/wk, Eztrackr $8.99/wk, Simplify $19.99/wk — Teal's weekly annualises to ~$678
against $316 for quarterly), while one-time and lifetime tiers draw unprompted praise.

**"Cancel and delete in one click, refund policy on the pricing page" is the cheapest
differentiation available in this category.** We already ship self-serve CV and account deletion;
Careerflow's lack of it is called *"borderline negligent"* by its own users.

### Regional pricing is an unclaimed position — and it is ours

**Interview OS** prices in Bangladeshi taka (৳29/month) via **bKash**, with manual activation and
**no auto-renewal**. That is a deliberate GTM for a market the incumbents price out entirely —
Teal at $13/week is not a product for a Karachi job seeker.

Given HireFlow's market, this deserves its own decision rather than being inherited from the
US-centric competitive set. Note also the price anchor: **339 free Notion templates**, Notion's
own free, Airtable's free, and several free-forever trackers. Verified paid *templates* top out
around $6.99–$9.

### Stage names: the convention is settled, so do not spend design effort there

Across ~25 products the default is `Saved → Applied → Interview(ing) → Offer → Rejected`. The
only differentiated stages anywhere in the market are **LoopCV's `Screened`, `Withdrew` and
`Hired`**, **Ghoster's `Ghosted`**, and **Nord Resume ending on `Hired` rather than `Rejected`** —
the one product that closes on a positive terminal state.

Our five-stage set matches the convention. §3.1's decision stands, and the effort belongs in
capture and analytics instead.

### Research limits, stated plainly

Reddit was unreachable from every route tried (direct, `.json`, three Redlib mirrors, PullPush),
so the "why people abandon trackers" evidence rests on Hacker News, Trustpilot and Chrome Web
Store reviews — which is dev-skewed. Notion and Airtable template *schemas* are not served to
fetchers, so property names there are unverified. `tealhq.com` returns 403 to all fetchers.
Two claims circulating internally did not survive checking: **"Cirrus"** — no job tracker by
that name has any public trace; and **"Jobtrek"** — the domains are parked, a holding page, an
interview-prep tool, and a contractor invoicing product. Neither belongs on a competitive slide.
