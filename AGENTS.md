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

# Frontend format (run before committing any frontend file)
cd frontend && npm run format

# Backend dependency management (uses uv, not pip)
cd backend && uv sync --extra dev           # install/sync all deps
cd backend && uv add <package>              # add a package

# Backend type checking
cd backend && uv run pyright app/
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
    services/coaching/ # LLM coaching layer (see coaching/README.md)
    dependencies/     # FastAPI dependency injection helpers
    core/config.py    # Settings / env vars
    core/database.py  # DB session setup
    utils/            # Error handling, auth helpers, logging, metrics
  alembic/            # DB migrations
  docs/               # Operational backend docs (config, schema, jobs, deploy)
  ml_models/          # Pre-trained model weights (MediaPipe pose, YOLO ball detection)
  scripts/            # Utility and maintenance scripts (backfill, annotation, DB tools)
  tests/              # pytest tests
frontend/
  VISUAL_IDENTITY.md  # Aesthetic north star — read before any frontend work
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
  llm_logs/           # JSONL logs of LLM calls (eval dataset, gitignored)
  videos/
    raw/              # Uploaded user videos
    processed/        # Transcoded/processed videos
    demo/             # Curated demo videos (controlled subset visible to users)
  database/           # Local DB volume mount (empty until docker compose up)
docs/
  decisions/          # Architectural decision records (ADRs)
  diagrams/           # Mermaid architecture diagrams (system overview, auth, upload,
                      # analysis pipeline, serve feedback pipeline, data flow, DB relationships)
  assets/             # Screenshots and images for README/docs
