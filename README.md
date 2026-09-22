<p align="center">
  <img src="frontend/public/favicon.svg" width="140" height="140" alt="Vital logo: two blue strokes forming Vi" />
</p>

<h1 align="center">Vital</h1>
<p align="center"><strong>Your health data, with the history behind it.</strong></p>
<p align="center">
  Lab results, body composition and physical progress in one place.<br />
  On your computer, on your phone, and on your own server.
</p>

<p align="center">
  <a href="https://github.com/11VitorAlves11/vital/releases"><img src="https://img.shields.io/github/v/release/11VitorAlves11/vital?style=flat-square&color=155BC4&label=release" alt="Latest release" /></a>
  <a href="https://github.com/11VitorAlves11/vital/actions/workflows/ci.yml"><img src="https://github.com/11VitorAlves11/vital/actions/workflows/ci.yml/badge.svg" alt="CI status" /></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-AGPL--3.0-155BC4?style=flat-square" alt="AGPL-3.0-or-later licence" /></a>
  <img src="https://img.shields.io/badge/web-PWA-155BC4?style=flat-square" alt="Website and installable PWA" />
</p>

<p align="center">
  <a href="#the-interface">See the interface</a> ·
  <a href="#features">Features</a> ·
  <a href="#try-it-locally">Install</a> ·
  <a href="#optional-ai-import">AI import</a> ·
  <a href="CONTRIBUTING.md">Contribute</a>
</p>

<p align="center">
  <a href=".github/images/desktop-dashboard.png"><img src=".github/images/desktop-dashboard.png" width="1100" alt="Vital dashboard showing changes since the last collection, out-of-range results and biomarker categories" /></a>
</p>

## What is Vital?

Vital is an open source, self-hosted application for following **lab results, body composition
and physical progress over time**. Bring your reports and measurements together, see what
changed, and read the history alongside the supplements, diet or training you recorded.

The application works on desktop and mobile, with English and European Portuguese, light
and dark themes, and an installable PWA in production builds. Your database, original
reports and progress photos stay on the infrastructure you run. AI-assisted import is
optional; manual entry works without a model or an API key.

