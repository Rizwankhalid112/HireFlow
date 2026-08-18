# HireFlow Frontend — Context

> Orientation document for the React SPA. Read this first when returning to the project.
> Last verified against commit `d1e740b` (branch `feat/template-user-cv-builder-module`).

---

## 1. What this is

A React 19 + Vite single-page app for HireFlow, a job-application tracking platform. It talks to a Django/DRF
backend through an nginx reverse proxy on the same origin.

**What actually works today:** the complete authentication surface — register, email verification, login,
Google OAuth, forgot/reset password, logout, and silent token refresh with request queueing — plus route
guarding, three layouts, six UI primitives, dark-mode context, an error boundary, a landing page, a 404, and a
skeletal authenticated home.

Plus the **CV Builder** (`src/features/cvBuilder/`) — spec Step 10, built against the live Steps 1–6 API. Six
sections with full CRUD, reorder, canonical skill autocomplete, completion scoring and profile autosave. See §16.

**What doesn't exist yet:** Kanban board, application tracking, analytics, notifications, settings, and reports
are all empty `.gitkeep` directories or 0-byte files. Within the CV Builder, upload/AI-parse (spec Steps 7–8) and
PDF export (Step 9) are absent because **those backend endpoints do not exist** — nothing is stubbed against a
route that would 404.

---

## 2. Tech stack

From [package.json](package.json) (`hireflow-frontend` 0.1.0, `type: module`, private).

**Dependencies**

| Package | Version | Role |
|---|---|---|
| `react` / `react-dom` | ^19.1.0 | UI runtime |
| `react-router-dom` | ^7.6.2 | Routing — JSX `<Routes>` config, not the data router |
| `@reduxjs/toolkit` | ^2.8.2 | Global client state (auth only) |
| `react-redux` | ^9.2.0 | Redux bindings |
| `@tanstack/react-query` | ^5.80.7 | Server state and mutations |
| `axios` | ^1.9.0 | HTTP client |
| `react-hook-form` | ^7.57.0 | Forms |
| `@hookform/resolvers` | ^5.0.1 | Zod resolver bridge |
| `zod` | ^3.25.56 | Schema validation |
| `sonner` | ^2.0.5 | Toasts |
| `@react-oauth/google` | ^0.12.2 | Google OAuth implicit flow |

**Dev:** `vite` ^6.3.5, `@vitejs/plugin-react` ^4.5.2, `tailwindcss` ^4.1.8, `@tailwindcss/vite` ^4.1.8.

**Scripts:** `dev` → `vite`, `build` → `vite build`, `preview` → `vite preview`. There is **no lint, format, or
test script**, and no ESLint/Prettier config or test framework installed.

### Build config — [vite.config.js](vite.config.js)

- Plugins `react()` and `tailwindcss()` — Tailwind v4 via its Vite plugin, so **no `tailwind.config.js` and no `postcss.config.js` exist by design**.
- `envDir: '..'` — env vars come from the **repo-root `.env`**, not `frontend/.env`. This trips people up.
- Alias `@` → `./src`, used in essentially every import.
- Dev server on `0.0.0.0:5173` with `watch.usePolling: true` for the Docker bind-mount.

[index.html](index.html) is a minimal shell: `<div id="root">` + the module script, title `HireFlow`. No favicon or meta tags yet.

**Docker:** [Dockerfile](Dockerfile) is multi-stage (`node:20-alpine` build → `nginx:1.27-alpine` serving `/app/dist`); [Dockerfile.dev](Dockerfile.dev) runs `npm install && npm run dev` at container start so the anonymous `node_modules` volume gets populated.

A top-level nginx proxy (see [../nginx/nginx.conf](../nginx/nginx.conf)) fronts everything on port 80: `/api/`, `/admin/`, `/health/`, `/media/` go to Django, `/` goes to this app. That same-origin arrangement is why the axios base URL is `http://localhost/api` and why `withCredentials` cookies work without CORS gymnastics.

---

## 3. Folder structure

