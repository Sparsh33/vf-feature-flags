# Contributing

## Structure per domain

Each domain lives in `backend/app/services/<domain>/`. File names:

| File | Purpose |
|---|---|
| `<domain>_route.py` | FastAPI router, exports `router: APIRouter` (no prefix — main.py adds it) |
| `<domain>_controller.py` | Thin HTTP boundary, maps service exceptions to HTTPException |
| `<domain>_service.py` | Business logic, raises `ValueError` / custom exceptions from `app/common/errors.py` |
| `<domain>_model.py` | Pydantic request/response + DB models |
| `repositories/<domain>_repository.py` | Mongo collection access; extends `BaseRepository` |
| `tasks.py` | Celery tasks (optional) |

Tests go in `backend/tests/<domain>/`.

## Rules

- Each domain touches only its own folder (plus tests + shared error classes if needed).
- Never edit `main.py` — it pre-wires all routers via `ROUTER_MODULES`.
- Register Mongo indexes via `app.database.indexes.register_index_builder(your_ensure_indexes_fn)`.
- Celery tasks autodiscover: audit + analytics are pre-imported in `app/tasks/__init__.py`.
- Every Mongo query filter MUST include `client_id` (cross-tenant isolation is non-negotiable).
- Use `Depends(get_current_user)` or `Depends(get_current_client)` from `app.services.auth.dependencies`.
- Logging: use `log_info/log_warning/log_error/log_debug` from `app.common.logging_helpers` with a `LoggingData` instance. Never use the `logging` module directly.
- Errors: raise typed exceptions from `app.common.errors`; controllers map to HTTP.
- Style: black line-length=100, py312. ZERO blank lines inside function bodies. Type hints everywhere.

## Local setup

```bash
# Backend venv (shared across agents)
cd backend && python3.12 -m venv venv && venv/bin/pip install -r requirements.txt

# Run full stack
docker-compose up -d

# Run tests
backend/venv/bin/pytest backend/tests/ -v

# Lint + format
backend/venv/bin/black backend/ --line-length=100
backend/venv/bin/ruff check backend/ --fix
```

## Dashboard

```bash
cd dashboard && npm install && npm run dev
```
