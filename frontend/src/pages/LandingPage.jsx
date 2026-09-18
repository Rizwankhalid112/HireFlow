import { Link } from 'react-router-dom';

import { Badge, Button, Icon } from '@/components/ui';

const buckets = [
  {
    name: 'Matched',
    tone: 'border-ok-line bg-ok-soft',
    head: 'text-ok',
    icon: 'check',
    chip: 'border-ok-line bg-ok-soft text-ok',
    body: 'Skills the posting asks for that your CV already evidences, in the employer’s own words. Nothing to do.',
    items: ['Python', 'Django', 'PostgreSQL'],
  },
  {
    name: 'Reworded',
    tone: 'border-warn-line bg-warn-soft',
    head: 'text-warn',
    icon: 'swap',
    chip: 'border-warn-line bg-warn-soft text-warn',
    body: 'You have the skill; they name it differently. Rename it and the keyword scan finds you. This is the free win, and where most of the value sits.',
    items: ['Task queues → Celery', 'Unit testing → pytest'],
  },
  {
    name: 'Missing',
    tone: 'border-bad-line bg-bad-soft',
    head: 'text-bad',
    icon: 'close',
    chip: 'border-bad-line bg-bad-soft text-bad',
    body: 'Genuinely absent. We show them and stop there — no tool should write a skill onto your CV that you would then have to defend in an interview.',
    items: ['Kubernetes', 'Kafka'],
  },
];

const features = [
  {
    icon: 'cv',
    title: 'One CV, six templates',
    body: 'Write it once in a structured editor that scores its own completeness. Five of the six layouts are ATS-safe. What you see in the preview is byte-for-byte the PDF you download — the same server render, not a browser approximation.',
  },
  {
    icon: 'upload',
    title: 'Import the CV you already have',
    body: 'Upload a PDF or DOCX and review what was read before a single field is written. Where a date is genuinely missing it asks you rather than guessing one.',
  },
  {
    icon: 'jobs',
    title: 'Jobs ranked against your skills',
    body: 'Listings gathered nightly straight from company boards, so one that closes disappears within days. Rank them by overlap with your own CV and see exactly which of your skills matched — not an unexplained percentage.',
  },
];

export default function LandingPage() {
  return (
    <>
      {/* ── hero ── */}
      <section className="mx-auto flex max-w-3xl flex-col items-center gap-6 px-5 pt-20 pb-14 text-center">
        <Badge variant="neutral">
          <span className="size-1.5 rounded-full bg-ok-solid" />
          Gathered nightly from Greenhouse, Ashby, Lever and Workable
        </Badge>

        <h1 className="text-4xl leading-[1.08] font-semibold tracking-tight text-balance sm:text-5xl md:text-[3.5rem]">
          Tailor your CV to the job.
          <br />
          Without inventing anything.
        </h1>

        <p className="max-w-xl text-base leading-7 text-pretty text-muted">
          Keep one master CV. HireFlow reads a posting and tells you which keywords you already
          cover, which you simply word differently, and which you genuinely lack — then drafts the
          letter from the first two only.
        </p>

        <div className="flex flex-wrap items-center justify-center gap-3 pt-1">
          <Link to="/register">
            <Button size="lg">Build my CV</Button>
          </Link>
          <Link to="/login">
            <Button size="lg" variant="secondary" iconAfter="chevronRight">
              Sign in
            </Button>
          </Link>
        </div>
      </section>

      {/* ── the differentiator ── */}
      <section className="border-y border-line bg-canvas px-5 py-16">
        <div className="mx-auto flex max-w-5xl flex-col gap-9">
          <div className="flex flex-col items-center gap-3 text-center">
            <h2 className="max-w-2xl text-2xl leading-tight font-semibold tracking-tight text-balance sm:text-3xl">
              Most CV tools will happily lie for you. This one sorts the keywords into three honest
              piles.
            </h2>
            <p className="max-w-xl text-sm leading-6 text-pretty text-muted">
              Flattening these into one list is what turns a tailoring tool into a fabrication tool.
              They stay separate, and the cover letter is drafted from the first two only.
            </p>
          </div>

          <div className="grid gap-4 md:grid-cols-3">
            {buckets.map((bucket) => (
              <article
                key={bucket.name}
                className={`flex flex-col gap-3 rounded-card border bg-surface p-5 ${bucket.tone.split(' ')[0]}`}
              >
                <h3 className={`flex items-center gap-2.5 text-base font-semibold ${bucket.head}`}>
                  <span className={`grid size-6 place-items-center rounded-md ${bucket.tone}`}>
                    <Icon name={bucket.icon} size={14} strokeWidth={2.6} />
                  </span>
                  {bucket.name}
                </h3>
                <p className={`text-[13px] leading-5 text-pretty ${bucket.head}`}>{bucket.body}</p>
                <ul className="flex flex-wrap gap-1.5 pt-0.5">
                  {bucket.items.map((item) => (
                    <li
                      key={item}
                      className={`rounded-md border px-2 py-0.5 text-[11px] font-medium ${bucket.chip}`}
                    >
                      {item}
                    </li>
                  ))}
                </ul>
              </article>
            ))}
          </div>
        </div>
      </section>

      {/* ── what you get ── */}
      <section className="mx-auto grid max-w-5xl gap-10 px-5 py-16 md:grid-cols-3">
        {features.map((feature) => (
          <article key={feature.title} className="flex flex-col gap-3">
            <span className="grid size-9 place-items-center rounded-card border border-accent-line bg-accent-soft text-accent">
              <Icon name={feature.icon} size={18} />
            </span>
            <h3 className="text-[17px] font-semibold tracking-tight">{feature.title}</h3>
            <p className="text-[13px] leading-6 text-pretty text-muted">{feature.body}</p>
          </article>
        ))}
      </section>

      {/* ── closing ── */}
      <section className="px-5 pb-20">
        <div className="relative mx-auto flex max-w-5xl flex-col items-start justify-between gap-7 overflow-hidden rounded-2xl bg-[#0B1220] p-12 md:flex-row md:items-center">
          <span className="pointer-events-none absolute -top-24 right-16 size-72 rounded-full border border-white/8" />
          <div className="relative flex max-w-xl flex-col gap-2.5">
            <h2 className="text-2xl leading-tight font-semibold tracking-tight text-balance text-white sm:text-3xl">
              Start with the CV you already have
            </h2>
            <p className="text-sm leading-6 text-pretty text-slate-400">
              Upload it, review what we read, and have a tailored application ready before the
              posting is a week old.
            </p>
          </div>
          <Link to="/register" className="relative shrink-0">
            <Button size="lg">Create your account</Button>
          </Link>
        </div>
      </section>
    </>
  );
}
