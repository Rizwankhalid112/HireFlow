import { Link, NavLink, Outlet } from 'react-router-dom';

import { Button } from '@/components/ui';
import { useTheme } from '@/context/ThemeContext';
import { useLogout, useProfile } from '@/features/auth/api/authQueries';

const navItems = [
  { label: 'Dashboard', to: '/home' },
  { label: 'CV Builder', to: '/cv-builder' },
  { label: 'Job Match', to: '/job-match' },
];

export function AppLayout() {
  const { theme, toggleTheme } = useTheme();
  const { data: profile } = useProfile();
  const logoutMutation = useLogout();

  const fullName = profile?.user?.full_name || 'there';

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-950">
      <div className="flex min-h-screen">
        <aside className="hidden w-64 flex-col border-r border-slate-200 bg-white p-6 dark:border-slate-800 dark:bg-slate-900 md:flex">
          <Link to="/home" className="text-xl font-bold text-indigo-600">
            HireFlow
          </Link>
          <nav className="mt-8 space-y-2">
            {navItems.map((item) => (
              <NavLink
                key={item.label}
                to={item.to}
                className={({ isActive }) =>
                  `block rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
                    isActive
                      ? 'bg-indigo-50 text-indigo-700 dark:bg-slate-800 dark:text-indigo-300'
                      : 'text-slate-700 hover:bg-indigo-50 hover:text-indigo-700 dark:text-slate-200 dark:hover:bg-slate-800'
                  }`
                }
              >
                {item.label}
              </NavLink>
            ))}
          </nav>
        </aside>

        <div className="flex flex-1 flex-col">
          <header className="flex h-16 items-center justify-between border-b border-slate-200 bg-white px-4 dark:border-slate-800 dark:bg-slate-900 md:px-6">
            <div>
              <p className="text-sm text-slate-500 dark:text-slate-400">Welcome back</p>
              <p className="font-medium text-slate-900 dark:text-slate-100">{fullName}</p>
            </div>
            <div className="flex items-center gap-3">
              <Button variant="ghost" size="sm" onClick={toggleTheme}>
                {theme === 'dark' ? 'Light' : 'Dark'}
              </Button>
              <Button
                variant="secondary"
                size="sm"
                loading={logoutMutation.isPending}
                onClick={() => logoutMutation.mutate()}
              >
                Log out
              </Button>
            </div>
          </header>
          <main className="flex-1 p-4 md:p-6">
            <Outlet />
          </main>
        </div>
      </div>
    </div>
  );
}
