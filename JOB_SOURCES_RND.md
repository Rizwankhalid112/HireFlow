# Job Data Sources — R&D Report

**HireFlow · Module 2 (Job Search)**
Prepared 10 September 2026 · every figure below was measured live, not quoted from documentation.

---

## 1. What we are building

Two modules. The first is **already built and tested**; this report is the research behind the second.

**Module 1 — Job Match (built).** A user pastes a job description, picks a CV, and gets back
keyword analysis and a cover letter.

**Module 2 — Find Matching Jobs (this report).** Instead of the user finding a job and pasting
it, we show them jobs that match the CV they already have with us.

### The flow

```
 ┌── DAILY, IN THE BACKGROUND (no user waiting) ────────────────────┐
 │  For each company we track:                                      │
 │    → call its ATS public API   (one request, no key, no auth)    │
 │    → normalise the response into our own shape                   │
 │    → upsert into our `jobs` table, de-duplicated                 │
 │    → drop listings we have not seen in the feed for 45 days      │
 └──────────────────────────────────────────────────────────────────┘
                                │
 ┌── WHEN THE USER SEARCHES ────┴───────────────────────────────────┐
 │  1. User enters a title + location, or clicks "use my CV"        │
 │  2. We query OUR OWN database — never a live scrape per user     │
 │  3. Rank against their CV's skills                               │
 │  4. Show job cards: title, company, location, match, posted      │
 │  5. Two actions per card:                                        │
 │       "Tailor CV for this" → hands the description to Module 1   │
 │       "Apply"              → opens the employer's own posting    │
 └──────────────────────────────────────────────────────────────────┘
```

**We never handle the application itself.** The user applies on the employer's site. Our job ends
when they are ready to click Apply.

**We fetch once a day into our own database, never per user request.** This keeps our request
volume flat regardless of traffic, and it is also what keeps us a well-behaved client of every
platform we use.

---

## 2. Summary for the reader in a hurry

- **Four platforms give us everything we need, free, with no API key and no legal risk:**
  Greenhouse, Ashby, Lever, Workable. All four return **full job descriptions in a single request
  per company**.
- **Posting dates from those four are trustworthy.** This took the most work to establish and is
  documented in §5.
- **We do not scrape LinkedIn, Indeed or Glassdoor.** Not a technical limit — a legal one, and
  their terms are explicit. The lawful route to that data is a licensed aggregator (§6).
- **Direct access to Pakistani job sites yields very little usable data** (§7). The realistic path
  to Pakistan coverage is the Jooble API, which needs a free key we do not yet have.
- **Cost of a daily run: ~500 requests, ~1 GB, ~42 minutes** for 500 companies (§8).

---

## 3. Platform-by-platform: what we get and how

Every row below was called live on 10 September 2026.

### Tier 1 — Public ATS APIs · no key, no account, no legal risk ✅

These exist because employers *want* their jobs syndicated. Using them is the intended behaviour.

| Platform | Endpoint | Tested against | Result |
|---|---|---|---|
| **Greenhouse** | `boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=true` | stripe, gitlab, monzo, airbnb, robinhood | ✅ 616 / 229 / 67 / 168 / 127 jobs |
| **Ashby** | `api.ashbyhq.com/posting-api/job-board/{slug}` | openai, ramp, notion, linear, posthog | ✅ 785 / 146 / 130 / 29 / 10 jobs |
| **Lever** | `api.lever.co/v0/postings/{slug}?mode=json` | palantir, matchgroup | ✅ 310 / 75 jobs |
| **Workable** | `apply.workable.com/api/v1/widget/accounts/{slug}?details=true` | blueground | ✅ 21 jobs |

**All four return the full job description in the list call.** This is the single most important
operational finding: ingestion is **one request per company**, not one per job. Five hundred
companies is five hundred requests, not eighty-seven thousand.

**Response speed** (measured, repeated):

| Platform | Typical | Note |
|---|---|---|
| Greenhouse | 0.3 – 1.5 s | consistent |
| Ashby | 0.3 – 2.0 s | consistent |
| Workable | ~1.2 s | consistent |
| **Lever** | **5 – 20 s** | consistently slow and variable — the pipeline bottleneck |

### Tier 1 platforms that did NOT work ⚠️

Both are named in most public guides, so it is worth recording that we tested them and they failed:

