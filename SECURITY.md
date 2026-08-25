# Security policy

Vital stores health data: lab results, body composition, and progress photos.
Security reports are taken seriously and handled quietly.

## Reporting a vulnerability

**Do not open a public issue.** Use GitHub's
[private vulnerability reporting](https://docs.github.com/code-security/security-advisories/guidance-on-reporting-and-writing/privately-reporting-a-security-vulnerability)
on this repository ("Security" → "Report a vulnerability").

Please include: affected version or commit, reproduction steps, and impact.

Expect an acknowledgement within 7 days and an assessment within 30. Fixes are released
alongside a GitHub Security Advisory crediting the reporter, unless anonymity is preferred.

## Scope

In scope: authentication and session handling, cross-user data access, file upload and
download paths, the PDF extraction pipeline, and dependency vulnerabilities that are
reachable from the application.

Out of scope: issues that require an already-compromised host, and misconfiguration of a
self-hosted deployment (reverse proxy, TLS, database exposure) — though documentation
fixes for those are very welcome.

## Deploying safely

- Serve Vital over HTTPS only; sessions are cookie-based.
- Never expose PostgreSQL or the API container directly to the internet.
- Progress photos and PDFs are served through authenticated endpoints, never as static
  files. Do not add a static route to `STORAGE_PATH`.
- Keep backups (`STORAGE_PATH` and the database dump) encrypted.
