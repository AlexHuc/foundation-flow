"""Company-centric endpoints: list, profile, prices, financial statements."""

from datetime import date

from fastapi import APIRouter, HTTPException, Query

from ..db import connection
from ..registry import SCHEMA, STATEMENT_TABLES
from ..serialization import row_to_dict, rows_to_dicts

router = APIRouter(prefix="/api/companies", tags=["companies"])

MAX_LIMIT = 10_000


def normalize_ticker(ticker: str) -> str:
    ticker = ticker.strip().upper()
    if not ticker or len(ticker) > 10:
        raise HTTPException(status_code=422, detail="Invalid ticker symbol")
    return ticker


@router.get("")
async def list_companies() -> list[dict]:
    """Tickers present in the landing data, with their latest info snapshot."""
    async with connection() as conn:
        rows = await conn.fetch(
            f"""
            SELECT DISTINCT ON (i.ticker)
                   i.ticker,
                   i.date          AS info_date,
                   i.market_cap,
                   i.pe_ratio,
                   i.earnings_per_share,
                   f.last_price,
                   f.currency,
                   f.exchange
            FROM {SCHEMA}.yahoo_info i
            LEFT JOIN LATERAL (
                SELECT last_price, currency, exchange
                FROM {SCHEMA}.yahoo_fast_info f
                WHERE f.ticker = i.ticker
                ORDER BY f.date DESC
                LIMIT 1
            ) f ON TRUE
            ORDER BY i.ticker, i.date DESC
            """
        )
    return rows_to_dicts(rows)


@router.get("/{ticker}")
async def get_company(ticker: str) -> dict:
    """Latest known profile for one ticker: info + fast_info + last close."""
    ticker = normalize_ticker(ticker)
    async with connection() as conn:
        info = await conn.fetchrow(
            f"""
            SELECT * FROM {SCHEMA}.yahoo_info
            WHERE ticker = $1 ORDER BY date DESC LIMIT 1
            """,
            ticker,
        )
        fast = await conn.fetchrow(
            f"""
            SELECT * FROM {SCHEMA}.yahoo_fast_info
            WHERE ticker = $1 ORDER BY date DESC LIMIT 1
            """,
            ticker,
        )
        last_bar = await conn.fetchrow(
            f"""
            SELECT date, close, adj_close, volume
            FROM {SCHEMA}.yahoo_history
            WHERE ticker = $1 ORDER BY date DESC LIMIT 1
            """,
            ticker,
        )
    if info is None and fast is None and last_bar is None:
        raise HTTPException(status_code=404, detail=f"No landing data for ticker {ticker}")
    return {
        "ticker": ticker,
        "info": row_to_dict(info) if info else None,
        "fast_info": row_to_dict(fast) if fast else None,
        "last_bar": row_to_dict(last_bar) if last_bar else None,
    }


@router.get("/{ticker}/prices")
async def get_prices(
    ticker: str,
    from_date: date | None = Query(default=None, alias="from"),
    to_date: date | None = Query(default=None, alias="to"),
    limit: int = Query(default=5_000, ge=1, le=MAX_LIMIT),
) -> list[dict]:
    """Daily OHLCV history, optionally bounded by a date range."""
    ticker = normalize_ticker(ticker)
    clauses = ["ticker = $1"]
    params: list = [ticker]
    if from_date is not None:
        params.append(from_date)
        clauses.append(f"date >= ${len(params)}")
    if to_date is not None:
        params.append(to_date)
        clauses.append(f"date <= ${len(params)}")
    params.append(limit)
    async with connection() as conn:
        rows = await conn.fetch(
            f"""
            SELECT ticker, date, open, high, low, close, adj_close, volume, dividend, split
            FROM {SCHEMA}.yahoo_history
            WHERE {" AND ".join(clauses)}
            ORDER BY date ASC
            LIMIT ${len(params)}
            """,
            *params,
        )
    return rows_to_dicts(rows)


@router.get("/{ticker}/financials/{statement}")
async def get_financials(
    ticker: str,
    statement: str,
    period: str = Query(default="annual", pattern="^(annual|quarterly|ttm)$"),
    limit: int = Query(default=40, ge=1, le=400),
) -> list[dict]:
    """Income statement, balance sheet, or cash flow rows for one ticker."""
    ticker = normalize_ticker(ticker)
    table = STATEMENT_TABLES.get((statement, period))
    if table is None:
        valid = sorted({s for s, _ in STATEMENT_TABLES})
        raise HTTPException(
            status_code=404,
            detail=f"Unknown statement '{statement}'. Valid: {', '.join(valid)}",
        )
    async with connection() as conn:
        rows = await conn.fetch(
            f"""
            SELECT * FROM {SCHEMA}.{table}
            WHERE ticker = $1
            ORDER BY date DESC
            LIMIT $2
            """,
            ticker,
            limit,
        )
    return rows_to_dicts(rows)
