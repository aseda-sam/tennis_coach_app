# Backend Tests

## Test Structure

Tests follow TDD principles: **tests define contracts** (behavior), not implementation details.

### Test Layers

**Contract Tests (API Level)**
- Location: `test_*_api.py` files
- Purpose: Test HTTP endpoints, request/response shapes, status codes
- Examples: `test_video_api.py`, `test_player_api.py`, `test_pose_detection.py`

**Integration Tests (Workflow Level)**
- Location: `test_*_e2e.py`, `test_*_integration.py`
- Purpose: Test full workflows, database interactions
- Examples: `test_serve_analysis_e2e.py`, `test_integration.py`

**Unit Tests (Service Level)**
- Location: `test_*_service.py`, `test_*.py` (service-specific)
- Purpose: Test business logic, calculations, pure functions
- Examples: `test_posture_analysis.py`, `test_storage_service.py`

### Serve MVP Test Map

The serve analysis workflow is tested at multiple levels:

1. **POST /v0/videos/upload**
   - Contract: `test_video_api.py::TestVideoAPI::test_upload_video_success`
   - Integration: `test_serve_analysis_e2e.py::test_complete_serve_analysis_flow`

2. **POST /v0/serve-attempts/**
   - Contract: Covered in e2e test
   - Integration: `test_serve_analysis_e2e.py::test_complete_serve_analysis_flow`

3. **POST /v0/analysis/videos/{id}**
   - Contract: `test_pose_detection.py::TestPoseDetectionAPI`
   - Integration: `test_serve_analysis_e2e.py::test_complete_serve_analysis_flow`

4. **POST /v0/videos/{id}/analyze-serves**
   - Contract: Covered in e2e test
   - Integration: `test_serve_analysis_e2e.py::test_complete_serve_analysis_flow`

5. **GET /v0/serve-attempts/me**
   - Contract: Covered in e2e test (verified via database query due to routing)

### Running Tests

```bash
# All tests
pytest

# With coverage
pytest --cov=app --cov-report=html

# Specific test file
pytest tests/test_serve_analysis_e2e.py

# Specific test
pytest tests/test_serve_analysis_e2e.py::TestServeAnalysisE2E::test_complete_serve_analysis_flow
```

### Test Configuration

- **Database**: SQLite test database (isolated per test)
- **Profile**: `PROFILE=local` (via `ensure_local_profile` fixture)
- **Auth**: Mock user (test_user_id fixture)
- **Storage**: Local filesystem (via PROFILE=local)

### TDD Principles

1. **Write tests first** for new features
2. **Test contracts** (status codes, response shapes), not internals
3. **Use PROFILE-based config** in tests, not internal fields
4. **Keep tests stable** when refactoring (only change if contract changes)

See `.cursor/rules/testing-patterns.mdc` for detailed TDD guidance.
