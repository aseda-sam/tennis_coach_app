# CLAUDE.md

## Project overview

Tennis Coach App — a serve-analysis MVP. Users upload serve videos, the app runs pose estimation (MediaPipe), tags serve attempts, computes biomechanics metrics, and returns coaching recommendations.

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
    design-tokens.css # Design system tokens
data/                 # Local SQLite, videos, analysis cache
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