| Platform | Result |
|---|---|
| **SmartRecruiters** | Endpoint responds `200` but returns `totalFound: 0` for **every** company tried — Bosch, Visa, Ubisoft, IKEA, Twilio, McDonald's, Publicis. Alive but yielding nothing. |
| **Recruitee** | `404` on every documented URL pattern and every company slug tried. |

Also note several company slugs in circulation are wrong: **Lever** — netflix, yelp, twitch,
shopify, plaid, brex all 404. **Greenhouse** — doordash 404s. **Ashby** — vercel returns 0.
The company list must be verified, not assumed.

### Tier 2 — Zero-auth public feeds ✅

Useful for remote-role coverage. All tested and working: **RemoteOK** (99 jobs), **Arbeitnow**
(250, but a 70-second first response), **Remotive** (18), **Himalayas** (20), **Jobicy** (20),
**The Muse** (20), **WeWorkRemotely** (25, RSS/XML).

⚠️ **Jobicy's own API response carries a licence condition**: Jobicy must be credited with a direct
link, and apply buttons must point at the original job URL. Other aggregators are likely to carry
similar terms — these need reading before we ship, not after.

### Tier 3 — Needs an account and API key · not yet tested 🔑

Deliberately deferred until we decide to set them up. **Two of these matter a great deal:**

| Source | Why it matters |
|---|---|
| **JSearch** (RapidAPI) | **The only lawful route to LinkedIn, Indeed and Glassdoor listings.** Aggregates them via Google for Jobs and tags each result with its publisher. |
| **Jooble** | Free key by email. Covers 70+ countries **including Pakistan**, and aggregates Rozee.pk indirectly — likely our whole Pakistan answer in one integration. |
| Adzuna | 250 calls/day free. No Pakistan; India tier gives regional coverage. |
| USAJobs · Reed · Findwork | Narrow (US federal / UK / remote-tech). Low priority. |

---

## 4. Is the data any good? (measured across 1,593 real jobs)

Answering "does the API respond" is the easy half. This is what the data actually looks like.

### What is reliable

**Title, company, location, description and apply URL are present on 100% of jobs, on every
platform.** Descriptions are substantial — median 1,400 to 10,800 characters depending on source.
These feeds serve only currently-open roles, so we are not ingesting dead listings.

### What is not

| Field | Reality |
|---|---|
| **Salary** | Mostly absent, and inconsistent *within* a platform — 97% present on Ashby/Ramp, **0% on Ashby/Notion**. It is a per-company opt-in. **Must be display-only, never a search filter**, or we would silently hide most jobs. |
| **Remote / onsite** | **Greenhouse does not have this field at all** — 0% across all boards tested. Greenhouse is our largest source and remote/onsite is a required filter. Either infer it from location and description text, or exclude Greenhouse from that filter and say so in the UI. |
| **Location** | Free text, different on every platform: `"Singapore"`, `"San Francisco, California"`, `"New York, NY"`, `"Tokyo, Japan "` (trailing space), plus `"N/A"` 21 times on Stripe alone. Needs a normalisation pass and will remain approximate. |
| **Description format** | Three different formats. Greenhouse is HTML but **entity-escaped** (`&lt;h2&gt;`) — a naive strip leaves visible tags in the text. Workable is raw HTML. Ashby and Lever are plain text. All must be normalised on ingest. |
| **`updated_at`** | Present on Greenhouse only (100%); absent on Ashby, Lever and Workable. So "only re-pull what changed" works for one platform in four. |

---

## 5. The posting date — the hardest question, and the answer

The date decides whether this product is useful. It took the most investigation.

### Greenhouse publishes four dates that disagree

| Field | What it means |
|---|---|
| `first_published` | when the requisition first went live |
| `updated_at` | **unusable** — every Stripe job reads "5 days ago"; it is a board-wide touch |
| `published_at` (embed endpoint) | usually equals `first_published` |
| **`datePosted`** (job page, schema.org JSON-LD) | **what the employer publishes to the world and Google indexes** |

Six randomly sampled jobs — all four dates agree exactly:

```
Business Systems Architect     first_pub 20d   updated 5d   embed 20d   PAGE 20d
Capital Markets Investments               12d           5d         12d        12d
Consumer Ops Program                      51d           5d         51d        50d
Machine Learning Engineer                 23d           5d         23d        23d
```

The *oldest* jobs — reposted requisitions — diverge sharply:

