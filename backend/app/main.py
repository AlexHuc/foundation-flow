"""Foundation Flow API — read-only access to the PostgreSQL landing schema."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .config import get_settings
from .db import close_pool, connection, ensure_pool, open_pool
from .routes import companies, datasets, pipelines

logger = logging.getLogger("foundation_flow.api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # A missing database at startup must not crash the service: Docker starts
    # containers in dependency order, but PostgreSQL can still be momentarily
    # unreachable. The health endpoint retries the connection and reports 503
    # until the pool is up.
    try:
        await open_pool()
    except Exception:  # noqa: BLE001 — logged, retried via /api/health
        logger.exception("Database pool unavailable at startup; will retry on health checks")
    try:
        yield
    finally:
        await close_pool()


app = FastAPI(
    title="Foundation Flow API",
    description=(
        "Read-only REST API over the PostgreSQL `landing` schema populated by "
        "the Yahoo Finance Airflow pipelines. Empty datasets return empty "
        "lists; the API never fabricates market data."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_methods=["GET"],
    allow_headers=["*"],
)

app.include_router(companies.router)
app.include_router(datasets.router)
app.include_router(pipelines.router)


@app.get("/api/health", tags=["health"])
async def health() -> JSONResponse:
    """Liveness + database connectivity check.

    Returns HTTP 200 only when the database answers `SELECT 1`; otherwise
    HTTP 503 so Docker health checks and load balancers treat the service as
    unavailable until PostgreSQL is reachable.
    """
    try:
        await ensure_pool()
        async with connection() as conn:
            await conn.fetchval("SELECT 1")
        return JSONResponse({"status": "ok", "database": "up"})
    except Exception as exc:  # noqa: BLE001 — surfaced intentionally
        logger.exception("Health check failed")
        return JSONResponse(
            {"status": "degraded", "database": "down", "detail": str(exc)},
            status_code=503,
        )
