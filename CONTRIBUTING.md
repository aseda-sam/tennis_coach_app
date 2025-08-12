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
- Backend: `pytest`
- Frontend: `npm test -- --watchAll=false`
- Add/Update tests for new features and bug fixes.

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
