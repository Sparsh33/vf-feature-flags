# vf-feature-flags

A feature-flag SaaS with a FastAPI backend, Celery worker, MongoDB + Redis, and a React/Vite dashboard. Supports deterministic cohort bucketing, gradual rollouts, async audit logging, request analytics, and a natural-language flag builder powered by a local Ollama model (no Anthropic key required).

---

## Table of contents

1. [Architecture](#architecture)
2. [Requirements](#requirements)
3. [Local quick start](#local-quick-start)
4. [Testing on local](#testing-on-local)
   - [Automated backend smoke](#automated-backend-smoke)
   - [Playwright E2E (dashboard)](#playwright-e2e-dashboard)
   - [Unit tests](#unit-tests)
5. [API reference (cheat sheet)](#api-reference-cheat-sheet)
6. [Configuration](#configuration)
7. [Deployment — Docker only](#deployment--docker-only)
8. [Troubleshooting](#troubleshooting)

---

## Architecture

```
┌─────────────┐  JWT   ┌────────────────────────────┐    Mongo
│   React     │───────►│  Dashboard API             │◄───(flags, users,
│  Dashboard  │        │  /api/auth, /api/flags,    │    clients, audit,
└─────────────┘        │  /api/audit, /api/analytics│    analytics, nl)
                       │  /api/nl, /api/clients     │
                       └──────────────┬─────────────┘
                                      │
┌──────────────┐  X-Client-API-Key    ▼
│ Client App   │──────►┌──────────────────────────────────┐
│ (any lang)   │       │ POST /v1/evaluate/{flag_key}     │     Redis
└──────────────┘       │ hash(client+flag+body) → cache   │◄─── (TTL 15m)
                       │ miss → Mongo → xxhash % 10000    │
                       │ → cohort → set cache             │
                       └─────────────────┬────────────────┘
                                         │ celery.delay
                                         ▼
                            ┌────────────────────────┐
                            │  Celery worker         │───► Mongo
                            │  (audit + analytics)   │    (audit_logs,
                            └────────────────────────┘     analytics_events)

                       ┌─────────────────────────────┐
 NL chat (dashboard) ──►│  /api/nl/chat               │───► Ollama (local)
                        │  tool-call → draft flag     │     llama3.1:8b
                        │  compact at 70% of budget   │
                        └─────────────────────────────┘
```

**Design highlights**

- **Stateless bucketing** — no per-user row; `xxhash(client_id + flag_key + body) % 10000` is deterministic and sticky for free.
- **Cache-through** — Redis caches the full eval result keyed on `sha256(canonical_json(body) + client_id)` with 15-min TTL. Flag edits invalidate the key range.
- **Cross-client isolation** — every Mongo query filter includes `client_id`. Tests explicitly verify client A can't see client B.
- **Availability > Consistency** — cache, analytics, and audit emits never fail the eval request.
- **Audit is async** — Celery task with retry; request-path fire-and-forget.
- **NL builder** — Claude-or-Ollama abstraction; tool calls extract flag params progressively; context compacts at 70% of input budget while preserving extracted params.

---

## Requirements

**The only thing you need is Docker.** Ollama, the LLM model, Mongo, Redis — everything else runs as compose services. First-run will pull the `llama3.1:8b` model automatically (~4.7 GB, one-time download).

| Tool | Required? | Notes |
|---|---|---|
| Docker Desktop | ✅ yes | 20+ with Docker Compose v2 |
| Node / Python / Ollama on host | ❌ no | all bundled as compose services |

> **Heads up:** Ollama inside Docker on macOS/Windows runs **CPU-only** (no Metal/GPU). Fine for correctness; NL turns take 10-30s per reply. For Linux hosts with NVIDIA GPUs, add `deploy.resources.reservations.devices: [{driver: nvidia, count: 1, capabilities: [gpu]}]` under the `ollama` service.

---

## Local quick start

```bash
git clone https://github.com/Sparsh33/vf-feature-flags.git
cd vf-feature-flags
docker-compose up -d         # that's it.
```

First run takes a while — it builds backend + dashboard images and pulls the Ollama model (~4.7 GB). Follow along:

```bash
docker-compose logs -f ollama-init   # watch the model pull
docker-compose ps                     # all services should be healthy
```

**Optional** — customize defaults (JWT secret, model, CORS origins, etc.):

```bash
cp .env.example .env      # edit any values you want to override
docker-compose up -d      # re-reads .env automatically
```

Open:

- Dashboard → http://localhost:5173
- Swagger → http://localhost:8000/docs
- Health → http://localhost:8000/health

**First-run journey:**

1. Visit `/signup`, create a user. The API key is shown **once** in a modal — copy it.
2. On `/flags`, click "New Flag" or "Build with AI".
3. Use the eval API with the copied API key:
   ```bash
   curl -X POST http://localhost:8000/v1/evaluate/<flag_key> \
     -H "X-Client-API-Key: <your-key>" \
     -H "content-type: application/json" \
     -d '{"user_id":"u1","country":"IN"}'
   ```

To tear down:

```bash
docker-compose down         # keep data
docker-compose down -v      # drop volumes (mongo + redis state)
```

---

## Testing on local

Three layers of tests.

### Automated backend smoke

End-to-end curl walkthrough covering every major flow (signup → flag CRUD → 500 evals → stickiness → cache hit → edit invalidation → audit → analytics → soft-delete → rotate API key).

```bash
docker-compose up -d
./scripts/backend_smoke.sh
```

Expected output (abridged):

```
== 1. Health           PASS GET /health → ok
== 2. Signup           PASS POST /api/auth/signup → JWT + api_key
== 5. Create flag      PASS POST /api/flags/ → created
== 8. Evaluate 500×    PASS 500 evals within ±8% of 60/40 target
== 9. Stickiness       PASS same input → same cohort (control)
== 10. Cache hit       PASS reason=cached on repeat call
== 11. Cache invalidate PASS post-edit reason=computed
== 13. Analytics       PASS total_requests=500
================================================
  Total: 19  19 pass  0 fail
================================================
```

Requires `jq` and `curl` on PATH (`brew install jq`).

### Playwright E2E (dashboard)

Full dashboard flows — signup, cohort editor validation, NL chat, analytics charts, audit viewer.

```bash
# one-time
cd dashboard
npm install
npx playwright install chromium

# run against the docker-compose stack (must be up)
npm run test:e2e            # headless
npm run test:e2e:ui         # interactive debugging
npm run test:e2e:headed     # watch the browser
```

Specs:

| File | Covers |
|---|---|
| `e2e/01-auth.spec.ts` | signup, login, /me rehydrate, bad-creds toast |
| `e2e/02-flags-crud.spec.ts` | create, cohort sum validator, auto-distribute, delete, cross-client isolation |
| `e2e/03-nl-chat.spec.ts` | NL chat extracts params, commits flag |
| `e2e/04-analytics-audit.spec.ts` | charts render, audit rows click → drawer |
| `e2e/05-settings.spec.ts` | API key rotation |

NL chat tests are marked `test.slow()` (Ollama is CPU-bound). Flakiness there is expected on first run as the model warms up.

### Unit tests

```bash
# backend
cd backend
python3.12 -m venv venv && venv/bin/pip install -r requirements.txt
venv/bin/pytest tests/ -v

# expected: ~155 tests across 6 domains
```

Format/lint:

```bash
venv/bin/black backend/ --line-length=100
venv/bin/ruff check backend/ --fix
```

---

## API reference (cheat sheet)

Full Swagger UI at `http://localhost:8000/docs`.

### Auth (dashboard)

| Method | Path | Notes |
|---|---|---|
| `POST` | `/api/auth/signup` | returns `{user, client, api_key (once), access_token}` |
| `POST` | `/api/auth/login` | returns `{user, access_token}` |
| `GET` | `/api/auth/me` | JWT — returns current user |
| `POST` | `/api/clients/rotate-api-key` | JWT — returns new plaintext key |

### Flags (dashboard)

| Method | Path | Notes |
|---|---|---|
| `POST` | `/api/flags/` | create; cohorts must sum to 100 ± 0.01 |
| `GET` | `/api/flags/` | list; query `status`, `limit`, `skip` |
| `GET` | `/api/flags/{id}` | detail |
| `PATCH` | `/api/flags/{id}` | partial update; invalidates cache |
| `DELETE` | `/api/flags/{id}` | soft delete |

### Eval (client apps)

| Method | Path | Auth | Notes |
|---|---|---|---|
| `POST` | `/v1/evaluate/{flag_key}` | `X-Client-API-Key` | body is arbitrary JSON; returns `{value, cohort_id, cohort_name, reason}` where `reason ∈ {cached, computed, fallback, not_found}` |

### Analytics, audit, NL

| Method | Path | Notes |
|---|---|---|
| `GET` | `/api/analytics/flags/{id}` | totals + per-cohort counts |
| `GET` | `/api/analytics/flags/{id}/time-series` | interval=`minute`/`hour`/`day` |
| `GET` | `/api/audit/` | query: `resource_type`, `resource_id`, `action`, `limit`, `skip` |
| `POST` | `/api/nl/chat` | JWT — chatbot turn; returns reply + extracted + optional draft flag |

---

## Configuration

All via `.env` (see `.env.example` for the canonical list).

| Key | Default | Purpose |
|---|---|---|
| `MONGO_URI` | `mongodb://mongo:27017` | Mongo connection |
| `MONGO_DB` | `vf_feature_flags` | DB name |
| `REDIS_URL` | `redis://redis:6379/0` | cache + Celery broker |
| `CELERY_BROKER_URL` | `redis://redis:6379/1` | separate DB for Celery |
| `JWT_SECRET` | `change-me-in-prod` | HS256 signing key |
| `JWT_TTL_MINUTES` | `1440` | 24h |
| `CORS_ORIGINS` | `http://localhost:5173` | comma-separated |
| `NL_PROVIDER` | `ollama` | `ollama` or `anthropic` |
| `OLLAMA_BASE_URL` | `http://host.docker.internal:11434` | from inside Docker |
| `OLLAMA_MODEL` | `llama3.1:8b` | must support tool calling |
| `NL_INPUT_TOKEN_BUDGET` | `8192` | compaction threshold base |
| `NL_COMPACTION_TRIGGER` | `0.70` | fraction (0.0–1.0) |
| `ANTHROPIC_API_KEY` | *(empty)* | only needed if `NL_PROVIDER=anthropic` |

---

## Deployment — Docker only

The entire stack ships as Docker containers. `docker-compose.yml` is the single source of truth for both local development and production-like environments. Nothing special is required to "deploy" — run the same compose file on any host with Docker Engine.

### Services

| Service | Image / Build | Ports | Role |
|---|---|---|---|
| `api` | built from `backend/Dockerfile` | 8000 | FastAPI, uvicorn with auto-reload for local |
| `worker` | same image as `api` (overridden command) | — | Celery worker; picks up audit + analytics tasks |
| `dashboard` | built from `dashboard/Dockerfile` | 5173 | Vite dev server (SPA) |
| `mongo` | `mongo:7` | 27017 | primary datastore; `mongo_data` volume |
| `redis` | `redis:7-alpine` | 6379 | cache + Celery broker; `redis_data` volume |

Ollama runs **on the host**, not in compose. The `api` container reaches it via `host.docker.internal:11434`.

### Local / single-host production

```bash
# one-time setup
cp .env.example .env
# edit .env — at minimum set JWT_SECRET and CORS_ORIGINS

# install Ollama on the host
brew install ollama             # macOS; use the Ollama installer on Linux
ollama serve &
ollama pull llama3.1:8b         # ~4.7 GB, tool-call capable

# bring up the stack
docker-compose up -d --build
docker-compose ps               # all services should be healthy
```

Dashboard: http://localhost:5173 · API: http://localhost:8000/docs · Health: http://localhost:8000/health

### Production hardening checklist

For anything past local dev, edit `docker-compose.yml` or create an override file (`docker-compose.prod.yml`) with these changes:

1. **Replace dev commands with production ones**:
   - `api.command: uvicorn main:app --host 0.0.0.0 --workers 4` (drop `--reload`)
   - `dashboard` should build once and serve via nginx instead of `npm run dev`. See `dashboard/Dockerfile.prod` pattern:
     ```dockerfile
     FROM node:20-alpine AS build
     WORKDIR /app
     COPY package*.json ./
     RUN npm ci
     COPY . .
     RUN npm run build
     FROM nginx:alpine
     COPY --from=build /app/dist /usr/share/nginx/html
     COPY nginx.conf /etc/nginx/conf.d/default.conf
     ```
     with an `nginx.conf` that proxies `/api/**` → `http://api:8000` and does SPA fallback (`try_files $uri /index.html`).
2. **Mount volumes correctly**:
   - Remove the `./backend:/app` bind mount used for hot-reload.
3. **Secrets via env file or Docker secrets** — never commit `.env`.
4. **Reverse proxy / TLS**: put Caddy or Traefik in front of the compose network; point it at `api:8000` and `dashboard:80`. Caddy example:
   ```
   api.example.com { reverse_proxy api:8000 }
   app.example.com { reverse_proxy dashboard:80 }
   ```
5. **Resource limits** — add `deploy.resources` per service.
6. **Healthchecks** already defined for mongo + redis; add one for `api` hitting `/health`.
7. **Log aggregation** — point Docker's `--log-driver=json-file` or ship to your preferred aggregator.

### Ollama in production

Two options, pick based on where you're hosting:

- **Host-native** (same as local) — Ollama runs on the host OS, api container reaches it via `extra_hosts: ["host.docker.internal:host-gateway"]` on Linux.
- **Sidecar container** — add an `ollama/ollama` service to compose with a GPU-enabled runtime (`deploy.resources.reservations.devices`), volume-mount `/root/.ollama` for model storage. Point `OLLAMA_BASE_URL=http://ollama:11434` in `.env`. Initial model pull must be done via `docker-compose exec ollama ollama pull llama3.1:8b`.

### What `docker-compose up -d` does end-to-end

```
┌─────────────────────────────────────────────┐
│  docker-compose up -d                        │
├─────────────────────────────────────────────┤
│  1. Build api/worker/dashboard images       │
│  2. Start mongo, redis → wait for healthy   │
│  3. Start api (lifespan: connects Mongo+    │
│     Redis, ensures indexes)                 │
│  4. Start worker (Celery registers tasks    │
│     audit.record + analytics.record_eval_   │
│     event, connects to Redis broker)        │
│  5. Start dashboard (Vite dev or nginx      │
│     serving /dist)                          │
└─────────────────────────────────────────────┘
```

### Scaling notes

- **API**: horizontal — add `api2`, `api3` services and front them with a load balancer. Each is stateless.
- **Worker**: horizontal — `docker-compose up -d --scale worker=4`.
- **Mongo/Redis**: migrate to managed services (Atlas / Upstash / AWS) when single-node is a bottleneck. Just change `MONGO_URI` / `REDIS_URL` / `CELERY_BROKER_URL` in `.env` — no code changes.

---

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `docker-compose up` hangs on `api` | waiting on mongo/redis healthcheck | `docker-compose logs mongo redis` — check for port conflict on 27017/6379 |
| API returns 500 on `/api/nl/chat` | Ollama unreachable from container | verify `curl http://host.docker.internal:11434/api/tags` from host; on Linux add `extra_hosts: ["host.docker.internal:host-gateway"]` to compose |
| Eval returns `reason: "fallback"` | Mongo or Redis down mid-request | check container health; cache tolerates Redis outage but DB is required |
| `X-FF-Fallback: true` header present | service error during eval; flag's `default_value` returned | check API logs for underlying exception |
| Dashboard 401 on every request | JWT expired or cleared | log out / log back in; token TTL is `JWT_TTL_MINUTES` |
| `cohorts sum != 100` rejected creates | validation guard working as intended | adjust percentages or use "Distribute remaining" button |
| Playwright flakes on NL spec | LLM cold start or small model can't tool-call | rerun; if persistent, pull a larger model: `ollama pull llama3.1:70b` |

---

## Project structure

```
vf-feature-flags/
├── backend/
│   ├── main.py                          FastAPI entry + ROUTER_MODULES registry
│   ├── celery_app.py                    Celery app factory
│   ├── app/
│   │   ├── config/settings.py           pydantic-settings
│   │   ├── database/{config,redis_client,base_repository,indexes}.py
│   │   ├── middleware/{request_context,logging_middleware,auth_middleware}.py
│   │   ├── common/{models,errors,logging_helpers}.py
│   │   ├── services/
│   │   │   ├── auth/                    JWT + users + clients + API keys
│   │   │   ├── flag/                    CRUD + cohorts + cache invalidation
│   │   │   ├── eval/                    hot path + bucketing + cache
│   │   │   ├── audit/                   async Celery logging
│   │   │   ├── analytics/               events + aggregation + time-series
│   │   │   └── nl/                      Ollama/Claude chatbot + compaction
│   │   └── tasks/                       Celery autodiscovery
│   └── tests/                           pytest, ~155 tests
├── dashboard/
│   ├── src/
│   │   ├── pages/{auth,flags,settings,chat,analytics,audit}/
│   │   ├── components/{ui,layout,flags,chat,analytics,audit}/
│   │   ├── hooks/, lib/, types/
│   │   └── App.tsx
│   ├── e2e/                             Playwright specs
│   └── package.json
├── scripts/backend_smoke.sh             end-to-end curl walkthrough
├── docker-compose.yml
├── .env.example
├── CONTRIBUTING.md                       domain conventions
└── README.md                             this file
```

---

## Contributing

See `CONTRIBUTING.md`.
