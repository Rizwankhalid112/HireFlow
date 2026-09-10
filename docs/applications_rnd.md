# Applications Module — R&D and Design

> The job application tracker: the core of HireFlow and the module every remaining
> one reads from. Researched 2026-09-08, before any code.
> Nothing here is built yet — this is the argument, not the plan.

---

## 1. What this module is

`apps/applications` is the thing the README is about: *"Track. Automate. Get Hired — managing job
applications, follow-ups, and hiring progress."* Everything we have shipped so far (auth, the CV
builder) is preparation for it.

It is also the base of the dependency chain. `notifications` sends follow-up reminders **about
applications**. `analytics` charts **application** outcomes. `reports` exports them. None of those
three can start until this exists, which is why it is next rather than any of them.

Current state: `apps/applications` exists on disk with every `.py` file at 0 bytes, and it is **not
in `INSTALLED_APPS`** — Django does not load it at all. Same for `apps/notifications`. The frontend
has empty `components/KanbanBoard/`, `components/ApplicationDrawer/` and `components/Charts/`
directories waiting for it.

---

## 2. What the market ships

| Product | Core idea | Tracking model | Notable |
|---|---|---|---|
| **Huntr** | Visual pipeline | Kanban: saved → applied → phone screen → interview → offer → rejected | Activity history, contacts, documents, map view, job-search metrics. Chrome "Job Clipper" |
| **Teal** | Structured records | Stage-based pipeline | Per-application **checklists**, 40+ follow-up email templates, contact management. Free tier is unlimited tracking |
| **Simplify** | Data entry | Light tracking | The whole pitch is **autofill** across Workday / Greenhouse / iCIMS |
| **Spreadsheets** | Still the baseline | Whatever you make | The thing every one of these products is actually competing with |

**Four conclusions.**

1. **Kanban is the expected default**, and dragging a card between columns is the primary
   interaction. Nobody ships a form-first tracker.
2. **The stage set is small and near-universal.** Saved / Applied / Screen / Interview / Offer, with
   Rejected and Withdrawn as terminal. Deviations are cosmetic.
3. **Contacts and documents hang off an application**, not off the user. Who you spoke to at Acme is
   a fact about that application.
4. **Every serious product leads with a browser extension.** That is not a coincidence — see §3.

---

## 3. The constraint: data entry, not tracking

The numbers decide the design.

Roughly **3% of applicants are invited to interview**, and in technology it takes around **191
applicants per hire**. A real user of this product will create **one to two hundred applications**
over a search. Recruitment-funnel benchmarks put application → interview at ~8% and interview →
offer at ~27–36%.

Two consequences, and they are the whole design brief:

> **A tracker is only as good as the user's willingness to keep feeding it.** At 180 applications,
> manual entry is the reason people abandon trackers and go back to a spreadsheet — or to nothing.
> Every product surveyed answers this with a Chrome extension. **We do not have one, and building one
> is its own project.** So our answer has to be something else, and it has to be decided *before* the
> schema, not after.

> **A Kanban board is unusable at this volume.** A hundred cards in an "Applied" column is not a
> board, it is a wall. Huntr's own Basic plan caps tracking at 100 jobs. Whatever we build needs a
> second view and a way for dead applications to leave the board.

**The candidate answer for entry** (to be decided, §7): paste a job posting URL or the pasted text
of one, and extract company / title / location / description the same way we already extract a CV.
`services/ai/` is built, the structured-output pattern is proven, and the metering exists. That is
the closest thing we have to Simplify's autofill without shipping an extension.

---

## 4. Ghosting is the default outcome, not an event

97% of applications do not reach an interview, and the overwhelming majority of those simply go
silent — no rejection email ever arrives.

This breaks the naive model where the user moves a card to "Rejected". They will not, because
nothing told them to. A tracker built that way fills up with months-old cards sitting in "Applied",
which is exactly the state that makes the board useless and the analytics wrong.

**Design consequence:** staleness has to be derived from time, not from user action. An application
untouched for N weeks is effectively closed and should be treated as such — surfaced for a decision,
moved off the board, or auto-marked "no response". This is the single most important behavioural
decision in the module, and it is invisible until you have used the thing for two months.

