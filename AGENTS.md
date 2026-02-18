# AGENTS.md

## Project overview

Tennis Coach App — a serve-analysis MVP. Users upload serve videos, the app runs pose estimation (MediaPipe), tags serve windows, segments the serve into biomechanics phases, and returns raw metrics for review.

**Stack:** FastAPI backend, React/TypeScript frontend, PostgreSQL (Docker local / Supabase prod), Redis Queue (RQ) for background jobs, Docker Compose for local dev.

## Quick reference

```bash
# Start everything (preferred local dev method)
docker compose up --build

# Run backend tests
docker compose exec backend pytest

# Run frontend tests
docker compose exec frontend npm test

# Backend lint/format
cd backend && ruff check . --fix && ruff format .

# Frontend lint
cd frontend && npm run lint

# Backend dependency management (uses uv, not pip)
cd backend && uv pip install -e ".[dev]"   # install/sync all deps
cd backend && uv pip install <package>      # add a package to the venv
# After adding a package, also add it to pyproject.toml dependencies
```

- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API docs: http://localhost:8000/docs
- RQ Dashboard: http://localhost:9181

## Project structure

```
backend/
  app/
    api/routes/       # FastAPI endpoints
    api/schemas/      # Pydantic request/response models
    models/           # SQLAlchemy ORM models
    services/         # Business logic (no HTTP concerns)
    core/config.py    # Settings / env vars
    core/database.py  # DB session setup
    utils/            # Error handling, auth helpers, logging, metrics
  alembic/            # DB migrations
  tests/              # pytest tests
frontend/
  src/
    components/       # React components
    hooks/            # Custom React hooks
    services/         # API client calls
    types/            # TypeScript types
    utils/            # Shared utilities
    lib/              # Third-party wrappers
    constants/        # App-wide constants
    design-tokens.css # Design system tokens
data/
  videos/
    raw/              # Uploaded user videos
    processed/        # Transcoded/processed videos
    demo/             # Curated demo videos (controlled subset visible to users)
  database/           # Local DB volume mount (empty until docker compose up)
project_docs/
  diagrams/           # Mermaid architecture diagrams (system overview, auth, upload,
                      # analysis pipeline, serve feedback pipeline, data flow, DB relationships)
writing/              # Substack context, LTA coaching notes, story seeds (gitignored — local only)
```

## Architecture rules

- **Layers:** Routes handle HTTP + auth, Services handle logic, Models define schema. Don't leak HTTP concerns into services.
- **Auth:** `Depends(get_current_user)` on protected endpoints. AuthZ via `app.utils.authorization` helpers. Always scope queries by `user_id`.
- **Errors:** Use `APIError` / `log_and_raise_error` from `app.utils.error_handling`. Never leak internals in 500s.
- **Storage:** Always go through `app.services.storage_service.storage_service`. No raw `open()` in routes/services.
- **Background jobs:** Use RQ + `VideoJob` for anything > 5s. Jobs create their own DB sessions.
- **API versioning:** All endpoints under `/v0/` (alpha, breaking changes allowed).
- **DB changes:** If you modify models, update `backend/docs/database_schema.md` and create an Alembic migration.

## Testing

- **TDD:** Write failing test first, implement, refactor.
- **Contract tests** for API endpoints (status codes + response shape). If you change a schema, update tests.
- **Unit tests** for service/business logic with mocked dependencies.
- **Mock externals** (Redis, storage, external APIs) unless explicitly integration testing.

## Code style

- **Python:** Type hints required. `ruff` for formatting/linting. Pre-commit hook runs ruff automatically. **`uv`** for package management (not pip).
- **React:** Use React Query for data fetching. Design tokens for styling (see `frontend/DESIGN.md`). Avoid `any` in TypeScript.
- **General:** KISS, DRY, YAGNI. No speculative abstractions.

## Product design philosophy

These constraints apply when building any user-facing feature. They come from hard-won lessons about what this app actually is (and isn't).

- **Practice > analysis.** The goal is to get users serving on a court, not spending more time in the app. Every feature should push them toward action, not deeper analysis. If a new UI element could trap a user in a stats-browsing loop, reconsider it.
- **Progressive disclosure.** Show one thing at a time. Don't front-load metrics, options, or complexity. Unlock detail as users demonstrate understanding.
- **App ≠ live coach.** The app gives asynchronous video feedback. It cannot see confusion, adjust in real time, or replace the feel of a human coach. Don't build features that pretend otherwise. Be honest about the medium's limits.
- **LTA L1 is context, not a pivot.** The coaching course informs design thinking. It does not override the current roadmap or justify new complexity. Real technique-teaching frameworks are LTA L2+ territory.
- **The app is a coach-prep tool.** Help users identify what to work on, give them language to use with a coach, encourage them to practice. It complements coaches; it doesn't replace them.

## Commits

- Do not add `Co-Authored-By` lines to commit messages.

## Detailed rules

Comprehensive coding conventions, patterns, and examples live in `.cursor/rules/`:

- `api-patterns.mdc` — REST conventions, error contracts, file uploads
- `backend-patterns.mdc` — Layers, auth, storage, RQ jobs
- `python-code-standards.mdc` — Python style, Pydantic v2, imports
- `react-frontend.mdc` — Components, styling, form patterns, accessibility
- `testing-patterns.mdc` — TDD workflow, what to test, contract testing
- `observability.mdc` — OpenTelemetry tracing, structured logging, metrics
