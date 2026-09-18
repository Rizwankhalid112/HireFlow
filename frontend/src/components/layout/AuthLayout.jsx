import { Link, Outlet } from 'react-router-dom';

import { Icon, Logo } from '@/components/ui';

/* A split: the product's case on the left, the form on the right. The left
   panel is always dark regardless of theme — it is a brand surface, not an
   app surface, so it does not follow the user's light/dark preference. */
export function AuthLayout() {
  return (
    <div className="flex min-h-screen bg-surface">
      <section className="relative hidden w-[46%] shrink-0 flex-col justify-between overflow-hidden bg-[#0B1220] p-11 lg:flex">
        {/* quiet concentric geometry — no gradient wash */}
        <span className="pointer-events-none absolute -top-32 -right-36 size-[26rem] rounded-full border border-white/8" />
        <span className="pointer-events-none absolute -top-16 -right-20 size-72 rounded-full border border-white/8" />
        <span className="pointer-events-none absolute -bottom-40 -left-24 size-96 rounded-full border border-white/5" />

        <Link to="/" className="relative flex items-center gap-2.5">
          <Logo size={26} />
          <span className="text-base font-bold tracking-tight text-white">HireFlow</span>
        </Link>

        <div className="relative flex max-w-md flex-col gap-7">
          <h1 className="text-[2.35rem] leading-[1.15] font-semibold tracking-tight text-balance text-white">
            One CV. Every application tailored to the posting.
          </h1>
          <p className="text-sm leading-6 text-pretty text-slate-400">
            Keep one master CV. HireFlow reads the job description, tells you which keywords you
            already cover and which you only word differently, and drafts the letter — without ever
            putting a claim on your CV you cannot back up.
          </p>

          <dl className="flex gap-8 pt-1">
            {[
              ['2,714', 'live listings'],
              ['13', 'company boards'],
              ['6', 'CV templates'],
            ].map(([value, label]) => (
              <div key={label} className="flex flex-col gap-0.5">
                <dt className="tabular text-xl font-medium tracking-tight text-white">{value}</dt>
                <dd className="text-[11px] text-slate-500">{label}</dd>
              </div>
            ))}
          </dl>
        </div>

        <p className="relative flex items-center gap-2 text-[11px] text-slate-500">
          <Icon name="check" size={14} />
          Your CV is yours. HireFlow never applies to a job or contacts an employer on your behalf.
        </p>
      </section>

      <section className="flex flex-1 items-center justify-center px-5 py-10">
        <div className="w-full max-w-sm">
          <Link to="/" className="mb-7 flex items-center justify-center gap-2.5 lg:hidden">
            <Logo size={26} />
            <span className="text-base font-bold tracking-tight">HireFlow</span>
          </Link>
          <Outlet />
        </div>
      </section>
    </div>
  );
}
