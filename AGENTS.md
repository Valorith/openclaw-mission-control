# Repository Guidelines

## Project Structure & Module Organization
- `backend/`: FastAPI service.
  - App code: `backend/app/` (routes `backend/app/api/`, models `backend/app/models/`, schemas `backend/app/schemas/`, workers `backend/app/workers/`).
  - DB migrations: `backend/migrations/` (generated versions in `backend/migrations/versions/`).
  - Tests: `backend/tests/`.
- `frontend/`: Next.js app.
  - Routes: `frontend/src/app/`; shared UI: `frontend/src/components/`; utilities: `frontend/src/lib/`.
  - Generated API client: `frontend/src/api/generated/` (do not edit by hand).
  - Tests: colocated `*.test.ts(x)` (example: `frontend/src/lib/backoff.test.ts`).
- `templates/`: shared templates packaged into the backend image (used by gateway integrations).
- `docs/`: protocol/architecture notes (see `docs/openclaw_gateway_ws.md`).

## Build, Test, and Development Commands
From repo root:
- `make setup`: install/sync backend + frontend dependencies.
- `make check`: CI-equivalent suite (lint, typecheck, tests/coverage, frontend build).
- `docker compose -f compose.yml --env-file .env up -d --build`: run full stack.

Fast local dev:
- `docker compose -f compose.yml --env-file .env up -d db`
- Backend: `cd backend && uv sync --extra dev && uv run uvicorn app.main:app --reload --port 8000`
- Frontend: `cd frontend && npm install && npm run dev`
- API client: `make api-gen` (backend must be running on `127.0.0.1:8000`).

## Coding Style & Naming Conventions
- Python: Black + isort (line length 100), flake8 (`backend/.flake8`), strict mypy (`backend/pyproject.toml`). Use `snake_case`.
- TypeScript/React: ESLint (Next.js) + Prettier (`make frontend-format`). Components `PascalCase`, variables `camelCase`. Prefix intentionally-unused destructured props with `_` (see `frontend/eslint.config.mjs`).
- Optional: `pre-commit install` to run format/lint hooks locally.

## Testing Guidelines
- Backend: pytest (`backend/tests/`, files `test_*.py`). Run `make backend-test` or `make backend-coverage` (writes `backend/coverage.xml`).
- Frontend: vitest + testing-library. Run `make frontend-test` (writes `frontend/coverage/`).

## Commit & Pull Request Guidelines
- Commits: Conventional Commits (e.g., `feat: ...`, `fix: ...`, `docs: ...`, `chore: ...`, `refactor: ...`; optional scope like `feat(chat): ...`).
- PRs: include what/why, how to test (ideally `make check`), linked issue (if any), and screenshots for UI changes.

## Security & Configuration Tips
- Never commit secrets. Use `.env.example` as the template and keep real values in `.env`.
