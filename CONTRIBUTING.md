# Contributing Guidelines

Thank you for considering contributing to S²Serve!

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
- Frontend: `npm run test:ci`

### Testing Checklist

**Bug fixes (TDD required):**
- [ ] Write failing test that reproduces the bug
- [ ] Fix the bug (test should pass)
- [ ] Verify test covers the edge case

**API schema changes (TDD required):**
- [ ] Write contract test asserting the new response shape
- [ ] Implement the schema/route change
- [ ] Use `PROFILE=local` in fixtures, not internal config fields

**New features (tests required, TDD when contract is known):**
- [ ] If the output shape is known upfront → write test first, then implement
- [ ] If discovering the structure → implement first, then write tests that lock it down
- [ ] Tests must exist before merge either way
- [ ] Test covers contract (status codes, response shapes), not implementation details

**For refactors:**
- [ ] Keep tests unchanged if behavior is unchanged
- [ ] Update tests only if contract changes (document why)

See `.agents/rules/testing-patterns.mdc` for detailed guidance.

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
