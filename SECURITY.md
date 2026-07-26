# Security policy

## Supported version

Security fixes are applied to the latest commit on `main`.

## Reporting a vulnerability

Please report vulnerabilities privately through GitHub Security Advisories for
this repository. If that is unavailable, contact
`majjigaparthu2004@gmail.com` with a description, reproduction steps, impact,
and any suggested mitigation. Do not include credentials, private documents,
or other sensitive data in a public issue.

## Deployment threat model

- The application uses Chroma through its in-process `PersistentClient`. It
  does not start or expose Chroma's separate HTTP API server. This distinction
  is important for `PYSEC-2026-311` / `CVE-2026-45829`, which affects Chroma's
  remotely accessible Python server. The CI audit documents this
  architecture-specific exclusion while continuing to fail on other findings.
- The public demo is an unauthenticated portfolio environment with bounded file
  uploads. Do not upload confidential or regulated documents. A private or
  multi-user deployment should add authentication and authorization in front of
  upload, ingest, and delete operations.
- Server-path ingestion is restricted to `GROUNDED_OPS_HOME`; uploaded
  filenames are sanitized and file count and size limits are enforced.
- Secrets belong in deployment environment variables. `.env`, runtime data,
  uploads, generated indexes, and local deployment metadata are ignored by Git.

## Operator checklist

1. Restrict `CORS_ALLOWED_ORIGINS` to the deployed frontend origins.
2. Keep the FastAPI application behind an HTTPS reverse proxy.
3. Do not expose a Chroma HTTP server to the public internet.
4. Use a persistent volume with appropriate access controls when uploaded
   documents must survive restarts.
5. Rotate provider keys immediately if a secret is suspected to be exposed.
6. Run `npm audit` and `pip-audit` during dependency review; evaluate findings
   against this architecture rather than suppressing them without analysis.
