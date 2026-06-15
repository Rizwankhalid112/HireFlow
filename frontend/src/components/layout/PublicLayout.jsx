import { Link, Outlet } from 'react-router-dom';

import { Button } from '@/components/ui';
import { useTheme } from '@/context/ThemeContext';
import { useAppSelector } from '@/hooks/useAppSelector';

export function PublicLayout() {
  const isAuthenticated = useAppSelector((state) => state.auth.isAuthenticated);
  const { theme, toggleTheme } = useTheme();

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-950">
      <header className="sticky top-0 z-20 border-b border-slate-200 bg-white/90 backdrop-blur dark:border-slate-800 dark:bg-slate-950/90">
        <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-4">
          <Link to="/" className="text-lg font-bold text-indigo-600">
            HireFlow
          </Link>
          <div className="flex items-center gap-3">
            <Button variant="ghost" size="sm" onClick={toggleTheme}>
              {theme === 'dark' ? 'Light' : 'Dark'}
            </Button>
            {isAuthenticated ? (
              <Link to="/home">
                <Button size="sm">Dashboard</Button>
              </Link>
            ) : (
              <>
                <Link to="/login">
                  <Button variant="ghost" size="sm">
                    Log in
                  </Button>
                </Link>
                <Link to="/register">
                  <Button size="sm">Sign up</Button>
                </Link>
              </>
            )}
          </div>
        </div>
      </header>
      <main>
        <Outlet />
      </main>
      <footer className="border-t border-slate-200 py-8 text-center text-sm text-slate-500 dark:border-slate-800 dark:text-slate-400">
        <p>&copy; {new Date().getFullYear()} HireFlow. Track. Automate. Get Hired.</p>
      </footer>
    </div>
  );
}
