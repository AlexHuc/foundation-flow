"""
Pydantic models for request/response validation and documentation.

Classes:
    - StockPrice: Individual price data point
    - StockMetrics: Latest stock metrics and fundamentals
    - StockReturns: Return calculations for different periods
    - StockDetail: Complete stock information
"""

from pydantic import BaseModel, Field
from datetime import date, datetime
from typing import Optional, List


class StockPrice(BaseModel):
    """Historical stock price data."""
    
    ticker: str = Field(..., description="Stock ticker symbol")
    date: date = Field(..., description="Trading date")
    open: float = Field(..., description="Opening price", ge=0)
    high: float = Field(..., description="Daily high price", ge=0)
    low: float = Field(..., description="Daily low price", ge=0)
    close: float = Field(..., description="Closing price", ge=0)
    volume: int = Field(..., description="Trading volume", ge=0)
    adj_close: Optional[float] = Field(None, description="Adjusted close price")
    daily_return: Optional[float] = Field(None, description="Daily percentage return")
    volatility_20d: Optional[float] = Field(None, description="20-day volatility")
    volatility_252d: Optional[float] = Field(None, description="252-day volatility")
    
    class Config:
        json_schema_extra = {
            "example": {
                "ticker": "AAPL",
                "date": "2024-01-15",
                "open": 185.50,
                "high": 186.75,
                "low": 185.25,
                "close": 186.50,
                "volume": 45000000,
                "adj_close": 186.50,
                "daily_return": 0.0027,
                "volatility_20d": 0.156,
                "volatility_252d": 0.203
            }
        }


class StockMetrics(BaseModel):
    """Latest stock metrics and fundamental data."""
    
    ticker: str = Field(..., description="Stock ticker symbol")
    current_price: float = Field(..., description="Current price", ge=0)
    market_cap: Optional[int] = Field(None, description="Market capitalization")
    pe_ratio: Optional[float] = Field(None, description="Price-to-earnings ratio")
    dividend_yield: Optional[float] = Field(None, description="Dividend yield percentage")
    earnings_per_share: Optional[float] = Field(None, description="EPS")
    fifty_two_week_high: Optional[float] = Field(None, description="52-week high")
    fifty_two_week_low: Optional[float] = Field(None, description="52-week low")
    fifty_two_week_position_pct: Optional[float] = Field(None, description="Position between 52w high/low")
    beta: Optional[float] = Field(None, description="Beta (systematic risk)")
    daily_return: Optional[float] = Field(None, description="Today's return")
    annual_return: Optional[float] = Field(None, description="Annual return")
    volatility_20d: Optional[float] = Field(None, description="20-day volatility")
    volatility_252d: Optional[float] = Field(None, description="252-day volatility")
    updated_at: datetime = Field(..., description="Last update timestamp")
    
    class Config:
        json_schema_extra = {
            "example": {
                "ticker": "AAPL",
                "current_price": 186.50,
                "market_cap": 2900000000000,
                "pe_ratio": 28.5,
                "dividend_yield": 0.004,
                "beta": 1.2,
                "fifty_two_week_high": 199.62,
                "fifty_two_week_low": 124.17,
                "fifty_two_week_position_pct": 55.2,
                "annual_return": 0.487,
                "volatility_252d": 0.203,
                "updated_at": "2024-01-15T20:30:00Z"
            }
        }


class StockReturns(BaseModel):
    """Return calculations for different periods."""
    
    ticker: str = Field(..., description="Stock ticker symbol")
    date: date = Field(..., description="Date")
    daily_return: Optional[float] = Field(None, description="Daily return")
    weekly_return: Optional[float] = Field(None, description="Weekly return")
    monthly_return: Optional[float] = Field(None, description="Monthly return")
    annual_return: Optional[float] = Field(None, description="Annual return")
    
    class Config:
        json_schema_extra = {
            "example": {
                "ticker": "AAPL",
                "date": "2024-01-15",
                "daily_return": 0.0027,
                "weekly_return": 0.0156,
                "monthly_return": 0.0842,
                "annual_return": 0.487
            }
        }


class StockDetail(BaseModel):
    """Complete stock information."""
    
    ticker: str = Field(..., description="Stock ticker symbol")
    metrics: StockMetrics = Field(..., description="Current metrics")
    latest_prices: List[StockPrice] = Field(..., description="Last 30 trading days")
    description: Optional[str] = Field(None, description="Company description")
    
    class Config:
        json_schema_extra = {
            "example": {
                "ticker": "AAPL",
                "metrics": {
                    "ticker": "AAPL",
                    "current_price": 186.50,
                    "market_cap": 2900000000000
                },
                "latest_prices": [
                    {
                        "ticker": "AAPL",
                        "date": "2024-01-15",
                        "close": 186.50
                    }
                ]
            }
        }


class Error(BaseModel):
    """Error response."""
    
    detail: str = Field(..., description="Error message")
    status_code: int = Field(..., description="HTTP status code")
    
    class Config:
        json_schema_extra = {
            "example": {
                "detail": "Stock INVALID not found",
                "status_code": 404
            }
        }