```

## Architecture rules

- **Layers:** Routes handle HTTP + auth, Services handle logic, Models define schema. Don't leak HTTP concerns into services.
- **Auth:** `Depends(get_current_user)` on protected endpoints. AuthZ via `app.utils.authorization` helpers. Always scope queries by `user_id`.
- **Errors:** Use `APIError` / `log_and_raise_error` from `app.utils.error_handling`. Never leak internals in 500s.
- **Schemas:** Define all request/response schemas in `app/api/schemas/`. Never inline in route files. Follow `.agents/rules/api-patterns.mdc`.
- **Storage:** Always go through `app.services.storage_service.storage_service`. No raw `open()` in routes/services.
- **Background jobs:** Use RQ + `VideoJob` for anything > 5s. Jobs create their own DB sessions.
- **API versioning:** All endpoints under `/v0/` (alpha, breaking changes allowed).
- **DB changes:** If you modify models, update `backend/docs/database_schema.md` and create an Alembic migration.
- **Demo compatibility:** `AnalysisDashboard` is shared between authenticated users and the public demo page (unauthenticated). When adding a new API call to AnalysisDashboard or its child components/hooks, ensure the backend endpoint allows unauthenticated access for demo videos (use `get_optional_user` + `require_video_access_or_public_demo`). If the call is only needed for authenticated users, gate it with `isDemo` in the frontend hook. Test the demo page unauthenticated after any AnalysisDashboard change.

## Documentation discipline

- **No standalone docs for one-time work.** Migration runbooks, one-off SQL guides, and per-feature setup notes do not get their own `.md` files. Document inline: in the migration file's docstring, the commit message, or a code comment. Standalone docs only for things that need ongoing reference.
- **Update docs at the point of change.** If you change a model → update `database_schema.md`. Change a config var → update `config.md`. Change a script's flags → update `demo-videos.md`. Don't defer it.
- **Docs live close to the code they describe.** Backend operational docs in `backend/docs/`. Product/system-level docs in root `docs/`. Shared AI rules live in `.agents/rules/`.
- **Design tokens are a reference, not a rule.** `frontend/src/design-tokens.css` has all CSS custom properties. Behavioral constraints are in `.agents/rules/react-frontend.mdc`.

## Testing

- **Tests required before merge.** Write tests first (TDD) when the contract is known — bug fixes, API schema changes, service logic with clear inputs/outputs. Write tests after implementation when discovering a new data structure or UI shape. Either way, no code merges without tests.
- **Contract tests** for API endpoints (status codes + response shape). If you change a schema, update tests.
- **Unit tests** for service/business logic with mocked dependencies.
- **Mock externals** (Redis, storage, external APIs) unless explicitly integration testing.
- **Contract test fixtures must patch the lifespan.** Any `TestClient(app)` fixture with a mocked DB (`MagicMock`) must also `patch("app.main.create_tables_if_not_exists")` and `patch("app.main.start_rq_worker", return_value=None)` — otherwise the lifespan connects to real Postgres/Redis and the fixture lies about needing "no real DB."
- **Clean up `dependency_overrides` in `finally`.** Always wrap `yield client` / `overrides.clear()` in `try/finally` so overrides don't leak on setup failure.

## Code style

- **Python:** Type hints required. `ruff` for formatting/linting. `pyright` (basic mode) for type checking — runs on push. Pre-commit hook runs ruff automatically. **`uv`** for package management (not pip); use `uv sync` / `uv add` / `uv run`. Pydantic v2: use `ConfigDict(from_attributes=True)` for ORM schemas, `model_validate()` not `from_orm()`. Parameterize log calls (`logger.info("x=%s", x)`), never f-strings in log calls.
- **React:** Use React Query for data fetching. Design tokens for styling (see `frontend/src/design-tokens.css`). Avoid `any` in TypeScript.
- **General:** KISS, DRY, YAGNI. No speculative abstractions.

## Product design philosophy

These constraints apply when building any user-facing feature. They come from hard-won lessons about what this app actually is (and isn't).

- **Practice > analysis.** The goal is to get users serving on a court with valuable data and recommendations, not spending too much time in the app
- **Progressive disclosure.** Show one thing at a time. Don't front-load too much metrics, options, or complexity. Unlock detail as users demonstrate understanding.
- **App ≠ live coach.** The app gives asynchronous video feedback. It cannot see confusion, adjust in real time, or replace the feel of a human coach. Don't build features that pretend otherwise. Be honest about the medium's limits.
- **The app is a coach-prep tool.** Help users identify what to work on, give them language to use with a coach, encourage them to practice. It complements coaches; it doesn't replace them.

## Pre-commit pipeline

A pre-commit hook runs automatically on every `git commit`. If it fails, the commit is blocked. Here is what runs and what to do:

| Hook                      | Stage    | What it does                                   | Auto-fixes?                                |
| ------------------------- | -------- | ---------------------------------------------- | ------------------------------------------ |
| `trailing-whitespace`     | commit   | Removes trailing whitespace                    | Yes — re-stage if fixed                    |
| `end-of-file-fixer`       | commit   | Ensures files end with newline                 | Yes — re-stage if fixed                    |
| `check-yaml / check-json` | commit   | Validates YAML/JSON syntax                     | No — fix manually                          |
| `check-added-large-files` | commit   | Blocks files >1 MB                             | No — remove the file                       |
| `detect-private-key`      | commit   | Blocks committed secrets                       | No — remove the secret                     |
| `ruff` (Python)           | commit   | Lints Python, applies safe fixes               | Yes — auto-fixed                           |
| `ruff-format` (Python)    | commit   | Formats Python                                 | Yes — auto-fixed                           |
| `frontend-eslint`         | commit   | ESLint on `.ts/.tsx` files                     | No — run `cd frontend && npm run lint:fix` |
| `frontend-prettier`       | commit   | Checks formatting of `.ts/.tsx/.css`           | No — run `cd frontend && npm run format`   |
| `backend-pytest`          | **push** | Runs backend test suite                        | No — fix failing tests                     |
| `backend-pyright`         | **push** | Runs pyright type checker on backend           | No — fix type errors                       |
| `frontend-typecheck`      | **push** | TypeScript `tsc --noEmit`                      | No — fix type errors                       |
| `mermaid-validate`        | **push** | Validates Mermaid diagrams in `docs/diagrams/` | No — fix broken diagrams                   |

**If a commit fails:** Read the hook name in the output to know what failed. The most common cause is `frontend-prettier` — fix by running `cd frontend && npm run format`, then re-staging and committing.

**Before committing any Python file, ruff runs automatically** and fixes what it can. If ruff modifies files, re-stage them and commit again.

## Commits

- Do not add `Co-Authored-By` lines to commit messages.
- Do not implement tracked file edits on `main`. Create/switch to a feature branch before editing tracked files. Exploratory read-only work on `main` is allowed.

## Local-only instructions

- `AGENTS.local.md` is reserved for machine-local or sensitive instructions and is gitignored.
- If `AGENTS.local.md` exists, read it after this file and treat it as local overrides/additions.

## Command intents

- Canonical command workflows live in `.agents/commands/`.
- Map natural-language command phrases (for example, "ship it") to the matching file in `.agents/commands/`.
- The `ship-pr` intent means: commit, push, PR, checks, merge.
- Create new shared command intents under `.agents/commands/` first, then add tool-specific local adapters only if needed.

## Detailed rules

**Frontend design:** Before any frontend work, read `frontend/VISUAL_IDENTITY.md` — it defines the aesthetic direction, typography system (DM Sans + DM Mono), color philosophy, layout grammar, and key view descriptions.

Shared coding conventions live in `.agents/rules/` (read the relevant file for your domain):

- `.agents/rules/api-patterns.mdc` — REST conventions, error contracts, file uploads
- `.agents/rules/backend-patterns.mdc` — Layers, auth, storage, RQ jobs
- `.agents/rules/react-frontend.mdc` — Components, styling, form patterns, accessibility
- `.agents/rules/frontend-design.mdc` — Visual design patterns, component aesthetics
- `.agents/rules/react-routing.mdc` — React Router conventions, route structure, page patterns
- `.agents/rules/frontend-api-patterns.mdc` — Frontend API client conventions
- `.agents/rules/testing-patterns.mdc` — When to test first vs after, what to test, contract testing
- `.agents/rules/frontend-testing-patterns.mdc` — Frontend test patterns
- `.agents/rules/anthropic-sdk-patterns.mdc` — Anthropic SDK tool use, agentic loops, model selection

Tool-specific local rules may exist under ignored folders. Shared, repo-level guidance should live in `AGENTS.md`, `.agents/rules/`, and `.agents/skills/`.

Before implementing code changes (not during planning/chat-only turns), load only the relevant files from `.agents/rules/` for the current domain.

Create new shared skills under `.agents/skills/` first, then add tool-specific local adapters only if needed.
