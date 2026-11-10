"""Pipeline run status, sourced from landing.pipeline_metadata."""

from fastapi import APIRouter, Query

from ..db import connection
from ..registry import SCHEMA
from ..serialization import rows_to_dicts

router = APIRouter(prefix="/api/pipelines", tags=["pipelines"])


@router.get("")
async def list_pipeline_runs(
    ticker: str | None = Query(default=None),
    status: str | None = Query(default=None),
    pipeline_name: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=1_000),
) -> list[dict]:
    """Recent ingestion runs, most recent first, with optional filters."""
    clauses = ["TRUE"]
    params: list = []
    if ticker is not None:
        params.append(ticker.strip().upper())
        clauses.append(f"ticker = ${len(params)}")
    if status is not None:
        params.append(status)
        clauses.append(f"status = ${len(params)}")
    if pipeline_name is not None:
        params.append(pipeline_name)
        clauses.append(f"pipeline_name = ${len(params)}")
    params.append(limit)

    async with connection() as conn:
        rows = await conn.fetch(
            f"""
            SELECT id, pipeline_name, ticker, status, rows_processed,
                   error_message, started_at, completed_at, created_at
            FROM {SCHEMA}.pipeline_metadata
            WHERE {" AND ".join(clauses)}
            ORDER BY created_at DESC
            LIMIT ${len(params)}
            """,
            *params,
        )
    return rows_to_dicts(rows)
