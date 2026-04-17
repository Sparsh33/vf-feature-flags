"""FastAPI entrypoint for vf-feature-flags.

Pre-wires all domain routers with try/except ImportError so the app boots
even while some domains are still unimplemented. Each domain module must
expose a top-level `router: APIRouter`.
"""

import importlib
import logging
from contextlib import asynccontextmanager
from typing import List, Tuple

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config.settings import settings
from app.database.config import mongodb
from app.database.redis_client import redis_client
from app.middleware.logging_middleware import LoggingMiddleware
from app.middleware.request_context import RequestContextMiddleware

logger = logging.getLogger(__name__)

ROUTER_MODULES: List[Tuple[str, str, List[str]]] = [
    ("app.services.auth.auth_route", "/api/auth", ["auth"]),
    ("app.services.auth.client_route", "/api/clients", ["clients"]),
    ("app.services.flag.flag_route", "/api/flags", ["flags"]),
    ("app.services.eval.eval_route", "/v1", ["eval"]),
    ("app.services.audit.audit_route", "/api/audit", ["audit"]),
    ("app.services.analytics.analytics_route", "/api/analytics", ["analytics"]),
    ("app.services.nl.nl_route", "/api/nl", ["nl"]),
]


@asynccontextmanager
async def lifespan(_: FastAPI):
    await mongodb.connect()
    await redis_client.connect()
    try:
        from app.database.indexes import ensure_all_indexes

        await ensure_all_indexes()
    except Exception as exc:  # pragma: no cover - indexes optional at scaffold time
        logger.warning("Index initialization skipped: %s", exc)
    yield
    await redis_client.close()
    await mongodb.close()


def _include_routers(app: FastAPI) -> None:
    for module_path, prefix, tags in ROUTER_MODULES:
        try:
            module = importlib.import_module(module_path)
        except ImportError as exc:
            logger.warning("Skipping router %s (not implemented): %s", module_path, exc)
            continue
        router = getattr(module, "router", None)
        if not isinstance(router, APIRouter):
            logger.warning("Module %s missing `router: APIRouter`; skipped", module_path)
            continue
        app.include_router(router, prefix=prefix, tags=tags)


def create_app() -> FastAPI:
    app = FastAPI(title="vf-feature-flags", version="0.1.0", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(LoggingMiddleware)
    app.add_middleware(RequestContextMiddleware)

    @app.get("/health")
    async def health() -> dict:
        mongo_ok = await mongodb.ping()
        redis_ok = await redis_client.ping()
        status = "ok" if (mongo_ok and redis_ok) else "degraded"
        return {"status": status, "mongo": mongo_ok, "redis": redis_ok}

    _include_routers(app)
    return app


app = create_app()