```
frontend/
├── index.html                 SPA shell
├── vite.config.js             Vite + Tailwind v4, @ alias, envDir '..'
├── Dockerfile / Dockerfile.dev / .dockerignore
└── src/
    ├── main.jsx               entry: createRoot → <StrictMode><Providers/>
    ├── app/
    │   ├── providers.jsx      the provider stack
    │   ├── store.js           Redux store + axios interceptor wiring
    │   └── router.jsx         route table (lazy + Suspense)
    ├── routes/                ProtectedRoute, PublicOnlyRoute
    ├── lib/                   axios.js, queryClient.js
    ├── store/slices/          authSlice.js (the only slice)
    ├── features/              feature-sliced modules
    │   ├── auth/{api,components,pages,schemas}
    │   └── cvBuilder/{api,components,hooks,pages,schemas,utils}
    ├── components/
    │   ├── layout/            AppLayout, AuthLayout, PublicLayout
    │   ├── ui/                design-system primitives + barrel index.js
    │   ├── ErrorBoundary.jsx
    │   └── KanbanBoard|Charts|Notifications|ApplicationDrawer|UI/   EMPTY
    ├── pages/                 top-level pages (mix of real and 0-byte stubs)
    ├── context/               ThemeContext.jsx
    ├── hooks/                 useAppSelector.js
    ├── utils/                 extractApiError.js
    ├── api/                   EMPTY — superseded by features/*/api
    └── styles/index.css       the app's only stylesheet
```

**Two organizational schemes coexist.** Feature-sliced (`src/features/auth/{api,components,pages,schemas}`) is the live, working one. Flat legacy (`src/pages`, `src/api`, `src/components/<Domain>/`) is leftover scaffolding from the initial commit. **Build new work feature-sliced.**

---

## 4. Bootstrap

[src/main.jsx](src/main.jsx) renders `<StrictMode><Providers /></StrictMode>` and imports `@/styles/index.css`. There is no `<App />` — `Providers` renders the whole app including the router.

[src/app/providers.jsx](src/app/providers.jsx), outer → inner:

```
Redux Provider (store)
└── QueryClientProvider (queryClient)
    └── ThemeProvider
        └── GoogleOAuthProvider (VITE_GOOGLE_CLIENT_ID)
            └── BrowserRouter
                ├── ErrorBoundary → AppRouter
                └── Toaster (sonner, top-right, richColors, closeButton)
```

Order matters: `ErrorBoundary` sits **inside** `BrowserRouter` because its fallback renders a `<Link to="/">`.

[src/app/store.js](src/app/store.js) configures a single `auth` reducer and then calls `setupAxiosInterceptors(store)` as a **module side effect at import time**. That's how `lib/axios.js` reads and dispatches Redux state without a circular import — the axios module never imports the store; the store injects itself.

---

## 5. Route table — [src/app/router.jsx](src/app/router.jsx)

Every page is `React.lazy()` code-split under one top-level `<Suspense fallback={<PageLoader/>}>`.

| Path | Component | Layout | Guard |
|---|---|---|---|
| `/` | `LandingPage` ([src/pages/LandingPage.jsx](src/pages/LandingPage.jsx)) | `PublicLayout` | — |
| `/login` | `LoginPage` ([src/features/auth/pages/LoginPage.jsx](src/features/auth/pages/LoginPage.jsx)) | `AuthLayout` | `PublicOnlyRoute` |
| `/register` | `RegisterPage` | `AuthLayout` | `PublicOnlyRoute` |
| `/forgot-password` | `ForgotPasswordPage` | `AuthLayout` | — |
| `/reset-password/:token` | `ResetPasswordPage` | `AuthLayout` | — |
| `/verify-email/:token` | `VerifyEmailPage` | `AuthLayout` | — |
| `/home` | `HomePage` ([src/pages/HomePage.jsx](src/pages/HomePage.jsx)) | `AppLayout` | `ProtectedRoute` |
| `/cv-builder` | `CVBuilderPage` ([src/features/cvBuilder/pages/CVBuilderPage.jsx](src/features/cvBuilder/pages/CVBuilderPage.jsx)) | `AppLayout` | `ProtectedRoute` |
| `*` | `NotFoundPage` | `PublicLayout` | — |

