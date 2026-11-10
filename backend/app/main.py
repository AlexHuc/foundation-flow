"""Foundation Flow API — read-only access to the PostgreSQL landing schema."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .db import close_pool, connection, open_pool
from .routes import companies, datasets, pipelines

logger = logging.getLogger("foundation_flow.api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    await open_pool()
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
async def health() -> dict:
    """Liveness + database connectivity check."""
    try:
        async with connection() as conn:
            await conn.fetchval("SELECT 1")
        return {"status": "ok", "database": "up"}
    except Exception as exc:  # noqa: BLE001 — surfaced intentionally
        logger.exception("Health check failed")
        return {"status": "degraded", "database": "down", "detail": str(exc)}
