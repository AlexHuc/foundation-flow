"""
Database connection management.

Manages connections to:
- PostgreSQL: Raw data layer
- TimescaleDB: Analytics layer

Uses connection pooling for efficiency.
"""

import os
import asyncpg
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Connection pools
raw_pool: Optional[asyncpg.Pool] = None
analytics_pool: Optional[asyncpg.Pool] = None


async def init_raw_db():
    """Initialize PostgreSQL raw data layer connection pool."""
    global raw_pool
    
    try:
        raw_pool = await asyncpg.create_pool(
            user=os.getenv('POSTGRES_USER', 'airflow'),
            password=os.getenv('POSTGRES_PASSWORD', 'airflow'),
            database=os.getenv('POSTGRES_DB', 'analytics'),
            host=os.getenv('POSTGRES_HOST', 'postgres'),
            port=int(os.getenv('POSTGRES_PORT', 5432)),
            min_size=5,
            max_size=20,
        )
        logger.info("PostgreSQL raw layer pool initialized")
    except Exception as e:
        logger.error(f"Failed to initialize PostgreSQL pool: {str(e)}")
        raise


async def init_analytics_db():
    """Initialize TimescaleDB analytics layer connection pool."""
    global analytics_pool
    
    try:
        analytics_pool = await asyncpg.create_pool(
            user=os.getenv('TIMESCALE_USER', 'postgres'),
            password=os.getenv('TIMESCALE_PASSWORD', 'postgres'),
            database=os.getenv('TIMESCALE_DB', 'analytics_prod'),
            host=os.getenv('TIMESCALE_HOST', 'timescale'),
            port=int(os.getenv('TIMESCALE_PORT', 5433)),
            min_size=5,
            max_size=20,
        )
        logger.info("TimescaleDB analytics layer pool initialized")
    except Exception as e:
        logger.error(f"Failed to initialize TimescaleDB pool: {str(e)}")
        raise


async def close_db():
    """Close all database connections."""
    global raw_pool, analytics_pool
    
    if raw_pool:
        await raw_pool.close()
        logger.info("PostgreSQL pool closed")
    
    if analytics_pool:
        await analytics_pool.close()
        logger.info("TimescaleDB pool closed")


async def get_raw_db():
    """Get connection from PostgreSQL pool."""
    if raw_pool is None:
        raise RuntimeError("Raw database pool not initialized")
    return raw_pool


async def get_analytics_db():
    """Get connection from TimescaleDB pool."""
    if analytics_pool is None:
        raise RuntimeError("Analytics database pool not initialized")
    return analytics_pool


async def get_raw_connection():
    """Get single connection from PostgreSQL pool."""
    pool = await get_raw_db()
    return await pool.acquire()


async def get_analytics_connection():
    """Get single connection from TimescaleDB pool."""
    pool = await get_analytics_db()
    return await pool.acquire()
