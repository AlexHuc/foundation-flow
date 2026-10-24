"""
Foundation Flow - FastAPI Backend

REST API for serving stock analytics data.
Connects to PostgreSQL (raw) and TimescaleDB (analytics) layers.

Endpoints:
    GET /: Health check
    GET /docs: Interactive API documentation
    GET /stocks/{ticker}: Get stock details
    GET /stocks/{ticker}/prices: Get historical prices
    GET /stocks/{ticker}/metrics: Get latest metrics
    GET /stocks/{ticker}/returns: Get return calculations
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
import logging
import os
from contextlib import asynccontextmanager

# Import routers
from api import stocks

# Configure logging
logging.basicConfig(level=os.getenv('LOG_LEVEL', 'INFO'))
logger = logging.getLogger(__name__)

# Lifespan context for startup/shutdown
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle startup and shutdown events."""
    logger.info("Starting Foundation Flow FastAPI Backend")
    yield
    logger.info("Shutting down FastAPI Backend")

# Create FastAPI app
app = FastAPI(
    title="Foundation Flow API",
    description="Stock analytics API - Yahoo Finance data",
    version="1.0.0",
    lifespan=lifespan,
)

# Configure CORS for frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(stocks.router, prefix="/api/stocks", tags=["stocks"])


@app.get("/", tags=["health"])
async def health_check():
    """
    Health check endpoint.
    
    Returns:
        dict: Status information
    """
    return {
        "status": "healthy",
        "service": "Foundation Flow API",
        "version": "1.0.0"
    }


@app.get("/health", tags=["health"])
async def detailed_health():
    """
    Detailed health check including database connectivity.
    
    Returns:
        dict: Detailed health status
    """
    try:
        from db import get_raw_db, get_analytics_db
        
        # Check raw database
        raw_conn = await get_raw_db()
        await raw_conn.execute("SELECT 1")
        
        # Check analytics database
        analytics_conn = await get_analytics_db()
        await analytics_conn.execute("SELECT 1")
        
        return {
            "status": "healthy",
            "databases": {
                "raw": "connected",
                "analytics": "connected"
            }
        }
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        raise HTTPException(status_code=503, detail="Database connection failed")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=os.getenv("FASTAPI_HOST", "0.0.0.0"),
        port=int(os.getenv("FASTAPI_PORT", 8000)),
        reload=os.getenv("FASTAPI_ENV") == "development",
        log_level=os.getenv("LOG_LEVEL", "info").lower(),
    )
