# Deprecation & Legacy Cleanup Checklist

This document tracks items that need to be deprecated, updated, or removed as part of the Fly.io consolidation migration.

## GitHub Actions Workflows

### ✅ `deploy-flyio-worker.yml`
- **Status**: Keep (already correct)
- **Action**: No changes needed

### ❌ `deploy-frontend.yml`
- **Issue**: Hardcoded Render API URL (`https://tennis-coach-backend.onrender.com/v0`)
- **Location**: Line 43
- **Action Required**:
  - Replace with GitHub secret: `REACT_APP_API_URL`
  - Or use Fly.io API hostname: `https://tennis-coach-api.fly.dev/v0`
  - Update to use environment variable from secrets

### ⚠️ New: `deploy-flyio-api.yml`
- **Status**: Needs to be created
- **Action Required**:
  - Create new workflow similar to `deploy-flyio-worker.yml`
  - Deploy API app: `tennis-coach-api`
  - Use `fly.api.toml` config file
  - Trigger on: `backend/**`, `Dockerfile`, `fly.api.toml`

---

## Backend Code

### ❌ `ENVIRONMENT=production` (Legacy Variable)
- **Location**: `backend/app/main.py` (lines 156, 161, 169)
- **Issue**: Legacy check that should be removed
- **Current Behavior**: API service starts worker if `ENVIRONMENT=production` is set
- **Action Required**:
  - Remove `ENVIRONMENT` checks from `main.py`
  - Rely solely on `SERVICE_TYPE` and `PROFILE` variables
  - Update comments to remove Render references
  - Remove from all documentation

### ❌ Render References in Comments
- **Location**: `backend/app/main.py` (lines 149, 160, 169)
- **Issue**: Comments mention "Render API" and "Render API env vars"
- **Action Required**:
  - Update comments to be platform-agnostic
  - Change "Render API" → "API service"
  - Remove specific platform references

### ⚠️ Worker Startup Logic
- **Location**: `backend/app/main.py` (lines 148-175)
- **Status**: Needs simplification
- **Action Required**:
  - Simplify logic to only check `SERVICE_TYPE`
  - Remove `ENVIRONMENT` check entirely
  - Update logging messages to be platform-agnostic

---

## Frontend Configuration

### ❌ Hardcoded API URL in GitHub Actions
- **Location**: `.github/workflows/deploy-frontend.yml` (line 43)
- **Issue**: Hardcoded Render URL
- **Action Required**:
  - Use GitHub secret: `${{ secrets.REACT_APP_API_URL }}`
  - Or set to Fly.io URL: `https://tennis-coach-api.fly.dev/v0`

### ✅ Frontend Code (`api.ts`)
- **Status**: Already correct
- **Note**: Uses `process.env.REACT_APP_API_URL` with fallback
- **Action**: No changes needed

---

## Documentation

### ❌ `backend/docs/flyio-deployment.md`
- **Status**: Outdated, should be consolidated
- **Issue**: 
  - References old region (`iad`)
  - Separate from main deployment guide
  - Some info duplicated in `backend-deployment.md`
- **Action Required**:
  - Delete after confirming all useful info is in `backend-deployment.md`
  - Or mark as deprecated and redirect to `backend-deployment.md`

### ❌ `.cursor/plans/region_migration_uk.plan.md`
- **Status**: Outdated, references Render
- **Issue**: 
  - Contains Render-specific migration steps
  - Uses deprecated `fly regions set` command
  - Superseded by `backend-deployment.md`
- **Action Required**:
  - Delete (migration info now in `backend-deployment.md`)

### ⚠️ Other Documentation Files
- **Files to Review**:
  - `backend/docs/background-tasks-rq.md` - Check for Render references
  - `backend/docs/upstash-redis-setup.md` - Check for Render references
  - `backend/README.md` - Check for `ENVIRONMENT` variable docs
  - `backend/docs/api.md` - Check for Render-specific notes

---

## Environment Variables

### ❌ `ENVIRONMENT` Variable
- **Status**: Deprecated, should be removed
- **Replacement**: Use `PROFILE` and `SERVICE_TYPE` instead
- **Action Required**:
  - Remove from all documentation
  - Remove from example `.env` files
  - Remove from deployment guides
  - Remove from code checks

### ✅ `PROFILE` Variable
- **Status**: Current standard
- **Values**: `local`, `production`
- **Action**: Keep and use everywhere

### ✅ `SERVICE_TYPE` Variable
- **Status**: Current standard
- **Values**: `api`, `worker`
- **Action**: Keep and use everywhere

---

## Deployment Configuration

### ✅ `fly.toml` (Worker)
- **Status**: Correct (already updated to `lhr`)
- **Action**: No changes needed

### ✅ `fly.api.toml` (API)
- **Status**: Correct (already configured for London)
- **Action**: No changes needed

---

## Priority Order

### High Priority (Do Before API Deployment)
1. ✅ Update `deploy-frontend.yml` to use Fly.io API URL
2. ✅ Create `deploy-flyio-api.yml` workflow
3. ✅ Remove `ENVIRONMENT` checks from `main.py`
4. ✅ Update Render references in `main.py` comments

### Medium Priority (Do After API Deployment)
5. ⚠️ Delete `flyio-deployment.md` (after verifying migration complete)
6. ⚠️ Delete `region_migration_uk.plan.md`
7. ⚠️ Review and update other documentation files

### Low Priority (Cleanup)
8. ⚠️ Remove `ENVIRONMENT` from all documentation
9. ⚠️ Update any remaining Render references in docs

---

## Verification Checklist

After completing changes:

- [ ] Frontend builds with Fly.io API URL
- [ ] API deploys via GitHub Actions
- [ ] Worker deploys via GitHub Actions
- [ ] No `ENVIRONMENT` variable used anywhere
- [ ] No Render references in code
- [ ] No Render references in active documentation
- [ ] All deployment docs point to Fly.io
- [ ] `main.py` worker logic simplified

---

## Notes

- Keep old Render service running until migration is verified
- Update frontend API URL in GitHub secrets before deploying
- Test all workflows after changes
- Consider keeping deprecated docs in archive folder if needed for reference
