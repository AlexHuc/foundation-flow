"""
Stock API endpoints.

Endpoints:
    GET /: List available stocks
    GET /{ticker}: Get stock metrics
    GET /{ticker}/prices: Get historical prices
    GET /{ticker}/returns: Get return calculations
    GET /search: Search for stocks
"""

from fastapi import APIRouter, HTTPException, Query
from typing import List
import logging
from services.stock_service import (
    get_stock_metrics,
    get_stock_prices,
    get_stock_returns,
    search_stocks,
    get_all_stocks,
)
from models.schemas import StockMetrics, StockPrice, StockReturns
from datetime import date

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("", response_model=List[str], tags=["stocks"])
async def list_stocks():
    """
    Get list of all available stocks.
    
    Returns:
        List of stock ticker symbols
        
    Example:
        GET /api/stocks
        Response: ["AAPL", "MSFT", "GOOGL", ...]
    """
    try:
        stocks = await get_all_stocks()
        return stocks
    except Exception as e:
        logger.error(f"Error listing stocks: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/search", response_model=List[str], tags=["stocks"])
async def search(
    q: str = Query(..., description="Search query (ticker or company name)", min_length=1),
    limit: int = Query(20, ge=1, le=100, description="Maximum results")
):
    """
    Search for stocks by ticker or company name.
    
    Args:
        q: Search query
        limit: Maximum results to return
        
    Returns:
        List of matching tickers
        
    Example:
        GET /api/stocks/search?q=APP&limit=10
        Response: ["AAPL", "APPL", ...]
    """
    try:
        results = await search_stocks(q, limit)
        return results
    except Exception as e:
        logger.error(f"Error searching stocks: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{ticker}", response_model=StockMetrics, tags=["stocks"])
async def get_stock(ticker: str):
    """
    Get latest metrics and fundamentals for a stock.
    
    Args:
        ticker: Stock ticker symbol (e.g., 'AAPL')
        
    Returns:
        StockMetrics with current price, P/E ratio, market cap, etc.
        
    Raises:
        404: Stock not found
        
    Example:
        GET /api/stocks/AAPL
        Response:
        {
            "ticker": "AAPL",
            "current_price": 186.50,
            "market_cap": 2900000000000,
            "pe_ratio": 28.5,
            "beta": 1.2
        }
    """
    try:
        metrics = await get_stock_metrics(ticker.upper())
        
        if metrics is None:
            raise HTTPException(
                status_code=404,
                detail=f"Stock {ticker} not found"
            )
        
        return metrics
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching stock {ticker}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{ticker}/prices", response_model=List[StockPrice], tags=["stocks"])
async def get_prices(
    ticker: str,
    days: int = Query(30, ge=1, le=1000, description="Number of days to fetch"),
    start_date: date = Query(None, description="Start date filter"),
    end_date: date = Query(None, description="End date filter")
):
    """
    Get historical price data for a stock.
    
    Args:
        ticker: Stock ticker symbol
        days: Number of days to fetch (if start/end dates not provided)
        start_date: Optional start date filter
        end_date: Optional end date filter
        
    Returns:
        List of StockPrice objects with OHLCV data
        
    Example:
        GET /api/stocks/AAPL/prices?days=30
        Response: [
            {
                "ticker": "AAPL",
                "date": "2024-01-15",
                "open": 185.50,
                "high": 186.75,
                "low": 185.25,
                "close": 186.50,
                "volume": 45000000
            }
        ]
    """
    try:
        prices = await get_stock_prices(
            ticker.upper(),
            days=days,
            start_date=start_date,
            end_date=end_date
        )
        
        if not prices:
            raise HTTPException(
                status_code=404,
                detail=f"No price data found for {ticker}"
            )
        
        return prices
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching prices for {ticker}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{ticker}/returns", response_model=List[StockReturns], tags=["stocks"])
async def get_returns(
    ticker: str,
    days: int = Query(30, ge=1, le=1000, description="Number of days to fetch")
):
    """
    Get return calculations for different periods.
    
    Args:
        ticker: Stock ticker symbol
        days: Number of days to fetch
        
    Returns:
        List of StockReturns with daily, weekly, monthly, annual returns
        
    Example:
        GET /api/stocks/AAPL/returns?days=30
        Response: [
            {
                "ticker": "AAPL",
                "date": "2024-01-15",
                "daily_return": 0.0027,
                "weekly_return": 0.0156,
                "monthly_return": 0.0842,
                "annual_return": 0.487
            }
        ]
    """
    try:
        returns = await get_stock_returns(ticker.upper(), days=days)
        
        if not returns:
            raise HTTPException(
                status_code=404,
                detail=f"No return data found for {ticker}"
            )
        
        return returns
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching returns for {ticker}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