---

## 5. The schema decision that cannot be undone later

Everything else here is reversible. This one is not:

> **Record every status change as a row, with its timestamp — from day one.**

A `status` column on the application tells you where it is now. It cannot tell you how long it sat
in screening, when it moved, or what your applied → interview conversion was last month. That
history is unrecoverable retroactively: if we do not write it at the time, the data does not exist.

This is the same reasoning that put `accepted_index` on `AISuggestionLog` before anything read it.
The `analytics` module is entirely a consumer of this table — build the module without it and
analytics becomes impossible without a migration that cannot backfill.

**Sketch, not final** (the build plan settles it):

- **`Application`** — company, role title, location, work mode, source, job URL, salary range,
  current status, applied date, next action date, notes. Owned by user.
- **`ApplicationStatusEvent`** — application, from_status, to_status, changed_at. Append-only.
- **`Contact`** — name, role, email, LinkedIn, hangs off an application.
- **`Interview`** — round, scheduled_at, format, outcome, notes.
- **`ApplicationDocument`** — which CV/cover letter was sent (see §6).

---

## 6. Where this collides with the CV Builder

The obvious field is "which CV did I send to this job". We cannot answer it today.

`CVProfile` is **one per user and mutable**. The CV a user sent to Acme in March is not recoverable
in September — they have edited it fifteen times since. Storing a foreign key to the profile records
nothing useful.

Three options, all with real costs:

1. **Snapshot the PDF per application.** We already render exact-snapshot PDFs and already store
   them; attaching one to an application is a small step. Storage cost, and it is a picture rather
   than data.
2. **Version the CV.** Correct, and much larger — it reopens the one-CV-per-user design that the
   whole builder rests on.
3. **Do not answer it yet.** Ship the tracker without it and revisit.

The AI suggestions R&D already parked this exact tension under "per-application tailoring vs the
single master CV" and called it a product decision rather than an implementation detail. It is now
in front of us again, which is a sign it needs deciding rather than deferring a second time.

---

## 7. Open questions — these need answers before the build plan

1. **How does an application get created?** Manual form only, or paste-a-URL with AI extraction?
   This is §3, and it decides whether the product is usable at real volume.
2. **What is the exact stage set?** Every stage added is one more the user must maintain and one
   more the funnel splits across.
3. **What happens to a stale application?** Auto-close, nag, or just grey out.
4. **Board or table first?** Kanban is expected but breaks at volume; a table is honest but nobody
   demos a table.
5. **Which CV was sent** — snapshot, version, or defer (§6).
6. **Is there AI in this module at all?** Job-description extraction and CV-to-job matching are both
   natural, both metered, and both scope.

---

## 8. Deliberately out of scope for a first build

- **Browser extension.** The right answer to §3 eventually, and its own project.
- **Email integration** (parsing rejection/interview emails from Gmail). Highest-value automation
  available and by far the largest surface — OAuth scopes, parsing, privacy.
- **Job board search inside HireFlow.** A different product.
- **Interview prep / question banks.** Adjacent, not this.

---

## Sources

- [Huntr vs Teal comparison](https://huntr.co/blog/huntr-vs-teal) · [Huntr features and pricing](https://www.jobfinder-ai.com/blog/huntr-job-search-tracker) · [Best job trackers 2026](https://offboard.co/resources/best-job-application-trackers-2026)
- [Job tracking stages guide](https://www.jobshinobi.com/blog/job-tracking-stages-applied-interview-offer-rejected) · [Job search metrics](https://www.jobshinobi.com/blog/how-to-track-job-search-metrics-applications-to-interviews)
- [Recruitment funnel benchmarks 2026](https://www.pin.com/blog/recruitment-funnel-benchmarks/) · [Recruiting funnel conversion rates](https://www.noon.ai/blog/articles/182-recruiting-funnel-benchmarks-2026)
- [Follow-up timing guide](https://novoresume.com/career-blog/follow-up-on-job-application) · [Follow-up etiquette 2026](https://www.resumemate.io/blog/job-application-follow-up-etiquette-2026-email-templates-best-timing/)
