"""Generic per-ticker dataset endpoints, driven by the table registry."""

from datetime import date

from fastapi import APIRouter, HTTPException, Query

from ..db import connection
from ..registry import DATASETS, SCHEMA
from ..serialization import rows_to_dicts
from .companies import normalize_ticker

router = APIRouter(prefix="/api", tags=["datasets"])


@router.get("/datasets")
async def list_datasets() -> list[dict]:
    """Catalog of the datasets exposed by this API."""
    return [
        {"slug": d.slug, "table": f"{SCHEMA}.{d.table}", "description": d.description}
        for d in DATASETS.values()
    ]


@router.get("/companies/{ticker}/datasets/{slug}")
async def get_dataset(
    ticker: str,
    slug: str,
    from_date: date | None = Query(default=None, alias="from"),
    to_date: date | None = Query(default=None, alias="to"),
    limit: int = Query(default=1_000, ge=1, le=10_000),
) -> list[dict]:
    """Rows for one ticker from any registered landing dataset.

    Empty result sets return an empty list — the API never fabricates data.
    """
    dataset = DATASETS.get(slug)
    if dataset is None:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown dataset '{slug}'. See /api/datasets for the catalog.",
        )
    ticker = normalize_ticker(ticker)

    clauses = ["ticker = $1"]
    params: list = [ticker]
    if from_date is not None:
        params.append(from_date)
        clauses.append(f"{dataset.date_column} >= ${len(params)}")
    if to_date is not None:
        params.append(to_date)
        clauses.append(f"{dataset.date_column} <= ${len(params)}")
    params.append(limit)

    async with connection() as conn:
        rows = await conn.fetch(
            f"""
            SELECT * FROM {SCHEMA}.{dataset.table}
            WHERE {" AND ".join(clauses)}
            ORDER BY {dataset.date_column} DESC
            LIMIT ${len(params)}
            """,
            *params,
        )
    return rows_to_dicts(rows)