There are two authenticated routes. `AppLayout`'s sidebar lists Dashboard and CV Builder, using `NavLink` so the active route highlights. The old placeholder Applications/Analytics entries (which both pointed at `/home`) were removed — add them back when their pages exist.

---

## 6. Auth guarding

[src/routes/ProtectedRoute.jsx](src/routes/ProtectedRoute.jsx) reads `state.auth.isAuthenticated`; false → `<Navigate to="/login" replace state={{from: location}} />`, else `<Outlet/>`. It also exports an unused `ProtectedRouteFallback`.

[src/routes/PublicOnlyRoute.jsx](src/routes/PublicOnlyRoute.jsx) is the mirror image: authenticated → `<Navigate to="/home" replace />`.

Both are **purely synchronous**, reading one boolean derived from the presence of an access token in `localStorage` at module-init time. Two consequences worth internalizing:

- There is no "verifying session" state, so no auth flash — but also **no token validity check**. An expired token renders `isAuthenticated: true`, `/home` mounts, the profile request 401s, the interceptor tries a refresh, and only if that fails does a hard redirect happen.
- `ProtectedRoute` records `state.from`, but **nothing consumes it** — `useLogin` always navigates to `/home`. Post-login return-to-intended-page is half-plumbed and unfinished.

---

## 7. HTTP layer — [src/lib/axios.js](src/lib/axios.js)

**Instance:** `baseURL: import.meta.env.VITE_API_URL || 'http://localhost/api'`, `withCredentials: true` (required — the refresh token is an HttpOnly cookie), JSON content type.

**Request interceptor:** reads `store.getState().auth.accessToken` on *every* request (rather than closing over a value) and sets `Authorization: Bearer <token>`, so rotation propagates immediately.

**Response interceptor — the refresh flow:**

1. Bail out unless status is `401`, `originalRequest` exists, `_retry` is falsy, and the URL is not `/auth/token/refresh/`. That last exclusion is what prevents an infinite loop.
2. If a refresh is already in flight, park the request in `failedQueue` as `{resolve, reject}`; on success rewrite its `Authorization` header and replay it. Standard single-flight pattern — no refresh stampede.
3. Otherwise mark `_retry`, `POST /auth/token/refresh/` with **no body** (the refresh token travels as the cookie), `dispatch(setCredentials(data.access))`, drain the queue, replay the original request.
4. On refresh failure: reject the queue, `dispatch(logout())`, and **hard-navigate** via `window.location.assign('/login')` (guarded against already being on `/login`). This is a full page reload — the one place the app leaves the SPA — which nukes the React Query cache, arguably the right call for a dead session.

[src/lib/queryClient.js](src/lib/queryClient.js): queries `retry: 1`, `staleTime: 5 min`, `refetchOnWindowFocus: false`; mutations `retry: 0`. No global `onError` — errors are handled per-hook with toasts.

---

## 8. State management

Three cleanly separated layers.

**Redux Toolkit — auth session only.** [src/store/slices/authSlice.js](src/store/slices/authSlice.js):

```js
state.auth = {
  accessToken: string | null,  // seeded from localStorage['accessToken'] at module load
  isAuthenticated: boolean,    // Boolean(accessToken)
}
```

Actions: `setCredentials(token)` (sets both fields, writes `localStorage`) and `logout()` (nulls both, removes the key). Every `localStorage` access is wrapped in `try/catch` for Safari private mode. Note there is **no `user` object in Redux** — identity comes from React Query's `['profile']` query.

**Token storage:** access token in `localStorage` under `accessToken` (JS-readable, so XSS-exposed — the usual tradeoff, and worth an explicit decision record given the refresh token is already correctly HttpOnly). Refresh token in an HttpOnly cookie set by Django, never touched by JS.