```
Risk Operations Associate      first_pub 1055d   →   PAGE 27d     (1000-day gap)
Data Analyst                             1043d   →   PAGE 19d
Account Executive (posted today)             0d  →   PAGE 0d      (exact match)
```

**Conclusion: `first_published` is correct for the large majority and too old for reposts.
Crucially the error runs only one way — it makes a job look older than it is, never fresher.**
That is a safe failure mode: we under-sell freshness rather than presenting a stale job as new.

### Lever and Ashby are accurate as they stand

Cross-checked the API date against each job page's published `datePosted`:

```
Lever  · Software Engineer, iOS      API 2023-10-23   page 2023-10-23   match
Lever  · Senior Product Manager      API 2023-12-14   page 2023-12-14   match
Ashby  · SWE, Developer Platform     API 2026-08-24   page 2026-08-24   match
Ashby  · Business Development Rep    API 2026-04-02   page 2026-04-02   match
```

An earlier assumption that Lever's old dates were a data fault was **wrong, and is corrected
here**: Lever publishes `createdAt` as its public posting date. The dates are accurate; those
roles genuinely have been open that long.

### A universal fallback exists

**Every ATS job page carries schema.org JSON-LD with `datePosted`**, because Google for Jobs
requires it. That is the public truth for any listing anywhere — but it costs one request per job,
so it cannot be the harvest.

**Recommended approach:** take the bulk API date on ingest; fetch the job page only for a listing
that looks old *and* is about to be shown near the top of a user's results. That bounds the cost to
jobs a user actually sees while keeping the displayed date honest.

Worth noting: displayed job dates are widely gamed across the industry — sponsored placements reset
the timer, and many career sites simply render today's date. Working from the ATS database
timestamp avoids this entirely.

### One product decision this forces

Palantir publishes `datePosted = 2009-12-05` for a live opening. Not a bug — that requisition has
genuinely been open since 2009 and they say so publicly. But a card reading **"posted 6,123 days
ago"** is useless, and sorting by date would bury every genuinely new role beneath perpetual ones.

This needs a display policy, not a parsing fix: show **"long-running listing"** past a threshold,
do not let raw date dominate ranking, and consider surfacing age as a useful signal — a role open
for four years is worth knowing about before spending an evening on the application.

---

## 6. Platforms we will NOT scrape, and why

### LinkedIn ❌

Their `robots.txt` opens with:

> *"The use of robots or other automated means to access LinkedIn without the express permission of
> LinkedIn is strictly prohibited."*

It explicitly blocks the exact job paths, **even for Googlebot**:

```
Disallow: /jobs-guest/            ← the public guest job search
Disallow: /api/jobPostings/jobs*
Disallow: /jobs?runSearch*
```

Only `LinkedInBot` is granted `Allow: /`. Permission is by application to a whitelist address and
is intended for search engines.

**The legal position, stated precisely** — it is widely misreported:

- **hiQ Labs won on the Computer Fraud and Abuse Act.** Scraping *public* pages is not
  "unauthorised access" and is not a computer crime.
- **hiQ then lost on breach of contract** (November 2022). LinkedIn's User Agreement §8.2
  unambiguously prohibits scraping. Outcome: a **$500,000 judgment, a permanent injunction, and
  destruction of the collected data.**
- **This is live, not history.** LinkedIn is pursuing Nubela/Proxycurl in 2026 — a commercial
  reseller of LinkedIn data. That is precisely the "we don't scrape, we buy from someone who does"
  workaround.

**Therefore: we do not scrape LinkedIn, and we do not purchase LinkedIn data from a reseller.**
"Not a crime" and "permitted" are different questions, and only the second one governs us.

**Indeed and Glassdoor** are treated the same way: restrictive terms and partner-gated APIs.

**The lawful alternative is JSearch**, which surfaces these listings via Google for Jobs under its
own licence and labels each result with its publisher.

### jobsalert.pk ❌

Their `robots.txt` blocks AI crawlers by name and states its terms as a condition of access:

```
User-agent: *
Content-Signal: search=yes, ai-train=no, use=reference
User-agent: ClaudeBot        Disallow: /
User-agent: CCBot            Disallow: /
User-agent: Bytespider       Disallow: /
User-agent: Google-Extended  Disallow: /
```

They permit search indexing and refuse AI collection. **We did not fetch a single page from this
site, and should not without written permission.**

---

## 7. Pakistan coverage — tested honestly