**Project status:** early development. The application already includes lab reports,
comparisons, body measurements, progress photos, interventions and a unified timeline.
See the [releases](https://github.com/11VitorAlves11/vital/releases) for changes.

## The interface

These are real browser screenshots using the local **synthetic demonstration account**.
The interface is in English; clinical catalogue names and some notes remain in Portuguese.
Click an image to view it full size.

### On a phone

Check recent changes, browse your timeline and record body measurements with navigation
always within reach.

<table>
  <tr>
    <th align="center">Recent changes</th>
    <th align="center">Your timeline</th>
    <th align="center">Body composition</th>
  </tr>
  <tr>
    <td width="33%" align="center"><a href=".github/images/mobile-dashboard.png"><img src=".github/images/mobile-dashboard.png" width="280" alt="Vital mobile dashboard with the latest lab result changes" /></a></td>
    <td width="33%" align="center"><a href=".github/images/mobile-timeline.png"><img src=".github/images/mobile-timeline.png" width="280" alt="Vital mobile timeline with dated health records and event filters" /></a></td>
    <td width="33%" align="center"><a href=".github/images/mobile-body.png"><img src=".github/images/mobile-body.png" width="280" alt="Vital mobile body composition screen with measurements and a new weigh-in action" /></a></td>
  </tr>
</table>

*Captured in Chromium with mobile emulation at 390 × 844. These are browser captures,
not screenshots of an installed PWA.*

### On a computer

Follow an individual biomarker through time, with its reference range and the events
recorded during the same period.

<p align="center">
  <a href=".github/images/desktop-trend.png"><img src=".github/images/desktop-trend.png" width="1100" alt="Vital biomarker detail with a trend chart, reference range and recorded interventions" /></a>
</p>

<details>
  <summary><strong>See the dark theme</strong></summary>
  <p align="center"><a href=".github/images/desktop-dark.png"><img src=".github/images/desktop-dark.png" width="1100" alt="Vital dashboard in the dark theme" /></a></p>
</details>

## Features

| | What you can do |
|---|---|
| **Lab results** | Record collections, laboratories, values and reference intervals; compare collections side by side. |
| **Trends and changes** | See out-of-range results, changes since the previous collection and individual biomarker histories. |
| **Body composition** | Log weight, measurements and bioimpedance readings, with derived indices and reference bands where supported. |
| **Timeline and interventions** | Keep lab reports, weigh-ins, photos, supplements, diet and training in chronological context; schedule repeat collections. |
| **Progress photos** | Keep a visual history and compare photos side by side. Uploads are re-encoded without EXIF metadata. |
| **Optional AI import** | Extract lab reports and body measurements from supported documents, then review the preview before saving. Choose your model through LiteLLM. |
| **Accounts** | Use email and password, or connect an OIDC identity provider with PKCE. |
| **Preferences** | Use English or European Portuguese and choose a light or dark theme. |

Body-composition flags use the standards documented in the [clinical catalogue](seed/README.md),
rather than a scale manufacturer's proprietary score. Metrics without a supported clinical
classification show their trend and explain the limitation. Set your sex, date of birth and
height in **Profile** so applicable references and derived measurements have the inputs they need.

## Try it locally

Needs Git, Docker and Docker Compose. From a terminal:

```bash
git clone https://github.com/11VitorAlves11/vital.git
cd vital
cp .env.example .env
```

For local sign-in and a populated demonstration account, set these two values in `.env`:

```dotenv
AUTH_MODE=local
SEED_DEMO_DATA=true
```

Then start the development environment:

```bash
docker compose -f docker-compose.dev.yml up --build
```

Open **[http://localhost:5173](http://localhost:5173)** and sign in with
**`demo@example.com` / `VitalDemo2026!`**, or create your own account.

The API applies migrations and loads the clinical catalogue automatically. The demo includes
lab results, body measurements, interventions and a scheduled repeat. Set `SEED_DEMO_DATA=false`
to stop creating or refreshing the demo account; this does not delete existing demo records.
Demo seeding is only allowed in development.

API: <http://localhost:8000/api> · Interactive documentation: <http://localhost:8000/docs>

### On your own server

The included Compose file is a **development environment**, with hot reload and exposed
service ports. A production deployment needs PostgreSQL, the API, the built frontend and
an HTTPS reverse proxy that forwards `/api` and `/auth` to the API.

Set `ENVIRONMENT=prod`, a strong `SECRET_KEY`, `SEED_DEMO_DATA=false`, your public
`FRONTEND_URL` and appropriate `CORS_ORIGINS`. Give `STORAGE_PATH` persistent storage and
back up both it and the database, including the storage directory's `.model-credentials.key`
if you use per-account AI credentials. Production session cookies require HTTPS.
See [`.env.example`](.env.example) for the available settings.

The production frontend includes a PWA. Once your instance is served over HTTPS, use
**Add to Home Screen** in Safari on iPhone, or **Install app** in a supporting Android browser.

## Authentication

| Mode | Configuration |
|---|---|
| `local` | Email and password, with open registration. No identity provider needed. |
| `oidc` | Set `OIDC_ISSUER`, `OIDC_CLIENT_ID` and `OIDC_CLIENT_SECRET`. Register `https://your-host/auth/callback` with your provider. |

OIDC uses discovery and the authorization-code flow with PKCE. Set `OIDC_REDIRECT_URI`
when a reverse proxy requires an explicit callback URL; disable `OIDC_PKCE` only if the
provider requires it. Sessions use signed, httpOnly, `SameSite=Lax` cookies.

## Optional AI import

Configure a model under **Profile → AI model**, or set instance defaults in `.env`:

```dotenv
LLM_MODEL=<provider>/<model>
LLM_API_KEY=<your-provider-key>
# For a self-hosted model, set its address as reachable from the API container:
# LLM_BASE_URL=http://your-model-host:11434
```

Use a model supported by LiteLLM; scanned documents need a model with vision support.
Account settings override the instance defaults. Stored account API keys are encrypted
with a Fernet key kept in persistent storage and are never returned to the browser.
Leave the model unconfigured to use manual entry only.

For lab reports, the import workflow accepts PDF, JPEG and PNG:

1. **Prepare locally.** Vital sanitises labelled identity data before contacting the model.
   Text PDFs become sanitised text; scanned pages become sanitised images. Image processing
   removes metadata, detects identity fields and machine-readable codes, and blurs detected faces.
2. **Extract and match.** The model's structured response is validated and matched against
   catalogue names and Portuguese aliases.
3. **Review and confirm.** Check every value in the preview before saving it to your history.
   The original upload is retained locally for comparison.

Sanitisation is not a guarantee of anonymity. A hosted model receives the processed health
data; choose a self-hosted model to keep model processing on your own infrastructure.
`EXTRACTION_MAX_PAGES` and `UPLOAD_MAX_BYTES` limit each upload.

## Development and documentation

**FastAPI · SQLAlchemy · Alembic · PostgreSQL · React · TypeScript · Vite · Tailwind CSS · Recharts · LiteLLM**

<details>
  <summary><strong>Running without Docker</strong></summary>

Needs PostgreSQL 16, Python 3.12+ and Node.js 22+. For the import pipeline, install the
system dependencies listed in [the backend Dockerfile](backend/Dockerfile), including
Tesseract with English and Portuguese language data and libzbar.

From the repository root, in an API terminal:

```bash
cd backend
python -m venv .venv
.venv/bin/pip install -e '.[dev]'
export DATABASE_URL=postgresql+asyncpg://vital:password@localhost:5432/vital
export AUTH_MODE=local
export STORAGE_PATH=/tmp/vital-storage
.venv/bin/alembic upgrade head
.venv/bin/uvicorn app.main:app --reload
```

Create the database and role first, and replace the connection details above with yours.
Use a persistent storage path for records you intend to keep. To populate the demo, also
export `SEED_DEMO_DATA=true` before starting the API.

In a second terminal, from the repository root:

```bash
cd frontend
npm ci
npm run dev
```

</details>

| Path | Contents |
|---|---|
| [`backend/`](backend/) | API, migrations and pytest suite |
| [`frontend/`](frontend/) | Responsive interface, PWA, Vitest and Playwright suites |
| [`seed/`](seed/) | Biomarker and body-composition catalogues |
| [`scripts/`](scripts/) | Catalogue validation and README screenshot capture |

- [Development setup, conventions and checks](CONTRIBUTING.md)
- [Clinical catalogue conventions and provenance](seed/README.md)
- [How to refresh the README screenshots](.github/SCREENSHOTS.md)
- [Report a problem or suggest an improvement](https://github.com/11VitorAlves11/vital/issues)
- [Report a security vulnerability privately](SECURITY.md)

## Not a medical device

Vital records and visualises data you already have. It does not diagnose or replace clinical
judgement. Bioimpedance readings are estimates; use their history as context rather than
treating an isolated value as a precise measurement.

## Licence

[AGPL-3.0-or-later](LICENSE).
