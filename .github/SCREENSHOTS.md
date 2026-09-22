# README screenshots

The README uses real Chromium captures, with English UI, European Portuguese catalogue
labels, and synthetic data from `backend/app/db/demo.py`. Desktop captures are 1440 × 1000;
mobile captures use a 390 × 844 viewport with touch and mobile emulation. Images are saved
without editing in `.github/images/`.

## Refresh

Use a disposable development instance with a **fresh database**, `AUTH_MODE=local` and
`SEED_DEMO_DATA=true`. An existing demo account may contain manually added or imported
health records: do not publish screenshots from it without reviewing every visible value.
Do not delete your normal development database to refresh these images.

With the disposable instance running on port 5173, install the frontend dependencies and
Playwright browser, then run the capture script from the repository root:

```bash
npm ci --prefix frontend
cd frontend
npx playwright install --with-deps chromium
cd ..
node scripts/readme-screenshots.mjs
```

`E2E_BASE_URL` can point to a different local development instance. The script signs in
using the known demo credentials, selects English and the light theme, then captures the
dashboard, a biomarker trend, the dark dashboard and three mobile screens. It does not
create or modify health records. It reports browser exceptions and server errors.

If the host lacks browser dependencies, use the Playwright Docker image matching the
version installed in `frontend/node_modules/@playwright/test/package.json`. Mount the
repository at `/work`, run `node scripts/readme-screenshots.mjs` there and set
`E2E_BASE_URL` to the disposable web service on its Docker network. The Vite server must
allow that hostname.

Review all six images for loaded data, readable text, correct themes and absence of personal
information before committing them. Keep the screenshots and README captions in sync.