**TanStack Query** owns all server state. **React Context** owns theme only; React Hook Form owns local form state.

---

## 9. The auth feature module

### [api/authApi.js](src/features/auth/api/authApi.js) — thin axios wrappers

| Function | Endpoint | Payload |
|---|---|---|
| `register` | `POST /auth/register/` | `{email, full_name, password, password2}` |
| `login` | `POST /auth/login/` | `{email, password}` |
| `logout` | `POST /auth/logout/` | — (refresh cookie) |
| `forgotPassword` | `POST /auth/forgot-password/` | `{email}` |
| `resetPassword` | `POST /auth/reset-password/` | `{token, new_password, new_password2}` |
| `verifyEmail` | `GET /auth/verify-email/${token}/` | — |
| `getProfile` | `GET /users/profile/` | — |
| `googleLogin` | `POST /auth/google/` | `{access_token}` |

Convention: these return the **raw axios response**, not `response.data` — unwrapping happens in the query layer. All paths carry Django-style trailing slashes. The backend also exposes `POST /auth/github/` and `POST /users/change-password/`, which have **no frontend caller yet**.

### [api/authQueries.js](src/features/auth/api/authQueries.js) — React Query hooks

| Hook | Type | On success |
|---|---|---|
| `useLogin` | mutation | `setCredentials(data.access)`, toast, navigate `/home` |
| `useRegister` | mutation | toast the backend message, navigate `/login` |
| `useLogout` | mutation | **`onSettled`** (fires on success *and* failure): `logout()`, `queryClient.clear()`, navigate `/login` |
| `useForgotPassword` | mutation | toast the neutral non-enumerating message |
| `useResetPassword` | mutation | toast, navigate `/login` |
| `useVerifyEmail` | mutation | `setCredentials(data.access)` — **auto-login** — then navigate `/home` |
| `useGoogleLogin` | mutation | `setCredentials(data.access)`, navigate `/home` |
| `useProfile` | query | key `['profile']`, unwraps `data`, `enabled: isAuthenticated` |

Every error path is `toast.error(extractApiError(e))`. Good touches: `useLogout` uses `onSettled` so a failed server logout still clears the local session, and forgot-password copy is deliberately non-enumerating.

### [components/](src/features/auth/components/)

All named exports following one identical pattern: `useForm({resolver: zodResolver(schema), defaultValues})` → `<form noValidate className="space-y-4">` → heading → `<FormField>`s → `<Button type="submit" loading={mutation.isPending}>` → footer `<Link>`.

