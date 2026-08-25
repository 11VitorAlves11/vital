# Vital

Self-hosted tracker for **lab results, body composition and physical progress**.

Vital turns a pile of PDF lab reports and bathroom-scale readings into a single timeline
you actually read: trends with the reference band drawn behind them, clinical flags, and
an overlay of the interventions (supplements, diet, training) you were running at the time.

Body-composition classifications come from **clinical standards** (WHO, ACE/ACSM, IDF) —
never from the proprietary ratings your scale prints.

> **Status:** early development. v1 (MVP) covers authentication, manual lab reports,
> body-composition logging with clinical flags, interventions and the trend dashboard.

## Stack

FastAPI · SQLAlchemy 2.0 · Alembic · PostgreSQL 16 · React 18 · Vite · TypeScript ·
Tailwind CSS v4 · Radix UI · Recharts · LiteLLM · PyMuPDF · OIDC (any provider) or local auth.

## Quick start (development)

```bash
cp .env.example .env
docker compose -f docker-compose.dev.yml up --build
```

Web: <http://localhost:5173> · API: <http://localhost:8000/api> · Docs: <http://localhost:8000/docs>

The API migrates and seeds itself on start-up, so the first run comes up with the full
clinical catalogue (31 biomarkers, 18 body-composition metrics) already loaded.

## Authentication

`AUTH_MODE` decides how people sign in, and the login screen follows it:

| Mode | What it does |
|---|---|
| `local` | Email and password, registration open. No identity provider needed — the default in the dev stack |
| `oidc` | Authorization-code flow against any OIDC provider (Authentik, Keycloak, Pocket ID, Google). Set `OIDC_ISSUER`, `OIDC_CLIENT_ID`, `OIDC_CLIENT_SECRET` and register `https://your-host/auth/callback` as the redirect URI |

Either way the session is a signed, httpOnly, `SameSite=Lax` cookie: no token is readable
from JavaScript and there is no session store to run. Set `SECRET_KEY` in production —
the API refuses to start without one.

Set your sex in the profile: reference ranges and clinical bands are sex-specific, and
Vital declines to classify anything rather than guess which set applies.

### Without Docker

```bash
# backend
cd backend
python -m venv .venv && .venv/bin/pip install -e '.[dev]'
.venv/bin/uvicorn app.main:app --reload

# frontend
cd frontend && npm install && npm run dev
```

## Repository layout

| Path | Contents |
|---|---|
| `backend/` | FastAPI application, Alembic migrations, pytest suite |
| `frontend/` | React + Vite app, design tokens, vitest suite |
| `seed/` | Clinical catalogues — biomarkers and body-composition metrics (JSON) |
| `scripts/` | Repository tooling (seed validation) |

## Tests and linting

```bash
cd backend  && .venv/bin/ruff check . && .venv/bin/mypy app && .venv/bin/pytest
cd frontend && npm run lint && npm run lint:css && npm test && npm run build
python scripts/validate_seed.py
```

## Documentation

- [`seed/README.md`](seed/README.md) — catalogue conventions and standard provenance (PT-PT)
- [`CONTRIBUTING.md`](CONTRIBUTING.md) — dev setup, conventions, how to run the tests

## Not a medical device

Vital records and visualises data you already have. It does not diagnose, and it does not
replace clinical judgement. Bioimpedance figures are estimates with a wide margin of error —
read the trend, not the isolated value.

## Licence

[AGPL-3.0-or-later](LICENSE).
