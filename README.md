# Devops Lab

A microservices playground for a fictional gym membership platform.

## Services

| Service | Responsibility | Port |
|---|---|---|
| `user-service` | Register/list gym members | 5001 |
| `membership-service` | Manage plan signups | 5002 |
| `payment-service` | Record payments with idempotency | 5003 |
| `notification-service` | Store/send mock notifications | 5004 |

## What was improved

- PostgreSQL-backed persistence (no in-memory data loss)
- Consistent JSON error responses with request IDs
- Liveness (`/health`), readiness (`/ready`), and metrics (`/metrics`) endpoints
- Cross-service validations:
  - Membership signup requires existing user
  - Payment requires existing membership
- Duplicate/idempotency handling:
  - Duplicate user email and active membership detection
  - Idempotent payment creation via `X-Idempotency-Key`
- Hardened Dockerfiles (non-root runtime, env-driven config)
- CI workflow for compose build + smoke test
- Deploy workflow for VM target using Docker Compose over SSH

## Run locally with Docker Compose

```bash
docker compose up --build
```

## Database migrations

Apply SQL migrations manually when needed:

```bash
DATABASE_URL=postgresql+psycopg2://devops:changeme@localhost:5432/devops_lab python scripts/apply_migrations.py
```

## Production deployment notes

- Use the production override with the base compose file:
  - `docker compose -f docker-compose.yml -f deploy/docker-compose.prod.yml up -d --build`
- Required env values are in `deploy/.env.example` (including `POSTGRES_PASSWORD`).
- In production, app services are not published on host ports 5001-5004; nginx is exposed on port 80 and path-routes to services:
  - `/users`
  - `/memberships`
  - `/payments`
  - `/notifications`
- Deploy workflow also runs migrations after services come up and Postgres is healthy.

## Smoke test

With services running:

```bash
python scripts/smoke_test.py
```

## CI and deploy

- CI: `.github/workflows/ci.yml`
- Deploy (VM + Docker Compose): `.github/workflows/deploy.yml`
- Production override/env template: `deploy/docker-compose.prod.yml`, `deploy/.env.example`
