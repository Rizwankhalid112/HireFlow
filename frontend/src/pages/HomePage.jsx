import { Card, Spinner } from '@/components/ui';
import { useProfile } from '@/features/auth/api/authQueries';

const stats = [
  { label: 'Total Applications', value: '0' },
  { label: 'Interviews', value: '0' },
  { label: 'Offers', value: '0' },
  { label: 'Pending', value: '0' },
];

export default function HomePage() {
  const { data: profile, isLoading } = useProfile();
  const fullName = profile?.user?.full_name || 'there';

  return (
    <div className="space-y-6">
      <Card>
        {isLoading ? (
          <Spinner className="py-4" />
        ) : (
          <>
            <h1 className="text-2xl font-semibold text-slate-900 dark:text-slate-100">
              Good morning, {fullName}
            </h1>
            <p className="mt-2 text-sm text-slate-600 dark:text-slate-400">
              Your dashboard is ready. The Kanban board and application tracker will live here next.
            </p>
          </>
        )}
      </Card>

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {stats.map((stat) => (
          <Card key={stat.label}>
            <p className="text-sm text-slate-500 dark:text-slate-400">{stat.label}</p>
            <p className="mt-2 text-3xl font-semibold text-slate-900 dark:text-slate-100">
              {stat.value}
            </p>
          </Card>
        ))}
      </div>
    </div>
  );
}
