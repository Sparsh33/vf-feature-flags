# vf-feature-flags

Feature-flag SaaS: FastAPI backend + Celery worker + React/Vite dashboard on MongoDB + Redis.

## Stack

| Layer      | Tech                                                                 |
| ---------- | -------------------------------------------------------------------- |
| Backend    | FastAPI (Python 3.12), motor, redis-py, Celery                       |
| Worker     | Celery (Redis broker + result backend)                               |
| Datastore  | MongoDB 7                                                            |
| Cache/Bus  | Redis 7                                                              |
| Dashboard  | Vite + React + TypeScript + Tailwind + shadcn/ui + TanStack Query    |
| Auth       | JWT (HS256) for dashboard; `X-Client-API-Key` header for eval API    |

## Quick start

```bash
cp .env.example .env
make up            # docker-compose up -d
make logs          # tail logs
make down          # stop
```

Services:

- API: http://localhost:8000 (Swagger at `/docs`)
- Dashboard: http://localhost:5173
- Mongo: `localhost:27017`
- Redis: `localhost:6379`

## Backend commands

```bash
make backend-test   # pytest
make backend-lint   # ruff check
make backend-fmt    # black + isort
```

## Layout

```
backend/                FastAPI app, Celery worker, tests
  app/config/           pydantic-settings
  app/database/         motor + redis singletons, base repository, indexes
  app/middleware/       request context, logging, auth (stub)
  app/services/<d>/     one folder per domain (auth, flag, eval, audit, analytics, nl)
  app/common/           shared models, errors, logging helpers
  app/tasks/            Celery autodiscovery hub
dashboard/              Vite + React + Tailwind + shadcn/ui
```

## Phase 2 agents

See `CONTRIBUTING.md` for domain ownership rules, filename conventions, and style.