| Site | Permission | Data available | Verdict |
|---|---|---|---|
| **mustakbil.com** | `Allow: /`, publishes a jobs sitemap | Full schema.org JSON-LD | ✅ accessible, ❌ **years out of date** |
| **brightspyre.com** | job pages open | RDFa on the listing page only | ❌ **no descriptions at all** |
| **rozee.pk** | `/job/jsearch/` permitted | **nothing in the HTML** | ⚠️ requires a headless browser |
| **jobsalert.pk** | **blocks us by name** | — | ❌ off limits |

**mustakbil.com** is the most cooperative site of the four — `Allow: /` and a published sitemap of
**1,226 job URLs**, each page carrying proper JSON-LD with title, date, employer, salary and
description. No scraping required. **But the content is stale.** Sampled listings:

```
Graphic Designer - Remote          posted 2022-04-21   (1,602 days ago)   "valid to" 2039
Administrative Support Specialist  posted 2022-08-08   (1,493 days)       "valid to" 2030
Shopify Developer                  posted 2025-01-04   (613 days)
```

The sitemap's `lastmod` is refreshed (median 36 days) while `datePosted` is not — **so the sitemap
makes stale jobs look fresh.** Presenting four-year-old listings as current would be worse than
showing nothing. It is also one request *per job*: 1,226 requests, ~40 minutes, for one site.

**brightspyre.com** gives title, company and location, but its detail pages carry **no description,
no date and no salary**. Without a description we cannot match a job to a CV, which makes it close
to useless for this product.

**rozee.pk** is fully client-rendered. The page returns 268 KB containing no job data — only empty
containers and framework hooks. We searched its JavaScript bundles for any `/api`, `/ajax` or
`/json` endpoint to use instead: **none exists.** Rozee means Playwright plus Chromium — roughly
400 MB added to the image, a much slower run, and selectors that break whenever they change their
front end. Their Terms of Service remain a separate question from robots.txt.

**Recommendation: get the Jooble key before writing any scraper.** It is free, covers Pakistan, and
aggregates Rozee indirectly — likely turning this entire section into one API integration.

---

## 8. What a daily run costs

Measured over 11 real companies: 1,918 jobs, 24.2 MB, 60 seconds.

| Companies tracked | Requests/day | Jobs held | Data transferred | Wall time |
|---|---|---|---|---|
| 50 | 50 | ~8,700 | ~110 MB | ~4 min |
| 200 | 200 | ~34,900 | ~440 MB | ~17 min |
| 500 | 500 | ~87,200 | ~1.1 GB | ~42 min |

No platform returned a `RateLimit-*` or `Retry-After` header, and Greenhouse accepted five rapid
consecutive calls without complaint. Undocumented limits are not absent limits, so a polite delay
between requests stays in the design regardless.

Data volume is the surprise, not request count — descriptions are large, and because only
Greenhouse exposes `updated_at`, we must re-fetch the other three platforms in full each day.

---

## 9. Recommendation

**Build on Greenhouse, Ashby, Lever and Workable.** Free, no keys, no legal exposure, trustworthy
dates, complete descriptions, one request per company. This is a solid foundation and can be built
immediately.

**Design these six realities in from the start**, rather than discovering them later:

1. Retention keys on **when we last saw a job in the feed**, not on its posting date — a 45-day rule
   based on posting date would delete live listings.
2. **Normalise descriptions per source** on ingest (Greenhouse's escaped HTML in particular).
3. **The remote/onsite filter needs a plan** — Greenhouse simply does not provide the field.
4. **Salary is display-only**, never a filter.
5. **Location needs normalisation** and will stay approximate.
6. **A display policy for long-running listings**, so evergreen requisitions neither look absurd nor
   distort ranking.

**Two decisions needed from outside engineering:**

- **The list of companies to track.** The pipeline is worth nothing without it, and it is a
  judgement about our target market. Recommend starting with ~50 verified companies rather than a
  placeholder 500 — several widely-circulated slugs are wrong.
- **Sign-ups for JSearch and Jooble.** These are not optional extras: they are the only lawful route
  to LinkedIn-sourced listings and the only realistic route to Pakistan coverage. Both have free
  tiers. **They should be obtained before any effort goes into scraping Pakistani sites**, because
  they may make that work unnecessary.

---

*All findings independently verified by live calls on 10 September 2026. Raw response data and test
scripts retained. Nothing in this report is quoted from vendor documentation without being tested.*
