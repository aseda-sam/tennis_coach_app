# Security Policy

## Supported Versions
Currently, security fixes are applied to the `main` branch.

## Reporting a Vulnerability
- Preferred: open a private GitHub security advisory:
  https://github.com/aseda-sam/tennis_coach_app/security/advisories/new
- If private advisories are unavailable, open an issue with the `[SECURITY]` prefix
  and avoid posting sensitive details.

Please include:
- Affected component (backend/frontend)
- Steps to reproduce
- Expected vs actual behavior
- Any logs or stack traces (sanitized)

We aim to acknowledge reports within 72 hours and provide a remediation plan promptly.

## Security Practices
- Automated scanning with Bandit and Trivy (see GitHub Actions)
- Dependency updates via Dependabot
- Secrets are never committed; use environment variables
