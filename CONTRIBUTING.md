# Contributing Guidelines

Thank you for considering contributing to Tennis Coach App!

## Getting Started
- Clone the repo: `git clone https://github.com/aseda-sam/tennis_coach_app.git`
- Backend setup: see `backend/README.md`
- Frontend setup: see `frontend/README.md`

## Development Workflow
- Create a branch from `main`:
  - Features: `feature/<short-description>`
  - Fixes: `fix/<short-description>`
- Follow Conventional Commits: `feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `chore:`
- Keep commits small and focused.

## Code Style
- Python: Ruff formatting and linting
  - `ruff format .` and `ruff check .`
- TypeScript/JS: ESLint + Prettier
  - `npm run lint` and `npm run format`
- Use type hints in Python and TypeScript types in the frontend.

## Tests

### Running Tests
- Backend: `pytest`
- Frontend: `npm test -- --watchAll=false`

### Test-Driven Development (TDD) Checklist

**For new features:**
- [ ] Write failing test first (Red)
- [ ] Implement minimum code to pass (Green)
- [ ] Refactor if needed (Refactor)
- [ ] Test covers contract (status codes, response shapes), not implementation details

**For bug fixes:**
- [ ] Write failing test that reproduces the bug
- [ ] Fix the bug (test should pass)
- [ ] Verify test covers the edge case

**For API endpoints:**
- [ ] Contract test: status codes, response models, error cases
- [ ] Integration test: full workflow if endpoint is part of a flow
- [ ] Use `PROFILE=local` in fixtures, not internal config fields

**For refactors:**
- [ ] Keep tests unchanged if behavior is unchanged
- [ ] Update tests only if contract changes (document why)

See `.cursor/rules/testing-patterns.mdc` for detailed TDD guidance.

## Pull Requests
- Ensure CI passes (backend, frontend, security scans)
- Fill in the PR template
- Link related issues (e.g., `Closes #123`)
- Provide screenshots or videos for UI changes where helpful

## Security
- Do not commit secrets. Use environment variables.
- Report vulnerabilities per `.github/SECURITY.md`.

## License
By contributing, you agree that your contributions will be licensed under the MIT License.
