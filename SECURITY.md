# Security Policy

## Supported versions

| Version | Supported |
|---------|-----------|
| 0.1.x   | Yes       |

## Reporting a vulnerability

If you discover a security vulnerability, please report it responsibly.

**Do not open a public issue.**

Instead, send an email to the maintainer with:

1. Description of the vulnerability
2. Steps to reproduce
3. Potential impact assessment
4. Suggested fix (if any)

You should receive an acknowledgement within 48 hours. We will work with you to
understand the issue and coordinate a fix before any public disclosure.

## Security measures in this project

- **detect-secrets** pre-commit hook prevents accidental credential commits
- **bandit** security rules (via ruff S category) check for common Python vulnerabilities
- **Frozen dataclasses** prevent mutation of governance evidence after construction
- **Hash-verified provenance chains** detect tampering in transformation history
- **Dependabot** monitors dependencies for known vulnerabilities
