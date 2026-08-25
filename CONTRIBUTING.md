# Contributing

Thanks for taking a look. Issues and pull requests are welcome.

## Language

Code, comments, commit messages, issues and pull requests are in **English**.
User-facing strings are translated — `en` and `pt-PT`. Portuguese in this project is
**European Portuguese (PT-PT)**, including the clinical catalogues in `seed/`.

## Getting set up

```bash
cp .env.example .env
docker compose -f docker-compose.dev.yml up --build
```

See the README for the non-Docker path.

## Before opening a pull request

```bash
cd backend  && ruff check . && ruff format --check . && mypy app && pytest
cd frontend && npm run lint && npm run lint:css && npm test && npm run build
python scripts/validate_seed.py
```

CI runs exactly these. A pull request needs all of them green.

## Conventions

- **Conventional Commits** (`feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `chore:`),
  imperative mood, title ≤72 characters. They feed the changelog.
- **Atomic commits** — one logical change each.
- **No hardcoded colours or spacing** in components: use the tokens in
  `frontend/src/design/tokens.css`. Stylelint enforces this.
- **New code ships with tests**; every bug fix ships with a regression test.
- Dependency bumps, CI changes and licence edits go in their own pull requests.

## Changing clinical data

`seed/` holds biomarker reference intervals and the clinical bands used to flag body
composition. Changes there need:

1. A cited standard (WHO, ACE/ACSM, IDF, or a lab reference method) recorded in `source`
   or `notes`.
2. `python scripts/validate_seed.py` passing.
3. An explanation in the pull request of *why* the previous value was wrong.

Bands only exist where a validated clinical standard exists. Metrics without one stay
trend-only (`bands: null`) — inventing thresholds for bioimpedance estimates is
pseudo-precision, and we would rather show nothing.

## Security

Vital handles health data. Do not open a public issue for a vulnerability —
see [SECURITY.md](SECURITY.md).
