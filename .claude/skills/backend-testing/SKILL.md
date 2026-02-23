# Backend Testing

Project-specific testing skill for the Tennis Coach App backend.

## Running tests

```bash
# Full suite (inside Docker — preferred)
docker compose exec backend pytest

# Quick summary
docker compose exec backend pytest -q

# Single file
docker compose exec backend pytest tests/test_video_api.py

# Single class or method
docker compose exec backend pytest tests/test_video_api.py::TestVideoUpload::test_upload_success

# Only last-failed
docker compose exec backend pytest --lf

# Run with output visible
docker compose exec backend pytest -s
```

Tests run against a local PostgreSQL (`tennis_coach_test` DB) inside Docker. The `conftest.py` auto-creates this DB if missing.

## Test directory layout

```
backend/tests/
  conftest.py                     # Root fixtures (client, db_session, test_user_id, ...)
  biomechanics_fixtures.py        # Shared pose/sequence builders
  api/                            # Contract tests (HTTP layer)
  services/                       # Unit tests (service layer)
    biomechanics/
      conftest.py                 # Biomechanics-specific fixtures
    ball_detection/
  test_*.py                       # Top-level contract, unit, integration tests
```

**Naming:** Files: `test_<feature>.py`. Classes: `TestFeatureBehavior`. Methods: `test_<scenario>`.

## Fixtures (from `conftest.py`)

| Fixture | What it provides | Use for |
|---------|-----------------|---------|
| `client` | `TestClient` with DB + mock auth | Contract/API tests |
| `db_session` | Isolated DB session (rollback per test) | Service tests needing DB |
| `test_user_id` | `"00000000-0000-0000-0000-000000000000"` | Matches mock auth user |
| `temp_upload_dir` | Temp `Path`, auto-cleaned | File operation tests |
| `sample_video_content` | Minimal MP4-like bytes | Upload endpoint tests |
| `test_video_path` | Path to real test video (skips if missing) | Processing tests |
| `ensure_local_profile` | Forces `PROFILE=local` (autouse) | All tests automatically |

## Shared helpers (`biomechanics_fixtures.py`)

Import directly — these are not pytest fixtures:

```python
from tests.biomechanics_fixtures import _make_pose, _make_serve_sequence
```

- `_make_pose(left_wrist_y=..., right_wrist_y=..., knee_y=..., ...)` — single pose dict
- `_make_serve_sequence(num_frames=60, fps=30.0)` — full serve pose sequence with realistic phase progression

## Mock patch conventions

**Patch where imported, not where defined:**

```python
# YES — patch at the import site
@patch("app.services.video_service.storage_service")

# NO — don't patch at the definition site
@patch("app.services.storage_service.storage_service")
```

**Common patches:**
- Storage: `app.services.<module>.storage_service`
- Settings: `patch.object(settings, "FIELD", value)` — not env vars
- Redis/RQ: `patch("app.services.<module>.Queue")` or the specific enqueue call
- Auth: already handled by `client` fixture (overrides `get_current_user`)

## DB vs pure unit tests

- **Needs DB:** Tests using `client` or `db_session` — requires Postgres running in Docker
- **Pure unit:** Biomechanics tests, utility tests — no DB, can run without Postgres

## Pre-commit / pre-push hooks

- `pytest` runs at **push**, not commit — you can commit with failing tests but can't push
- Ruff (lint + format) runs at commit and auto-fixes Python files
