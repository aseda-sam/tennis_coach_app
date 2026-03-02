# S²Serve — Frontend

Technical frontend guide for contributors working in `frontend/`.

For product context, screenshots, and a quick project intro, start at the root [`README.md`](../README.md).

## Quick start

**Prerequisites:** Node.js 18+, backend running (see [backend README](../backend/README.md)).

```bash
npm install
npm start          # Vite dev server → http://localhost:3000
```

Or via Docker from the repo root (preferred):

```bash
docker compose up --build
```

### Environment

Create a `.env` file in `frontend/`:

```bash
VITE_API_URL=http://localhost:8000
VITE_SUPABASE_URL=https://your-project.supabase.co/
VITE_SUPABASE_PUBLISHABLE_KEY=your-publishable-key
VITE_MAX_FILE_SIZE=104857600    # 100 MB
VITE_DEBUG=true
```

Docker Compose provides defaults for local dev — no `.env` needed.

## Scripts

```bash
npm start              # Dev server (Vite)
npm test               # Tests (Vitest, watch mode)
npm run test:ci        # Tests once + coverage
npm run lint           # ESLint
npm run lint:fix       # ESLint auto-fix
npm run format         # Prettier (run before committing)
npm run format:check   # Prettier check only
npm run type-check     # tsc --noEmit
npm run build          # Production build
```

## Project structure

```
frontend/
├── public/                    # Static assets (favicon, manifest, brand mark)
├── src/
│   ├── components/
│   │   ├── layouts/           # AppLayout, ProtectedRoute
│   │   ├── pages/             # Route-level pages (Home, Library, Demo, Analysis, Admin)
│   │   ├── DemoTour/          # Guided tour overlay for demo page
│   │   └── ...                # Feature components (serve navigator, video player,
│   │                          #   phase timeline, trophy filmstrip, detection panels, etc.)
│   ├── hooks/                 # Custom hooks (auth, analysis, serve playback, video state)
│   ├── services/              # API client modules (api.ts, biomechanicsApi, playerApi, etc.)
│   ├── types/                 # TypeScript type definitions
│   ├── utils/                 # Shared utilities (auth interceptor, canvas drawing, validation)
│   ├── constants/             # App-wide constants
│   ├── lib/                   # Third-party wrappers
│   ├── design-tokens.css      # Design system tokens
│   ├── router.tsx             # React Router config (lazy-loaded pages)
│   └── index.tsx              # Entry point
├── VISUAL_IDENTITY.md         # Aesthetic north star — read before any UI work
├── DESIGN.md                  # CSS component patterns reference
└── package.json
```

## Stack

- **Vite** — build tool and dev server
- **React 18** + **TypeScript**
- **React Router v6** — URL-based routing with lazy-loaded pages
- **React Query** (`@tanstack/react-query`) — data fetching and cache
- **Recharts** — feature curves and metrics charts
- **Supabase** — auth (production only; local dev bypasses auth)
- **Vitest** + **React Testing Library** — tests
- **Lucide React** — icons
- **CSS Modules / design tokens** — styling (no Tailwind runtime; `clsx` + `tailwind-merge` for class composition)

## Routing

| Path | Page | Auth |
|---|---|---|
| `/` | Home — CTAs for Demo and Upload | No |
| `/demo` | Demo analysis dashboard | No |
| `/library` | Video library (upload, browse) | Yes |
| `/analysis/:videoId` | Analysis dashboard for a video | Yes |
| `/player/analysis` | Player-level analysis | Yes |
| `/admin/demos` | Demo video administration | Yes (admin) |

Demo video metadata is prefetched on the home page for fast demo load.

## Key patterns

- **Auth:** Supabase in production, mock user in local. `ProtectedRoute` wraps auth-gated pages. `useAuth` hook for session state.
- **Analysis dashboard:** Shared between authenticated users and the public demo page. New API calls in this tree must handle unauthenticated demo access (see `CLAUDE.md` demo compatibility rules).
- **Data fetching:** React Query for all API calls. API client modules live in `services/`.
- **Styling:** Design tokens in `design-tokens.css`. Read `VISUAL_IDENTITY.md` before UI work. `DESIGN.md` has CSS component patterns.
- **Code splitting:** Pages are `React.lazy` loaded via the router.

## Testing

```bash
npm test                           # Watch mode
npm run test:ci                    # CI (single run + coverage)
npm test -- VideoList.test.tsx     # Specific file
```

Tests use Vitest + React Testing Library. Mock external dependencies (API, Supabase). See `CLAUDE.md` testing section for when to write tests first vs. after.

## Deployment

### GitHub Pages (current)

Automatic via GitHub Actions on pushes to `main`. Built with `vite build`.

### Docker

```bash
docker build -t s2serve-frontend .
docker run -p 80:80 s2serve-frontend
```

## Troubleshooting

**API connection errors:** Check backend is running, `VITE_API_URL` is set, CORS is configured.

**Build errors:**
```bash
rm -rf node_modules package-lock.json
npm install
```

**Pre-commit hook failures:** Most often `frontend-prettier` — run `npm run format`, re-stage, commit again.
