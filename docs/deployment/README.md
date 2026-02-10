# Deployment / Self-hosting (Docker Compose)

This guide covers how to self-host **OpenClaw Mission Control** using the repository’s `compose.yml`.

> Scope
> - This is a **dev-friendly self-host** setup intended for local or single-host deployments.
> - For production hardening (TLS, backups, external Postgres, observability), see **Production notes** below.

## What you get

When running Compose, you get:

- **Postgres** database (persistent volume)
- **Backend API** (FastAPI) on `http://localhost:${BACKEND_PORT:-8000}`
  - Health check: `GET /healthz`
- **Frontend UI** (Next.js) on `http://localhost:${FRONTEND_PORT:-3000}`

Auth (Clerk) is **required** right now. You must configure Clerk keys for the frontend, and configure `CLERK_JWKS_URL` for the backend so protected API routes can verify JWTs.

## Requirements

- Docker Engine
- Docker Compose **v2** (`docker compose ...`)
- Recommended: **4GB+ RAM** (frontend build can be memory/CPU intensive)

## Quick start (self-host)

From repo root:

```bash
cp .env.example .env

docker compose -f compose.yml --env-file .env up -d --build
```

Check containers:

```bash
docker compose -f compose.yml ps
```

## Sanity checks

Backend health:

```bash
curl -f http://localhost:${BACKEND_PORT:-8000}/healthz
```

Frontend serving:

```bash
curl -I http://localhost:${FRONTEND_PORT:-3000}/
```

## Compose overview

### Services

`compose.yml` defines:

- `db` (Postgres 16)
- `backend` (FastAPI)
- `frontend` (Next.js)

### Ports

By default:

- Postgres: `5432` (`POSTGRES_PORT`)
- Backend: `8000` (`BACKEND_PORT`)
- Frontend: `3000` (`FRONTEND_PORT`)

Ports are sourced from `.env` (passed via `--env-file .env`) and wired into `compose.yml`.

### Volumes (data persistence)

Compose creates named volumes:

- `postgres_data` → Postgres data directory

These persist across `docker compose down`.

## Environment strategy

### Root `.env` (Compose)

- Copy the template: `cp .env.example .env`
- Edit values as needed (ports, Clerk URLs/keys, etc.)

Compose is invoked with:

```bash
docker compose -f compose.yml --env-file .env ...
```

### Backend env

The backend container loads `./backend/.env.example` via `env_file` and then overrides the DB URL for container networking.

If you need backend customization, prefer creating a real `backend/.env` and updating compose to use it (optional improvement).

### Frontend env

`compose.yml` intentionally **does not** load `frontend/.env.example` at runtime, because it may contain non-empty placeholders.

Instead, it supports an optional user-managed env file:

- `frontend/.env` (not committed)

If present, Compose will load it.

## Clerk (auth) notes

Clerk is currently required.

### Frontend (Clerk keys)

Create `frontend/.env` (this file is **not** committed; `compose.yml` loads it if present):

```env
# Frontend → Backend
NEXT_PUBLIC_API_URL=http://localhost:8000

# Frontend → Clerk
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=YOUR_PUBLISHABLE_KEY
CLERK_SECRET_KEY=YOUR_SECRET_KEY

# Optional (but recommended) redirects
NEXT_PUBLIC_CLERK_SIGN_IN_FORCE_REDIRECT_URL=/boards
NEXT_PUBLIC_CLERK_SIGN_UP_FORCE_REDIRECT_URL=/boards
NEXT_PUBLIC_CLERK_SIGN_IN_FALLBACK_REDIRECT_URL=/boards
NEXT_PUBLIC_CLERK_SIGN_UP_FALLBACK_REDIRECT_URL=/boards
```

### Backend (JWT verification)

The backend verifies Clerk JWTs using **`CLERK_JWKS_URL`**.

- Compose loads `backend/.env.example` by default, where `CLERK_JWKS_URL` is empty.
- For a real deployment, provide a real value either by:
  1) creating `backend/.env` and updating `compose.yml` to load it (preferred), **or**
  2) adding `CLERK_JWKS_URL: ${CLERK_JWKS_URL}` under `backend.environment` and setting it in root `.env`.

Related backend env vars (optional tuning):
- `CLERK_VERIFY_IAT` (default: true)
- `CLERK_LEEWAY` (default: 10.0)

**Security:** treat `CLERK_SECRET_KEY` like a password. Do not commit it.

## Troubleshooting

### 1) Check container status

```bash
docker compose -f compose.yml ps
```

### 2) Tail logs

```bash
docker compose -f compose.yml --env-file .env logs -f --tail=200
```

### 3) Common issues

- **Docker permission denied** (`/var/run/docker.sock`)
  - Ensure your user is in the `docker` group and your session picked it up (re-login), or use a root/sudo-capable host.
- **Frontend build fails because of missing `public/`**
  - If the repo doesn’t have `frontend/public`, the Dockerfile should not `COPY public/`.
- **Backend build fails looking for `uv.lock`**
  - If backend build context is repo root, Dockerfile must copy `backend/uv.lock` not `uv.lock`.

## Reset / start fresh

Safe (keeps volumes/data):

```bash
docker compose -f compose.yml --env-file .env down
```

Destructive (removes volumes; deletes Postgres data):

```bash
docker compose -f compose.yml --env-file .env down -v
```

## Production notes (future)

If you’re running this beyond local dev, consider:

- Run Postgres as a managed service (or on a separate host)
- Add TLS termination (reverse proxy)
- Configure backups for Postgres volume
- Set explicit resource limits and healthchecks
- Pin image versions/tags and consider multi-arch builds
