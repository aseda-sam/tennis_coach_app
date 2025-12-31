# PR Review Assessment

## Critical (Must Fix)

### 1. Exception Handling

**File**: `backend/app/utils/supabase_auth.py:50`

- **Issue**: `except Exception` masks security errors
- **Fix**: Catch specific `AuthError`, `APIError`; log failures; re-raise unexpected

### 2. Rate Limiting

**File**: Auth endpoints

- **Issue**: No rate limiting = brute force risk
- **Fix**: Add `slowapi` middleware, limit to 5/min per IP

## High Priority (Should Fix)

### 3. Config Mutation

**File**: `backend/app/core/config.py:142-143`

- **Issue**: Mutating `settings.STORAGE_TYPE` after creation
- **Fix**: Use computed `@property` instead

### 4. Type Hints

**File**: `backend/app/utils/authorization.py:12`

- **Issue**: `user: dict` instead of typed model
- **Fix**: Create `TypedDict` or Pydantic `User` model

## Not Applicable

- **Foreign Keys**: Can't FK to `auth.users` (Supabase-managed). RLS provides security. Use app-level cleanup (see `user_data_deletion_gdpr.md`).
