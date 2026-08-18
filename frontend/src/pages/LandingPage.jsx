import { Link } from 'react-router-dom';

import { Button, Card } from '@/components/ui';

const features = [
  {
    title: 'Kanban pipeline',
    description: 'Track every application from saved to offer with a visual board.',
  },
  {
    title: 'Smart reminders',
    description: 'Never miss a follow-up with automated nudges and deadlines.',
  },
  {
    title: 'Actionable analytics',
    description: 'See response rates, interview conversion, and time-to-offer.',
  },
];

export default function LandingPage() {
  return (
    <>
      <section className="mx-auto max-w-6xl px-4 py-20">
        <div className="mx-auto max-w-3xl text-center">
          <p className="text-sm font-semibold uppercase tracking-wide text-indigo-600">
            HireFlow
          </p>
          <h1 className="mt-4 text-4xl font-bold tracking-tight text-slate-900 dark:text-slate-100 md:text-6xl">
            Track. Automate. Get Hired.
          </h1>
          <p className="mt-6 text-lg text-slate-600 dark:text-slate-400">
            The modern job search command center. Organize applications, automate follow-ups,
            and land your next role faster.
          </p>
          <div className="mt-8 flex flex-wrap justify-center gap-4">
            <Link to="/register">
              <Button size="lg">Start for free</Button>
            </Link>
            <Link to="/login">
              <Button size="lg" variant="secondary">
                Sign in
              </Button>
            </Link>
          </div>
        </div>
      </section>

      <section className="border-y border-slate-200 bg-white py-16 dark:border-slate-800 dark:bg-slate-900">
        <div className="mx-auto grid max-w-6xl gap-6 px-4 md:grid-cols-3">
          {features.map((feature) => (
            <Card key={feature.title}>
              <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-100">
                {feature.title}
              </h2>
              <p className="mt-2 text-sm text-slate-600 dark:text-slate-400">{feature.description}</p>
            </Card>
          ))}
        </div>
      </section>

      <section className="mx-auto max-w-6xl px-4 py-16">
        <Card className="bg-gradient-to-r from-indigo-600 to-violet-600 text-white">
          <div className="flex flex-col items-start justify-between gap-6 md:flex-row md:items-center">
            <div>
              <h2 className="text-2xl font-semibold">Start for free today</h2>
              <p className="mt-2 text-indigo-100">
                Create your account and take control of your job search in minutes.
              </p>
            </div>
            <Link to="/register">
              <Button variant="secondary">Get started</Button>
            </Link>
          </div>
        </Card>
      </section>
    </>
  );
}
