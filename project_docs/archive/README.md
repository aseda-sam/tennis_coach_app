# Archived Documentation

This directory contains documentation files that have been archived due to being outdated, superseded, or no longer relevant to the current codebase.

## Archived Files

### `api_documentation.md`
**Reason**: Superseded by interactive Swagger documentation at `/docs`
**Status**: Removed - API documentation is now available at http://localhost:8000/docs

### `database_schema.md`
**Reason**: Describes database schema that doesn't match current Alembic models
**Status**: Archived - Contains future schema designs that aren't implemented
**Note**: Current database schema is defined in `backend/alembic/versions/` and `backend/app/models/`

### `deep_analysis_branch_summary.md`
**Reason**: Historical branch summary that was reverted
**Status**: Archived - Contains useful implementation details for future reference
**Note**: This was from a feature branch that was reverted due to frontend instability

### `react_frontend_guide.md`
**Reason**: Tutorial content merged into `frontend/README.md`
**Status**: Archived - Development patterns moved to frontend documentation
**Note**: Contains useful React development patterns that are now in the frontend README

### `testing_guide.md`
**Reason**: Testing patterns moved to respective READMEs
**Status**: Archived - Testing guidance is now in `backend/README.md` and `frontend/README.md`
**Note**: Contains comprehensive testing patterns that are now integrated into component documentation

## Current Documentation Structure

- **`backend/README.md`** - Backend setup, API, testing, deployment
- **`frontend/README.md`** - Frontend components, testing, build process
- **`project_docs/deployment_guide.md`** - Production deployment instructions
- **`project_docs/project_plan.md`** - Development roadmap
- **`project_docs/pose_estimation_comparison.md`** - Technology decision record
- **`project_docs/cursor_rules_migration.md`** - Documentation migration guide

## Migration Notes

The documentation has been reorganized to:
1. **Reduce duplication** - API docs now point to Swagger UI
2. **Improve maintainability** - Component-specific docs in respective READMEs
3. **Preserve history** - Archived files contain useful implementation details
4. **Focus on current state** - Remove outdated schema and API information

## Accessing Archived Content

If you need to reference archived documentation:
1. Check the current documentation first
2. Look in the appropriate README for component-specific information
3. Use archived files for historical context or implementation details
4. Consider updating archived content if implementing similar features
