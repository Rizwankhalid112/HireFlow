import { Link, Outlet } from 'react-router-dom';

import { Button, IconButton, Logo } from '@/components/ui';
import { useTheme } from '@/context/ThemeContext';
import { useAppSelector } from '@/hooks/useAppSelector';

export function PublicLayout() {
  const isAuthenticated = useAppSelector((state) => state.auth.isAuthenticated);
  const { theme, toggleTheme } = useTheme();

  return (
    <div className="flex min-h-screen flex-col bg-surface">
      <header className="sticky top-0 z-20 border-b border-line bg-surface/85 backdrop-blur">
        <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-5">
          <Link to="/" className="flex items-center gap-2.5">
            <Logo size={26} />
            <span className="text-base font-bold tracking-tight">HireFlow</span>
          </Link>

          <div className="flex items-center gap-2">
            <IconButton
              icon={theme === 'dark' ? 'sun' : 'moon'}
              label={theme === 'dark' ? 'Switch to light theme' : 'Switch to dark theme'}
              onClick={toggleTheme}
            />
            {isAuthenticated ? (
              <Link to="/home">
                <Button size="md">Dashboard</Button>
              </Link>
            ) : (
              <>
                <Link to="/login" className="hidden sm:block">
                  <Button variant="ghost" size="md">
                    Sign in
                  </Button>
                </Link>
                <Link to="/register">
                  <Button size="md">Create account</Button>
                </Link>
              </>
            )}
          </div>
        </div>
      </header>

      <main className="flex-1">
        <Outlet />
      </main>

      <footer className="border-t border-line">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-4 px-5 py-7">
          <p className="flex items-center gap-2.5 text-xs text-subtle">
            <Logo size={22} />
            &copy; {new Date().getFullYear()} HireFlow
          </p>
          <nav className="flex gap-6 text-xs text-subtle">
            <span>Privacy</span>
            <span>Terms</span>
            <span>Contact</span>
          </nav>
        </div>
      </footer>
    </div>
  );
}
