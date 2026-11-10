"""Async PostgreSQL connection pool (read-only access to the landing schema)."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import asyncpg

from .config import get_settings

_pool: asyncpg.Pool | None = None


async def open_pool() -> None:
    global _pool
    settings = get_settings()
    _pool = await asyncpg.create_pool(
        dsn=settings.dsn,
        min_size=settings.db_pool_min_size,
        max_size=settings.db_pool_max_size,
        # The API is read-only by design; enforce it at the session level too.
        server_settings={"default_transaction_read_only": "on"},
    )


async def close_pool() -> None:
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None


@asynccontextmanager
async def connection() -> AsyncIterator[asyncpg.Connection]:
    if _pool is None:
        raise RuntimeError("Database pool is not initialized")
    async with _pool.acquire() as conn:
        yield conn
