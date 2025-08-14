# Security Policy

## Supported Versions
Currently, security fixes are applied to the `main` branch.

## Reporting a Vulnerability
- Email: security@tennis-coach-app.local (or open a private GitHub security advisory)
- Alternatively, create an issue with the `[SECURITY]` prefix (avoid sensitive details)

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
