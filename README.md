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
7. [Deployment](#deployment)
   - [Frontend on Vercel](#frontend-on-vercel)
   - [Backend deployment options](#backend-deployment-options)
   - [Why not the full stack on Vercel](#why-not-the-full-stack-on-vercel)
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

| Tool | Version | Purpose |
|---|---|---|
| Docker Desktop | 20+ | runs the whole stack |
| [Ollama](https://ollama.com) | 0.3.0+ | local LLM for the NL chatbot |
| Node | 20+ | only needed if running dashboard outside Docker |
| Python | 3.12 | only needed if running backend outside Docker |

Ollama runs **on the host machine**, not inside docker-compose. The API container reaches it via `host.docker.internal:11434`.

---

## Local quick start

```bash
# 1. clone + env
git clone <this-repo> vf-feature-flags
cd vf-feature-flags
cp .env.example .env

# 2. Ollama (one-time) — ~4.7 GB download
brew install ollama
ollama serve &                 # starts on :11434
ollama pull llama3.1:8b        # tool-call capable model

# 3. Stack
docker-compose up -d
docker-compose ps              # verify all services healthy
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

## Deployment

The split is important: the **dashboard** deploys cleanly to Vercel as a static SPA. The **backend** does not — it requires a persistent Python process, a Celery worker, MongoDB, Redis, and a GPU/CPU runtime for Ollama. Deploy the backend to a platform that runs long-lived containers.

### Frontend on Vercel

The `dashboard/` folder is a standard Vite project. Two deployment modes:

**Option A — Vercel CLI from the repo**

```bash
npm i -g vercel
cd dashboard
vercel link          # first time: create new project
vercel env add VITE_API_BASE_URL production   # e.g. https://api.yourdomain.com
vercel --prod
```

**Option B — Git integration (recommended)**

1. Push the repo to GitHub.
2. Go to https://vercel.com/new → import the repo.
3. Under "Root Directory" choose `dashboard`.
4. Framework: Vercel auto-detects Vite.
5. Build command: `npm run build` · Output: `dist`.
6. Environment variable: `VITE_API_BASE_URL=https://api.yourdomain.com`.
7. Deploy.

**Required source change** (one line): `dashboard/src/lib/api.ts` currently points at `/api` and relies on Vite's dev proxy. For Vercel, point axios at `import.meta.env.VITE_API_BASE_URL`:

```ts
const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api',
});
```

Vercel config (`dashboard/vercel.json`, optional — only for SPA fallback):

```json
{
  "rewrites": [{ "source": "/(.*)", "destination": "/index.html" }]
}
```

That's it. Every commit to main auto-deploys to production; PRs get preview URLs.

### Backend deployment options

You need: FastAPI container, Celery worker, MongoDB, Redis, and either Ollama or Anthropic. Pick a platform that supports long-lived processes.

| Platform | FastAPI | Celery | Mongo | Redis | Ollama | Cost |
|---|---|---|---|---|---|---|
| **Railway** | ✅ container | ✅ separate service | ✅ plugin | ✅ plugin | ⚠️ sidecar container, small model only | $5/mo + usage |
| **Render** | ✅ web service | ✅ background worker | ✅ managed | ✅ managed | ❌ (use Anthropic) | ~$14/mo |
| **Fly.io** | ✅ | ✅ | use Atlas | use Upstash | ✅ GPU tier | pay-as-you-go |
| **AWS ECS/Fargate** | ✅ | ✅ | Atlas/DocDB | ElastiCache | ✅ GPU ECS task | moderate ops |
| **DigitalOcean App Platform** | ✅ | ✅ | managed | managed | ❌ | ~$12/mo |

**Recommended minimal setup (Railway):**

1. Railway project → new service from repo, root `backend/`.
2. Second service in the same project: same image, override command to `celery -A celery_app.celery worker --loglevel=info`.
3. Add Mongo plugin → sets `MONGO_URI` in env.
4. Add Redis plugin → sets `REDIS_URL` and `CELERY_BROKER_URL`.
5. Set `NL_PROVIDER=anthropic`, `ANTHROPIC_API_KEY=...` (simplest path; Ollama on Railway needs a separate container with a pinned model).
6. Set `CORS_ORIGINS=https://your-vercel-app.vercel.app`.
7. Expose port 8000 → gives you `https://vf-ff-api.up.railway.app`.
8. On Vercel, set `VITE_API_BASE_URL=https://vf-ff-api.up.railway.app` → redeploy.

**Managed DB alternative (any platform):**

- Mongo: [MongoDB Atlas](https://www.mongodb.com/atlas) free M0 tier (512 MB)
- Redis: [Upstash](https://upstash.com/) free tier (256 MB, 10k commands/day)

Swap the `MONGO_URI` / `REDIS_URL` / `CELERY_BROKER_URL` env vars to the managed-service URIs and stop running Mongo/Redis yourself.

### Why not the full stack on Vercel

Vercel's Python runtime is **serverless only** — every request spins up a new function invocation. That breaks several assumptions in this codebase:

1. **Celery worker** — needs a long-lived process subscribed to Redis. Serverless invocations can't host one. You'd need a separate service anyway.
2. **Motor connection pool** — cold starts re-establish Mongo connections; reasonable for low traffic, painful at scale.
3. **FastAPI lifespan** — `ensure_all_indexes`, redis client init, etc. would run per cold start instead of once at boot.
4. **Ollama** — the LLM daemon needs a persistent host with RAM/VRAM for the model; Vercel functions have a 50MB code budget and ephemeral storage.
5. **In-process caches** — Redis covers this, but any in-memory cache (e.g. FastAPI's lifespan state) evaporates per invocation.

The dashboard does not have any of these constraints — it's static files after `npm run build`. That's why the split makes sense.

**If you're determined to try Vercel for the API:** you can wrap FastAPI with `@vercel/python` in a `api/index.py`, move Celery to another platform (e.g. Upstash QStash or Railway worker), and use Anthropic instead of Ollama. Expect cold-start latency on every burst.

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
