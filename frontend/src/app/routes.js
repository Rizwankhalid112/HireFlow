/*
 * The lazy-route registry.
 *
 * Every page is code-split, which keeps the first load small but means each
 * navigation used to be a cold chunk fetch behind a blank spinner — the user
 * pays the network round trip *after* deciding where to go.
 *
 * Holding the importers here lets anything trigger one early: the sidebar
 * warms a route on hover, and the app warms the likely-next ones once the
 * browser is idle. `import()` is memoised by the bundler, so calling a loader
 * twice costs nothing and the router's `lazy()` resolves instantly from the
 * already-fetched module.
 */

export const routeLoaders = {
  '/': () => import('@/pages/LandingPage'),
  '/login': () => import('@/features/auth/pages/LoginPage'),
  '/register': () => import('@/features/auth/pages/RegisterPage'),
  '/forgot-password': () => import('@/features/auth/pages/ForgotPasswordPage'),
  '/reset-password': () => import('@/features/auth/pages/ResetPasswordPage'),
  '/verify-email': () => import('@/features/auth/pages/VerifyEmailPage'),
  '/home': () => import('@/pages/HomePage'),
  '/cv-builder': () => import('@/features/cvBuilder/pages/CVBuilderPage'),
  '/job-match': () => import('@/features/jobMatch/pages/JobMatchPage'),
  '/jobs': () => import('@/features/jobs/pages/JobsPage'),
  '/my-cvs': () => import('@/features/jobMatch/pages/MyCVsPage'),
};

const warmed = new Set();

/** Fetch a route's chunk ahead of the click. Safe to call repeatedly. */
export function prefetchRoute(path) {
  if (warmed.has(path)) return;

  const load = routeLoaders[path];
  if (!load) return;

  warmed.add(path);
  // A failed prefetch must never surface: the real navigation will retry and
  // report properly. Swallowing here keeps an offline blip off the console.
  load().catch(() => warmed.delete(path));
}

/**
 * Warm the routes behind the primary navigation once the browser is idle.
 *
 * Deliberately not every route: the CV Builder alone pulls pdf.js, so warming
 * the whole app on load would undo the code splitting it exists to enable.
 */
export function prefetchPrimaryRoutes(paths) {
  const run = () => paths.forEach(prefetchRoute);

  if (typeof requestIdleCallback === 'function') {
    requestIdleCallback(run, { timeout: 3000 });
  } else {
    setTimeout(run, 1500);
  }
}
