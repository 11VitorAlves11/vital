# Vital

Self-hosted tracker for **lab results, body composition and physical progress**.

Vital turns a pile of PDF lab reports and bathroom-scale readings into a single timeline
you actually read: trends with the reference band drawn behind them, clinical flags, and
an overlay of the interventions (supplements, diet, training) you were running at the time.

Body-composition classifications come from **clinical standards** (WHO, IDF, GLIM/ESPEN) —
never from the proprietary ratings your scale prints. A scale that is not clinical, like the
ACE/ACSM body-fat categories, names the reading and stops there: sixteen of the twenty body
metrics carry no verdict at all, and each says why in its own words.

> **Status:** early development. v1 (MVP) covers authentication, manual lab reports,
> body-composition logging with clinical flags, interventions and the trend dashboard.
> Reading a lab PDF with a model is built and off until you configure one.

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
clinical catalogue (31 biomarkers, 20 body-composition metrics) already loaded.

## Authentication

`AUTH_MODE` decides how people sign in, and the login screen follows it:

| Mode | What it does |
|---|---|
| `local` | Email and password, registration open. No identity provider needed — the default in the dev stack |
| `oidc` | Authorization-code flow **with PKCE** against any OIDC provider (Authentik, Keycloak, Pocket ID, Google), discovered from the issuer's `.well-known/openid-configuration`. Set `OIDC_ISSUER`, `OIDC_CLIENT_ID`, `OIDC_CLIENT_SECRET` and register `https://your-host/auth/callback` as the redirect URI. `OIDC_PKCE=false` for a provider that refuses the extra parameters |

Either way the session is a signed, httpOnly, `SameSite=Lax` cookie: no token is readable
from JavaScript and there is no session store to run. Set `SECRET_KEY` in production —
the API refuses to start without one.

Set your sex in the profile: reference ranges and clinical bands are sex-specific, and
Vital declines to classify anything rather than guess which set applies.

## Reading a PDF with a model

Point Vital at any model LiteLLM supports and **Import lab report** appears next to the manual
entry form. Leave `LLM_MODEL` empty and the button does not: no model configured means no
extraction, not a broken one.

```bash
# In .env. A model you host yourself: no key, and nothing leaves the machine.
LLM_MODEL=ollama/llama3.2-vision
LLM_BASE_URL=http://10.0.0.10:11434

# Or a hosted provider — anything LiteLLM accepts, written "provider/model",
# with that provider's key. Vital hardcodes no vendor and prefers none.
# LLM_MODEL=<provider>/<model>
# LLM_API_KEY=...
```

What happens to the file:

1. PDFs, JPEGs and PNGs are accepted. Before anything reaches the model, Vital removes
   labelled identity data locally; photographed pages are re-encoded without metadata,
   OCR-located identity and machine-readable codes, with faces blurred. Text PDFs are
   reduced to sanitised text; scans go as sanitised 144 dpi page images.
2. The model is asked for JSON and nothing else. The answer is validated against a schema,
   and each name it returns is matched against the catalogue by name and PT-PT alias.
3. The result is a **preview**, not a report. Nothing reaches your history until you have
   looked at every row and confirmed it — two-column layouts are read across the columns
   often enough that this gate is not optional, and a wrong value entered as fact is worse
   than no value. The original upload is kept locally, so the reading can always be checked.

`EXTRACTION_MAX_PAGES` and `UPLOAD_MAX_BYTES` bound what a single upload can cost, in
tokens and in memory. A cloud model means your blood work is sent to that provider; a
self-hosted one is the reason the setting exists.

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