`LoginForm` (email/password + forgot link + "or" divider + `GoogleSignInButton`), `RegisterForm` (full_name/email/password/password2 — no Google button, asymmetric with login), `ForgotPasswordForm` (also renders a persistent success `Alert`), `ResetPasswordForm` (takes a `token` prop), `GoogleSignInButton` (uses `@react-oauth/google`'s `useGoogleLogin` implicit flow, aliased locally to avoid a name clash with our own hook, and posts `{access_token}` to the backend).

### [pages/](src/features/auth/pages/)

Thin **default-exported** wrappers (default export is required for `React.lazy`). `ResetPasswordPage` reads `useParams().token` and renders an error `Alert` if it's missing. `VerifyEmailPage` is the only one with real logic — it fires the mutation on mount and renders spinner / error-with-CTA / success states.

### [schemas/authSchemas.js](src/features/auth/schemas/authSchemas.js)

Zod v3. `loginSchema` (valid email; password min 1 only — correct for login), `registerSchema` (email valid, `full_name` 1–150, passwords min 8, cross-field `.refine` with the error attached to `path: ['password2']`), `forgotPasswordSchema`, `resetPasswordSchema` (min 8 + matching refine).

Field names are **snake_case to match the Django API directly** — there is no case-transformation layer anywhere in the app, and there shouldn't be one.

---

## 10. Component inventory

### UI primitives — [src/components/ui/](src/components/ui/)

All className-merged by template literal (no `clsx`/`cva`/`tailwind-merge` dependency), all re-exported from `index.js`.

| Component | API |
|---|---|
| `Button` | `variant`: primary \| secondary \| ghost \| danger; `size`: sm(h-9) \| md(h-11) \| lg(h-12); `loading` (inline spinner + forced `disabled`); `type` defaults to `"button"`; spreads `...props` |
| `Input` | `forwardRef` (essential for RHF `register()`); `error` boolean toggles red border/ring |
| `Card` | `rounded-2xl` bordered surface, `p-6`, `shadow-sm`, dark variants |
| `Alert` | `variant`: info \| success \| warning \| error |
| `Spinner` | fixed 8×8 indigo ring in a centering wrapper |
| `FormField` | composes `<label>` + `<Input>` + error `<p>`; props `id, label, type, error, registration, placeholder, autoComplete` |
| `index.js` | barrel: `Alert, Button, Card, FormField, Input, Spinner` |

Two gaps to know: `FormField` has a **closed prop list** (no `...rest`), so `disabled`, `min`, `inputMode` etc. silently do nothing — extend it when you add non-text fields. And there is no `Select`, `Textarea`, `Checkbox`, `Modal`, `Badge`, `Table`, or `Tooltip` yet; the CV Builder UI will need most of those.

### Layouts — [src/components/layout/](src/components/layout/)

- **`AppLayout`** — authenticated shell: fixed 64-wide sidebar (`hidden md:flex`, so **there is no mobile navigation**), nav items, header showing `profile?.user?.full_name` (fallback `'there'`), theme toggle, logout wired to `useLogout()`, `<main><Outlet/></main>`.
- **`AuthLayout`** — centered `max-w-md` card on an indigo→white gradient, brand link, tagline "Track. Automate. Get Hired."
- **`PublicLayout`** — sticky blurred header, auth-aware CTAs (Dashboard vs. Log in / Sign up), footer with dynamic year.

### [ErrorBoundary.jsx](src/components/ErrorBoundary.jsx)

Class component, named export, `getDerivedStateFromError` → fallback UI with Refresh and Go-home buttons. It has **no `componentDidCatch`**, so errors are never logged or reported anywhere, and the only reset path is a full reload.

### Empty, planned-but-unimplemented directories (`.gitkeep` only)

`src/components/KanbanBoard/`, `src/components/Charts/`, `src/components/Notifications/`, `src/components/ApplicationDrawer/`, `src/components/UI/`, and `src/api/`.

---

## 11. `src/pages` — implemented vs. stub

| File | Status |
|---|---|
| `LandingPage.jsx` | **Implemented** — hero, three feature cards, gradient CTA |
| `HomePage.jsx` | **Implemented** — greeting via `useProfile()` + four stat cards with **hardcoded `'0'`** placeholder data |
| `NotFoundPage.jsx` | **Implemented** — 404 with back-home CTA |
| `Dashboard.jsx` | **0 bytes** |
| `Analytics.jsx` | **0 bytes** |
| `Reports.jsx` | **0 bytes** |
| `Notifications.jsx` | **0 bytes** |
| `Settings.jsx` | **0 bytes** |
| `Login.jsx` | **0 bytes** — dead; the real one is `features/auth/pages/LoginPage.jsx` |
| `Register.jsx` | **0 bytes** — dead; superseded by the feature module |

Seven of ten files here are zero-byte placeholders and none are routed.

---

## 12. Styling

[src/styles/index.css](src/styles/index.css) is the app's only stylesheet, 19 lines:

```css
@import 'tailwindcss';
@custom-variant dark (&:where(.dark, .dark *));   /* required — see below */
:root { --color-primary: 79 70 229; --color-primary-hover: 67 56 202; }
html { scroll-behavior: smooth; }
body { @apply bg-slate-50 text-slate-900 antialiased; }
.dark body { @apply bg-slate-950 text-slate-100; }
```

- **Tailwind CSS v4**, configured entirely through the Vite plugin — no config file, no `@theme` block. Utility classes only; no CSS Modules or styled-components.
- **Design tokens** are just two custom properties holding space-separated RGB channels for the indigo primary (indigo-600 / indigo-700), consumed only by `Button`'s primary variant via `bg-[rgb(var(--color-primary))]`. Everything else uses raw Tailwind palette classes — `slate` for neutrals, `indigo` for brand, `emerald`/`amber`/`red`/`blue` for Alert semantics. So the token layer exists but is ~95% bypassed.
- **Dark mode:** `ThemeContext` toggles a `.dark` class on `document.documentElement`, persisted to `localStorage['hireflow-theme']`, defaulting to `prefers-color-scheme`.

> **Do not remove the `@custom-variant` line.** In Tailwind v4 the `dark:` variant follows `prefers-color-scheme` by default; class-based toggling needs `@custom-variant dark (&:where(.dark, .dark *));` in the CSS entry (the v4 replacement for v3's `darkMode: 'class'`). It was missing originally, so the toggle restyled only `body` while every component followed the OS setting. Verified fixed: the built CSS now emits `:where(.dark, .dark *)` selectors and zero `prefers-color-scheme` rules.

---

## 13. Auth flow, end to end

- **Register** → Zod validate → `POST /auth/register/` → toast → redirect `/login`. No tokens issued; verification required.
- **Verify email** → user clicks the emailed link → `/verify-email/:token` → `GET /auth/verify-email/:token/` → `{access}` + refresh cookie → **auto-logged-in**, redirect `/home`.
- **Login** → `POST /auth/login/` → `{access}` in body, refresh token in HttpOnly cookie → `setCredentials` writes Redux + `localStorage` → `/home`.
- **Google** → implicit flow yields a Google access token → `POST /auth/google/` → same shape → `/home`.
- **Authenticated requests** → interceptor attaches `Authorization: Bearer`; `withCredentials` sends the cookie.
- **Refresh** → any 401 (except on the refresh endpoint, once per request) triggers a single-flight `POST /auth/token/refresh/`; concurrent 401s queue and replay. Backend rotates and blacklists the old refresh token.
- **Session death** → refresh fails → queue rejected → `logout()` → hard `window.location.assign('/login')`.
- **Logout** → `POST /auth/logout/` → `onSettled` clears Redux, `queryClient.clear()`, navigate `/login`.
- **Password reset** → `/forgot-password` → neutral message always → emailed link → `/reset-password/:token` → `POST /auth/reset-password/` → `/login`.

**Env vars consumed:** `VITE_API_URL` and `VITE_GOOGLE_CLIENT_ID`, both read from the repo-root `.env` (because of `envDir: '..'`). Both are **baked into the client bundle at build time** — fine for a public API URL and a public OAuth client ID. Rule to keep: never put a secret behind a `VITE_` prefix, since everything so prefixed ships to the browser.

---

## 14. Conventions for adding features

**Module layout.** New domains go in `src/features/<domain>/` mirroring `auth`:
`api/<domain>Api.js` (raw axios wrappers returning the full response) · `api/<domain>Queries.js` (React Query hooks that unwrap `data`, dispatch, toast, navigate) · `components/` (named exports) · `pages/` (**default exports**, required for `React.lazy`) · `schemas/<domain>Schemas.js` (Zod).
Do **not** add to the legacy `src/api/`, and reserve `src/pages/` for genuinely cross-cutting pages like the landing page and 404.

**Imports.** Always the `@/` alias, never relative `../../`. Import primitives from the barrel: `import { Button, Card } from '@/components/ui'`.

**Routing.** Add a `lazy()` import in [src/app/router.jsx](src/app/router.jsx) and nest the `<Route>` under the right guard + layout pair. Authenticated pages go inside `<ProtectedRoute>` → `<AppLayout>`; add the sidebar entry to `AppLayout`'s `navItems` too (and fix the three placeholder `/home` targets while you're in there).

**Data fetching.** Never call axios from a component — wrap it in an `api/` function, then a query hook. Query keys are plain arrays (`['profile']`); adopt a key factory once the key space grows. Mutations own their side effects (toast, navigate, dispatch) inside the hook, not the component. After writes, `queryClient.invalidateQueries({queryKey: [...]})` — note the codebase has **no example of this yet**, since `useLogout`'s `queryClient.clear()` is the only cache manipulation so far.

**Errors.** Always `toast.error(extractApiError(error))`. [src/utils/extractApiError.js](src/utils/extractApiError.js) recursively walks DRF payloads (strings, arrays, nested objects) and returns the **first** message, falling back to `error.message` then a generic string. Because it surfaces only one message, multi-field server errors collapse into a single toast — so keep validation mirrored client-side in Zod.

**Forms.** `useForm` + `zodResolver` + `defaultValues` for every field; `<form noValidate className="space-y-4">`; one `<FormField>` per input with `registration={register('name')}` and `error={errors.name}`; submit button gets `loading={mutation.isPending}`. Cross-field rules via `.refine(..., {path: ['field']})`.

**Naming.** Payload and response fields stay **snake_case end-to-end** to match Django. Components are named exports; lazy-loaded pages are default exports.

**Styling.** Tailwind utilities inline. For a new variant-bearing primitive, follow `Button.jsx`: a module-level `variants`/`sizes` lookup object plus template-literal concatenation with a `className = ''` prop appended last. Pair every light class with a `dark:` counterpart. Neutrals are `slate`, brand is `indigo`.

**Redux.** Reserve it for genuinely global client state; server data belongs in React Query. New slices go in `src/store/slices/` and register in `src/app/store.js`; access via [src/hooks/useAppSelector.js](src/hooks/useAppSelector.js) (thin passthroughs today — they exist as the seam for a future TypeScript migration's typed hooks).

---

## 15. Known issues

Ordered by impact.

1. **Production nginx lacks an SPA history fallback** (`try_files $uri /index.html`) — a hard refresh or direct link to `/login`, `/home`, or `/reset-password/:token` returns a raw nginx 404 in production. Dev via Vite is fine.
2. **`src/components/UI/` vs `src/components/ui/` case collision** — breaks checkout and builds on case-insensitive filesystems (macOS, Windows). Delete `src/components/UI/.gitkeep`.
3. **`VerifyEmailPage` fires its mutation from a `useEffect`** with `[token]` deps. Under React 19 StrictMode's dev double-effect this posts twice against a single-use token, and the second call's error toast can win the race. Use `useQuery` with `retry: false`, or a `useRef` guard.
4. **Post-login redirect-to-intended is unfinished** — `ProtectedRoute` records `state.from` but `useLogin` ignores it.
5. **Access token in `localStorage` is XSS-readable** — an accepted tradeoff, but worth recording as a deliberate decision.
6. **`ErrorBoundary` swallows errors** with no `componentDidCatch` logging or reporting.
7. **No tests, no linting, no formatting config**, and no mobile navigation (the sidebar is `hidden md:flex`, so the CV Builder is desktop-only for navigation purposes).
8. Dead files to delete: `src/pages/Login.jsx`, `src/pages/Register.jsx`, `src/api/.gitkeep`, and the unused `ProtectedRouteFallback` export.

---

## 16. The CV Builder module

`src/features/cvBuilder/` — spec Step 10, built against the live Steps 1–6 API. Route `/cv-builder`.

```
features/cvBuilder/
├── api/cvApi.js            one wrapper per backend endpoint, mirrors urls.py 1:1
├── api/cvQueries.js        React Query hooks + cvKeys + shared invalidation
├── constants.js            choice options, months, weights, step list, date formatting
├── schemas/cvSchemas.js    Zod mirrors of the backend serializer validation
├── utils/payload.js        '' -> null coercion, tech_stack parsing, URL scheme fix
├── hooks/                  useAutosave, useDebouncedValue, useReorder
├── components/             CompletionBar, StepNavigator, SectionShell, EntryCard, SaveStatus
├── components/steps/       ContactStep, ExperienceStep (+ExperienceForm, BulletList),
│                           EducationStep, SkillsStep, ProjectsStep, ExtrasStep
└── pages/CVBuilderPage.jsx shell: ensure-profile, completion bar, step nav, prev/next
```

**Load sequence.** `GET /cv/profile/` 404s until a CV shell exists, so the page POSTs first (idempotent per spec §2.1, guarded by a ref against StrictMode's double effect) and only enables the profile and completion queries once that resolves.

**Server is authoritative on scoring.** The completion bar and the step-navigator dots both read the backend's `completion_score` / `section_completion`. `constants.js` duplicates the weights only to explain the score in copy — never to compute it.

**Cache invalidation.** Every section write goes through `useSectionMutation`, which invalidates that section's list plus `cvKeys.profile` and `cvKeys.completion`, because any child write changes the score. Bullet writes invalidate the *experience* list, since bullets arrive nested there.

**Two different save models, and the UI must say so.** Contact & Summary autosaves and has an explicit "Save section" button. Every other section writes immediately on add/edit — there is no save button because there is nothing to defer. That asymmetry reads as data loss if unlabelled, so `SectionShell` shows a "Saves automatically" badge by default (`autosaves={false}` on Contact), and every mutation toasts on success. Skills and bullets originally saved silently; don't remove those toasts.

**Why the score looks stalled.** Scoring is all-or-nothing per section: an experience with one bullet scores 0 of 25, and four skills score 0 of 15. `STEPS` in `constants.js` carries `points` and `requirement` per step purely so the navigator can explain this. Those numbers mirror `services/completion.py` (25/10/25/15/15/10, complete at 75) — if the backend weights change, change them here too. The completion bar is rendered twice, in the header and in the sticky nav card, because the header scrolls out of view while editing and the score is the main signal that a write landed.

**Invalidation uses `refetchType: 'all'`.** The React Query default (`'active'`) skips disabled or unmounted observers, which can leave the completion bar showing a stale score after a write. Don't drop it.

**Autosave applies to the profile only.** Child resources expose no PATCH, so they use explicit save. Two non-obvious details in `useAutosave`, both worth preserving: it subscribes to RHF's `watch` rather than `isDirty` (which latches `true` and would silence every save after the first), and it gates on `profileSchema.safeParse` so a half-typed URL never fires a PATCH that 400s invisibly. Failed saves back up to `sessionStorage`; `ContactStep` reads that back on mount and offers a recovery banner.

**Reorder is buttons, not drag-and-drop.** Deliberate: the backend rejects the whole batch if any id fails the ownership check, so the full ordered array must always be sent — `useReorder` does exactly that. It also avoids a new dependency and is keyboard-accessible. Swap in `@dnd-kit` later if you want, but keep sending the complete list.

**Two contract traps encoded here.** Django's `URLField` validator runs before the backend's `normalize_profile_url`, so `toAbsoluteUrl` prepends `https://` client-side for all five URL fields. And `Education.cgpa` is `DecimalField(max_digits=3)`, so the schema caps CGPA below 10 even though the form accepts any scale.

### Adding a section

1. Add wrappers to `cvApi.js`, then hooks to `cvQueries.js` via `useSectionMutation`.
2. Add a Zod schema mirroring the serializer, and any choice values to `constants.js`.
3. Build the step under `components/steps/` using `SectionShell` + `EntryCard` + a `Modal` form.
4. Register it in `STEPS` (`constants.js`) and in `CVBuilderPage`'s switch.

---

## 17. Where to look next

- Backend counterpart, including the full API surface this app talks to: [backend/context.md](../backend/context.md).
- Upload + AI parse (spec Steps 7–8) and PDF export (Step 9) are the next builds, but **each needs its backend endpoints first** — `POST /cv/upload/`, the status/apply routes, and the export routes do not exist yet. Designs are in [docs/cv_builder_spec.md](../docs/cv_builder_spec.md); the upload status poller and diff modal are specced in §10.4–10.5.
