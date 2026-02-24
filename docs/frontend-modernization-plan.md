# Frontend Modernization Plan

**Branch:** `frontend-modernization`, cut from `main` after `ui-consistency` merges

**Estimated effort:** 1.5–2 working days (sequential — steps cannot be parallelized)

---

## Overview

Migrate the frontend from Create React App (abandoned upstream) to Vite. Along the way: upgrade TypeScript, fix the tsconfig for a modern target, remove ~200MB of dead webpack/babel dependencies, and clean up CRA boilerplate. Steps are ordered so each one leaves the app in a buildable, testable state.

---

## Step 1 — Vite + Vitest setup (the anchor change)

This is the largest step and everything else depends on it being correct first.

### Build tooling
- Install: `vite`, `@vitejs/plugin-react`
- Remove: `react-scripts`
- Create `vite.config.ts`:
  - `base: '/tennis_coach_app/'` — required for GitHub Pages subpath; without this all assets 404 in production
  - Proxy `/v0` → `http://backend:8000` for local dev (replaces CRA's `proxy` in package.json)
  - Plugin: `@vitejs/plugin-react`

### Test tooling
- Install: `vitest`, `@vitest/coverage-v8`, `jsdom`, `@vitest/ui`
- Configure in `vite.config.ts` under `test:`:
  - `globals: true` — enables `vi.*` as globals (matches Jest's behavior)
  - `environment: 'jsdom'`
  - `setupFiles: ['src/setupTests.ts']` — Vitest doesn't auto-discover this unlike Jest
  - `coverage` thresholds moved from `package.json` jest block to here (same values)

### Test file migration (all 13 files)
Mechanical but must be done manually — not fully auto-fixable:
- `jest.fn()` → `vi.fn()`
- `jest.mock()` → `vi.mock()` (note: `vi.mock` is hoisted like Jest, but double-check each usage)
- `jest.spyOn()` → `vi.spyOn()`
- `jest.clearAllMocks()` / `jest.resetAllMocks()` → `vi.clearAllMocks()` / `vi.resetAllMocks()`

Files to update (files marked ✓ have zero `jest.*` calls and need no migration work):
1. `src/App.test.tsx`
2. `src/components/AuthForm.test.tsx`
3. `src/components/ErrorBoundary.test.tsx`
4. `src/components/LoadingIndicator.test.tsx`
5. `src/components/ProgressBar.test.tsx`
6. `src/components/VideoList.test.tsx` — grew significantly; now mocks VideoFilters, VideoEditModal, Icons, VideoUpload
7. `src/components/__tests__/TimingPerformance.test.tsx`
8. `src/hooks/useAnalysisManager.test.tsx`
9. `src/hooks/useServeProposals.test.tsx`
10. `src/hooks/useServeWindows.test.tsx`
11. `src/hooks/useVideoUrl.test.ts`
12. `src/utils/__tests__/canvasDrawing.test.ts` ✓ — added in ui-consistency branch; pure assertions, no mocks
13. `src/utils/__tests__/validation.test.ts` ✓ — pure assertions, no mocks

### ESLint config replacement (MUST be in this step — pre-commit blocks on it)
`package.json` currently extends `"react-app"` and `"react-app/jest"` — both are bundled inside
`react-scripts`. Removing react-scripts without replacing this will break `npm run lint` and
block every commit via the pre-commit hook.

- Install: `eslint-config-react-app` as an explicit devDependency (it can be used standalone)
- Drop `"react-app/jest"` extend — replace with Vitest globals in eslint config
- Or: replace entirely with `@eslint/js` + `@typescript-eslint/eslint-plugin` + `eslint-plugin-react` + `eslint-plugin-react-hooks`. More work but cleaner long-term.

### package.json scripts
- `"start"`: `react-scripts start` → `vite`
- `"build"`: `react-scripts build` → `vite build`
- `"test"`: `react-scripts test` → `vitest`
- `"test:ci"`: → `vitest run --coverage`
- Remove the `"eject"` script
- Move `jest` coverage config block out of package.json into `vite.config.ts`

### `public/index.html`
- Replace all three `%PUBLIC_URL%` occurrences with empty string (Vite uses `/` directly):
  - `href="%PUBLIC_URL%/favicon.ico"` → `href="/favicon.ico"`
  - `href="%PUBLIC_URL%/logo192.png"` → `href="/logo192.png"`
  - `href="%PUBLIC_URL%/manifest.json"` → `href="/manifest.json"`
- Remove the CRA comments in the file

### Docker + nginx
- `Dockerfile` development CMD: `npm start` → `npm run dev` (or keep `npm start` if script is updated)
- `Dockerfile` production build: output path `/app/build` → `/app/dist`
  - Line 42: `COPY --from=builder /app/build` → `COPY --from=builder /app/dist`
- `nginx.conf`: verify static file root path is correct for `/dist`
- `docker-compose.yml`: remove `CHOKIDAR_USEPOLLING=true` (react-scripts/webpack concept; Vite uses its own watcher)

### Delete CRA boilerplate
- `src/react-app-env.d.ts` — CRA-specific type shim, not needed
- `src/reportWebVitals.ts`
- Remove `reportWebVitals` import and call from `src/index.tsx`

### `.gitignore`
- `/build` → `/dist`

---

## Step 2 — Env var rename (`REACT_APP_*` → `VITE_*`)

Vite only exposes env vars prefixed with `VITE_` and uses `import.meta.env.VITE_*` (build-time
substitution). Any unrenamed var becomes `undefined` at runtime and the app silently falls back
to `http://localhost:8000` everywhere — including production.

### Source files (9 files, ~12 occurrences)
Change both the variable name and the access syntax:
- `process.env.REACT_APP_*` → `import.meta.env.VITE_*`

| File | Variables |
|------|-----------|
| `src/services/api.ts` | `REACT_APP_API_URL` |
| `src/services/supabaseClient.ts` | `REACT_APP_PROFILE`, `REACT_APP_SUPABASE_URL`, `REACT_APP_SUPABASE_PUBLISHABLE_KEY` |
| `src/utils/authInterceptor.ts` | `REACT_APP_PROFILE` |
| `src/components/pages/HomePage.tsx` | `REACT_APP_PROFILE` |
| `src/components/pages/DemoPage.tsx` | `REACT_APP_PROFILE`, `REACT_APP_API_URL` |
| `src/components/pages/VideoAnalysisPage.tsx` | `REACT_APP_API_URL` |
| `src/hooks/useAdmin.ts` | `REACT_APP_PROFILE` |
| `src/components/layouts/AppLayout.tsx` | `REACT_APP_PROFILE` |
| `src/components/layouts/ProtectedRoute.tsx` | `REACT_APP_PROFILE` |

### Config files
- `frontend/.env`: rename all keys
- `frontend/.env.example`: rename all keys

### CI/CD workflows (EASY TO MISS — production breaks without this)
- `.github/workflows/deploy-frontend.yml` — the `Build` step sets env vars inline:
  ```yaml
  env:
    REACT_APP_PROFILE: production          # → VITE_PROFILE
    REACT_APP_API_URL: ${{ secrets.REACT_APP_API_URL }}  # → VITE_API_URL: ${{ secrets.VITE_API_URL }}
    REACT_APP_SUPABASE_URL: ...            # → VITE_SUPABASE_URL
    REACT_APP_SUPABASE_PUBLISHABLE_KEY: ... # → VITE_SUPABASE_PUBLISHABLE_KEY
  ```
- Also update the artifact upload path: `path: frontend/build` → `path: frontend/dist`
- `.github/workflows/ci.yml` — the frontend `Build` step runs `npm run build` with no env vars
  set (relies on defaults). This is fine for CI but worth noting.

### GitHub Secrets — must be renamed
The workflow references `secrets.REACT_APP_API_URL` and `secrets.REACT_APP_SUPABASE_URL`. After
renaming the workflow to use `secrets.VITE_API_URL` etc., the old secrets will no longer be
read. **Add the renamed secrets to GitHub before merging this branch** (Settings → Secrets →
Actions). The old secrets can be deleted after confirming deploy works.

---

## Step 3 — TypeScript upgrade + tsconfig fixes

### Upgrade TypeScript
- `typescript` 4.9 → `^5.0` (currently `^4.9.5`)
- Fix any new type errors surfaced by TS5 strictness (unlikely to be many; strict mode was already on)

### `tsconfig.json` changes
```json
{
  "compilerOptions": {
    "target": "ES2020",          // was "es5" — ES5 was for IE11, which is dead
    "moduleResolution": "bundler", // was "node" — correct mode for Vite
    "useDefineForClassFields": true // add — required with ES2022+ targets
    // remove "isolatedModules" — Vite handles this natively via esbuild
  }
}
```

Note: `"moduleResolution": "bundler"` can surface import errors in packages that have unusual
`exports` fields. Run `npm run type-check` and fix any new errors before proceeding.

---

## Step 4 — Remove dead dependencies

Remove from `package.json`:
- `react-scripts` (the main event — eliminates webpack, babel, jest, ~200 transitive deps)
- `web-vitals` (already deleted the file in Step 1; remove the package too)
- `@types/jest` (Vitest ships its own types via `globals: true`)
- `@types/axios` (axios ships its own types)
- **The entire `overrides` block** — every entry was patching CRA's ancient dep tree. With
  react-scripts gone, these entries either do nothing or actively mislead. Delete all of them.

Run `npm install` and verify `package-lock.json` regenerates cleanly. The lockfile will change
substantially — this is expected.

---

## Step 5 — Axios removal (previously deferred — recommend doing it now)

The review found that deferring axios is the wrong call: you're already testing every API call,
already in "break everything and fix it" mode, and the interceptor is ~26 lines. Doing it in a
separate PR means the next person adds code around axios, and the effort grows.

**What to replace:**
- `src/services/api.ts`: replace axios instance with a typed `fetch` wrapper (base URL config,
  timeout via `AbortController`, JSON serialization)
- `src/utils/authInterceptor.ts`: ~26 lines; rewrite as a thin wrapper that injects the auth
  header
- Error normalization (FastAPI validation errors → string): move into the fetch wrapper

Remove: `axios`, `@types/axios`

If this feels too risky to bundle in, it can still be deferred — but acknowledge the asymmetric
cost.

---

## Step 6 — Doc updates

| File | Change |
|------|--------|
| `.cursor/rules/frontend-testing-patterns.mdc` | Update description ("Jest + React Testing Library" → "Vitest + React Testing Library"); replace all `jest.fn()`/`jest.mock()` examples with `vi.fn()`/`vi.mock()`; note that `vi` is a global (no import needed with `globals: true`) |
| `.cursor/rules/react-routing.mdc` line 127 | `REACT_APP_PROFILE=local` → `VITE_PROFILE=local` |
| `frontend/.env.example` | Rename all keys (covered in Step 2) |
| `frontend/README.md` | Update env var names (5 references), test command, build output path |
| `frontend/docs/api-integration.md` | Update any `REACT_APP_API_URL` references |

---

## Commit strategy

One commit per step, in order. This makes bisecting possible if something breaks.

```
feat: migrate CRA to Vite + Vitest, replace ESLint config
feat: rename REACT_APP_* to VITE_*, update CI workflow and GitHub secrets
feat: upgrade TypeScript 4.9 → 5.x, fix tsconfig target and moduleResolution
chore: remove react-scripts, dead deps, and overrides block
feat: replace axios with native fetch  (if doing Step 5)
docs: update cursor rules and README for Vite/Vitest migration
```

---

## Pre-merge checklist

- [ ] `docker compose up --build` — dev server starts, HMR works
- [ ] Dev server starts in <5s (the whole point)
- [ ] All 12 test files pass: `npm test`
- [ ] `npm run type-check` clean
- [ ] `npm run lint` clean (verify ESLint config replacement works)
- [ ] Production build works: `docker build --target production frontend/`
- [ ] Env vars resolve in browser (check Network tab — API calls should hit the right host)
- [ ] GitHub Pages URL loads assets correctly (verify subpath `/tennis_coach_app/` works)
- [ ] Pre-commit hook passes on a test commit

---

## Production env var status by service

See the section below for what needs changing in each external service.
