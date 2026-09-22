import { useEffect } from 'react';
import { Link, NavLink, Outlet, useLocation } from 'react-router-dom';

import { prefetchPrimaryRoutes, prefetchRoute } from '@/app/routes';
import { Icon, IconButton, Logo } from '@/components/ui';
import { useTheme } from '@/context/ThemeContext';
import { useLogout, useProfile } from '@/features/auth/api/authQueries';
import { useCompletion, useSuggestionCredits } from '@/features/cvBuilder/api/cvQueries';

/* `ai: true` marks a destination that cannot work without a configured model
   key. The server reports that per deployment, so rather than showing a nav
   item that leads to a 503 the entry is simply absent — the same way the CV
   Builder's suggestion panel already removes itself. */
const navItems = [
  { label: 'Dashboard', short: 'Home', to: '/home', icon: 'dashboard' },
  { label: 'CV Builder', short: 'CV', to: '/cv-builder', icon: 'cv' },
  { label: 'Job Match', short: 'Match', to: '/job-match', icon: 'match', ai: true },
  { label: 'Jobs', short: 'Jobs', to: '/jobs', icon: 'jobs' },
  /* Not marked `ai`, unlike Job Match: nothing here calls a model, and these are
     the user's own saved documents. Hiding the page that holds their data
     because a key is missing would be worse than showing an empty state. */
  { label: 'My CVs', short: 'Saved', to: '/my-cvs', icon: 'cv' },
];

const initials = (name) =>
  (name || '')
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0])
    .join('')
    .toUpperCase() || '—';

export function AppLayout() {
  const { theme, toggleTheme } = useTheme();
  const { data: profile } = useProfile();
  const logoutMutation = useLogout();
  const { pathname } = useLocation();

  /* 404s until the builder has created a CV shell, which is a normal state —
     the badge simply does not render until there is a score to show. */
  const { data: completion } = useCompletion();

  /* Undefined while loading, so the item is kept until the server actually
     says the feature is off — a flash of disappearing navigation is worse
     than a moment of showing it. */
  const { data: aiCredits } = useSuggestionCredits();
  const items = navItems.filter((item) => !item.ai || aiCredits?.enabled !== false);

  /* Warm the other authenticated routes once the browser is idle, so the first
     click into any of them is instant rather than a cold chunk fetch. */
  useEffect(() => {
    prefetchPrimaryRoutes(navItems.filter((i) => !i.ai).map((item) => item.to));
  }, []);

  const fullName = profile?.user?.full_name || 'there';
  const active = navItems.find((item) => pathname.startsWith(item.to));

  const linkClass = ({ isActive }) =>
    `relative flex h-8 items-center gap-2.5 rounded-control px-2 text-[13px] transition-colors ${
      isActive
        ? 'bg-accent-soft font-semibold text-accent'
        : 'font-medium text-muted hover:bg-surface-3 hover:text-ink'
    }`;

  return (
    <div className="flex min-h-screen bg-canvas">
      {/* ── sidebar (md and up) ── */}
      <aside className="hidden w-58 shrink-0 flex-col border-r border-line bg-surface md:flex">
        <div className="flex h-13 items-center gap-2.5 border-b border-line px-4">
          <Logo size={24} />
          <span className="text-[15px] font-bold tracking-tight">HireFlow</span>
        </div>

        <nav className="flex flex-1 flex-col gap-1 p-3">
          <p className="px-2 pb-1.5 text-[11px] font-semibold tracking-wider text-subtle uppercase">
            Workspace
          </p>
          {items.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={linkClass}
              onMouseEnter={() => prefetchRoute(item.to)}
              onFocus={() => prefetchRoute(item.to)}
            >
              {({ isActive }) => (
                <>
                  {isActive && (
                    <span className="absolute -left-3 top-1.5 bottom-1.5 w-[3px] rounded-r bg-accent" />
                  )}
                  <Icon name={item.icon} size={16} />
                  {item.label}
                  {item.to === '/cv-builder' && completion ? (
                    <span
                      className={`tabular ml-auto rounded-full border px-1.5 py-px text-[11px] font-medium ${
                        completion.is_complete
                          ? 'border-ok-line bg-ok-soft text-ok'
                          : 'border-warn-line bg-warn-soft text-warn'
                      }`}
                    >
                      {completion.completion_score}%
                    </span>
                  ) : null}
                </>
              )}
            </NavLink>
          ))}
        </nav>

        <div className="flex items-center gap-2.5 border-t border-line p-3">
          <span className="grid size-7 shrink-0 place-items-center rounded-full bg-ink text-[11px] font-semibold text-surface">
            {initials(profile?.user?.full_name)}
          </span>
          <div className="flex min-w-0 flex-1 flex-col leading-tight">
            <span className="truncate text-xs font-semibold">{fullName}</span>
            <span className="truncate text-[11px] text-subtle">{profile?.user?.email}</span>
          </div>
          <IconButton
            icon="logout"
            label="Log out"
            size="sm"
            onClick={() => logoutMutation.mutate()}
            disabled={logoutMutation.isPending}
          />
        </div>
      </aside>

      {/* ── main column ── */}
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex h-13 shrink-0 items-center justify-between gap-3 border-b border-line bg-surface px-4">
          <div className="flex min-w-0 items-center gap-2.5">
            <Link to="/home" className="md:hidden">
              <Logo size={24} />
            </Link>
            <span className="truncate text-[13px] font-semibold">{active?.label ?? 'HireFlow'}</span>
          </div>

          <div className="flex items-center gap-1">
            <IconButton
              icon={theme === 'dark' ? 'sun' : 'moon'}
              label={theme === 'dark' ? 'Switch to light theme' : 'Switch to dark theme'}
              onClick={toggleTheme}
            />
            <IconButton
              icon="logout"
              label="Log out"
              className="md:hidden"
              onClick={() => logoutMutation.mutate()}
              disabled={logoutMutation.isPending}
            />
          </div>
        </header>

        {/* pb-16 clears the mobile tab bar, which is fixed over the content */}
        <main className="flex-1 p-4 pb-20 md:pb-6 lg:p-6 lg:pb-6">
          <Outlet />
        </main>
      </div>

      {/* ── bottom tab bar (below md) ──
          The sidebar is desktop-only, so without this there is no way to change
          page on a phone at all. 44px targets. */}
      <nav
        aria-label="Primary"
        style={{ gridTemplateColumns: `repeat(${items.length}, minmax(0, 1fr))` }}
        className="fixed inset-x-0 bottom-0 z-40 grid gap-1 border-t border-line bg-surface px-2 pt-1.5 pb-[max(0.5rem,env(safe-area-inset-bottom))] md:hidden"
      >
        {items.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            className={({ isActive }) =>
              `flex h-11 flex-col items-center justify-center gap-0.5 rounded-control text-[10px] transition-colors ${
                isActive ? 'bg-accent-soft font-semibold text-accent' : 'font-medium text-muted'
              }`
            }
          >
            <Icon name={item.icon} size={19} />
            {item.short}
          </NavLink>
        ))}
      </nav>
    </div>
  );
}
