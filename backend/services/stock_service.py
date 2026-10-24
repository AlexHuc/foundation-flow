"""
Stock service layer - business logic for stock queries.

Functions:
    - get_stock_metrics(): Fetch latest stock metrics
    - get_stock_prices(): Fetch historical prices
    - get_stock_returns(): Fetch return calculations
    - search_stocks(): Search for stocks
"""

import logging
from datetime import date, datetime, timedelta
from typing import List, Optional
from db.connection import get_analytics_connection, get_raw_connection
from models.schemas import StockMetrics, StockPrice, StockReturns

logger = logging.getLogger(__name__)


async def get_stock_metrics(ticker: str) -> Optional[StockMetrics]:
    """
    Fetch latest metrics and fundamentals for a stock.
    
    Args:
        ticker: Stock ticker symbol
        
    Returns:
        StockMetrics object or None if not found
        
    Raises:
        Exception: Database connection errors
    """
    try:
        conn = await get_analytics_connection()
        
        query = """
            SELECT
                ticker,
                current_price,
                market_cap,
                pe_ratio,
                dividend_yield,
                earnings_per_share,
                fifty_two_week_high,
                fifty_two_week_low,
                fifty_two_week_position_pct,
                beta,
                daily_return,
                annual_return,
                volatility_20d,
                volatility_252d,
                updated_at
            FROM marts.fact_stock_metrics
            WHERE ticker = $1
        """
        
        row = await conn.fetchrow(query, ticker.upper())
        await conn.close()
        
        if not row:
            logger.warning(f"Stock {ticker} not found in metrics")
            return None
        
        return StockMetrics(**dict(row))
        
    except Exception as e:
        logger.error(f"Error fetching metrics for {ticker}: {str(e)}")
        raise


async def get_stock_prices(
    ticker: str,
    days: int = 30,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None
) -> List[StockPrice]:
    """
    Fetch historical prices for a stock.
    
    Args:
        ticker: Stock ticker symbol
        days: Number of days to fetch (if start_date/end_date not provided)
        start_date: Optional start date filter
        end_date: Optional end date filter
        
    Returns:
        List of StockPrice objects
        
    Raises:
        Exception: Database connection errors
    """
    try:
        conn = await get_analytics_connection()
        
        # Calculate date range
        if end_date is None:
            end_date = date.today()
        if start_date is None:
            start_date = end_date - timedelta(days=days)
        
        query = """
            SELECT
                ticker,
                date,
                open,
                high,
                low,
                close,
                volume,
                adj_close,
                daily_return,
                volatility_20d,
                volatility_252d
            FROM marts.fact_stock_prices
            WHERE ticker = $1
              AND date >= $2
              AND date <= $3
            ORDER BY date DESC
            LIMIT 500
        """
        
        rows = await conn.fetch(query, ticker.upper(), start_date, end_date)
        await conn.close()
        
        prices = [StockPrice(**dict(row)) for row in rows]
        logger.info(f"Fetched {len(prices)} price records for {ticker}")
        
        return prices
        
    except Exception as e:
        logger.error(f"Error fetching prices for {ticker}: {str(e)}")
        raise


async def get_stock_returns(
    ticker: str,
    days: int = 30
) -> List[StockReturns]:
    """
    Fetch return calculations for a stock.
    
    Args:
        ticker: Stock ticker symbol
        days: Number of days to fetch
        
    Returns:
        List of StockReturns objects
        
    Raises:
        Exception: Database connection errors
    """
    try:
        conn = await get_analytics_connection()
        
        start_date = date.today() - timedelta(days=days)
        
        query = """
            SELECT
                ticker,
                date,
                daily_return,
                weekly_return,
                monthly_return,
                annual_return
            FROM intermediate.int_returns
            WHERE ticker = $1
              AND date >= $2
            ORDER BY date DESC
            LIMIT 500
        """
        
        rows = await conn.fetch(query, ticker.upper(), start_date)
        await conn.close()
        
        returns = [StockReturns(**dict(row)) for row in rows]
        logger.info(f"Fetched {len(returns)} return records for {ticker}")
        
        return returns
        
    except Exception as e:
        logger.error(f"Error fetching returns for {ticker}: {str(e)}")
        raise


async def search_stocks(query: str = "", limit: int = 20) -> List[str]:
    """
    Search for stocks by ticker or company name.
    
    Args:
        query: Search query (ticker prefix or company name)
        limit: Maximum results to return
        
    Returns:
        List of ticker symbols
        
    Raises:
        Exception: Database connection errors
    """
    try:
        conn = await get_analytics_connection()
        
        search_query = """
            SELECT DISTINCT ticker
            FROM marts.fact_stock_metrics
            WHERE ticker ILIKE $1
               OR name ILIKE $2
            ORDER BY ticker
            LIMIT $3
        """
        
        search_pattern = f"{query.upper()}%"
        name_pattern = f"%{query}%"
        
        rows = await conn.fetch(search_query, search_pattern, name_pattern, limit)
        await conn.close()
        
        tickers = [row['ticker'] for row in rows]
        logger.info(f"Search for '{query}' returned {len(tickers)} results")
        
        return tickers
        
    except Exception as e:
        logger.error(f"Error searching stocks: {str(e)}")
        raise


async def get_all_stocks() -> List[str]:
    """
    Get list of all available stocks.
    
    Returns:
        List of all ticker symbols
        
    Raises:
        Exception: Database connection errors
    """
    try:
        conn = await get_analytics_connection()
        
        query = """
            SELECT DISTINCT ticker
            FROM marts.fact_stock_metrics
            ORDER BY ticker
        """
        
        rows = await conn.fetch(query)
        await conn.close()
        
        tickers = [row['ticker'] for row in rows]
        logger.info(f"Retrieved {len(tickers)} available stocks")
        
        return tickers
        
    except Exception as e:
        logger.error(f"Error fetching all stocks: {str(e)}")
        raise
