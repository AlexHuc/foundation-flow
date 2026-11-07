"""
Custom Airflow Operators for Yahoo Finance Data Ingestion

These operators handle fetching data from Yahoo Finance API and storing
landing responses in PostgreSQL for later transformation by dbt.

Classes:
    - FetchYahooFinanceHistory: Fetch history proces
    - FetchYahooFinanceTickerInfo: Fetch fundamental metrics
    - FetchYahooFinanceTickerFastInfo: Fetch info metrics
    - FetchYahooFinanceIncomeStatement: Fetch income statement
"""

from airflow.exceptions import AirflowException
from airflow.models import BaseOperator
from psycopg2.extras import execute_values
from typing import Dict, Any
from psycopg2 import sql
import yfinance as yf
import pandas as pd
import datetime
import requests
import logging
import json
import re

logger = logging.getLogger(__name__)

class YahooFinanceBaseOperator(BaseOperator):
    """
    Base operator for Yahoo Finance data fetching.
    
    Provides common functionality for all Yahoo Finance operators:
    - Connection management
    - Error handling and retries
    - Logging
    - Data validation
    """
    
    def __init__(self, ticker: str, postgres_conn_id: str = 'postgres_landing', **kwargs):
        """
        Initialize operator.
        
        Args:
            ticker: Stock ticker symbol (e.g., 'AAPL')
            postgres_conn_id: Airflow PostgreSQL connection ID
            **kwargs: Additional Airflow operator arguments
        """
        super().__init__(**kwargs)
        self.ticker = ticker
        self.postgres_conn_id = postgres_conn_id

    def create_yahoo_session(self):
        session = requests.Session()

        session.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/126.0.0.0 Safari/537.36"
            )
        })

        return session

    def get_db_connection(self):
        """Get PostgreSQL connection from Airflow."""
        from airflow.providers.postgres.hooks.postgres import PostgresHook
        hook = PostgresHook(postgres_conn_id=self.postgres_conn_id)
        return hook.get_conn()
    
    def execute_query(self, query: str, params: tuple = None):
        """
        Execute a query in PostgreSQL.
        
        Args:
            query: SQL query string
            params: Query parameters
        """
        conn = self.get_db_connection()
        cursor = conn.cursor()
        try:
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            conn.commit()
            logger.info(f"Query executed successfully for {self.ticker}")
        except Exception as e:
            conn.rollback()
            logger.error(f"Query execution failed for {self.ticker}: {str(e)}")
            raise
        finally:
            cursor.close()
            conn.close()


class FetchYahooFinanceHistory(YahooFinanceBaseOperator):
    """
    Fetch History OHLCV (Open, High, Low, Close, Adj Close, Volume, Dividends, Stock Splits)

    This operator:
    - Fetches historical price data for a stock
    - Stores raw response in PostgreSQL landing layer
    - Handles idempotency (can be rerun safely)
    - Validates data quality
    
    Example:
        task = FetchYahooFinanceHistory(
            task_id='fetch_aapl',
            ticker='AAPL',
            session=session_dict,
            period='1d',
            interval='1d'
        )
    """
    
    def __init__(
        self,
        ticker: str,
        period: str = '5y',
        interval: str = '1d',
        postgres_conn_id: str = 'postgres_landing',
        **kwargs
    ):
        """
        Initialize prices fetch operator.
        
        Args:
            ticker: Stock ticker (e.g., 'AAPL')
            period: Data period ('1d', '5d', '1mo', '3mo', '6mo', '1y', '2y', '5y', '10y', 'ytd', 'max')
            interval: Data interval ('1m', '2m', '5m', '15m', '30m', '60m', '90m' '1h', '1d', '1wk', '1mo', '3mo')
            postgres_conn_id: Airflow PostgreSQL connection ID
        """
        super().__init__(ticker=ticker, postgres_conn_id=postgres_conn_id, **kwargs)
        self.period = period
        self.interval = interval
        
    def execute(self, context):
        """
        Main execution method.
        
        Steps:
        1. Fetch data from Yahoo Finance
        2. Validate data
        3. Store in PostgreSQL raw layer
        4. Log metrics
        """
        logger.info(f"Fetching prices for {self.ticker} (period={self.period}, interval={self.interval})")
        
        try:
            # Fetch from Yahoo Finance
            ticker_obj = yf.Ticker(self.ticker)
            df = ticker_obj.history(period=self.period, interval=self.interval)
            
            if df.empty:
                logger.warning(f"No data returned for {self.ticker}")
                return {'status': 'no_data', 'ticker': self.ticker}
            
            # Validate data
            if len(df) == 0:
                raise AirflowException(f"No price data received for {self.ticker}")
            
            logger.info(f"Fetched {len(df)} price records for {self.ticker}")
            
            # Store in PostgreSQL
            self._store_prices_in_postgres(df)
            
            return {
                'status': 'success',
                'ticker': self.ticker,
                'records_inserted': len(df)
            }
            
        except Exception as e:
            logger.error(f"Error fetching prices for {self.ticker}: {str(e)}")
            raise AirflowException(f"Failed to fetch prices for {self.ticker}: {str(e)}")
    
    def _store_prices_in_postgres(self, df):
        """
        Store price data in PostgreSQL raw layer.
        
        Args:
            df: DataFrame with history OHLCV data from yfinance
        """
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        try:
            # Prepare data for insertion
            rows = []
            for date, row in df.iterrows():
                rows.append((
                    self.ticker,
                    date.date(),
                    float(row['Open']),
                    float(row['High']),
                    float(row['Low']),
                    float(row['Close']),
                    float(row.get('Adj Close', row['Close'])),
                    int(row['Volume']),
                    float(row.get('Dividends', 0.0)),
                    float(row.get('Stock Splits', 0.0))
                ))
            
            # Upsert (insert or update) data - idempotent operation
            query = '''
                INSERT INTO landing.yahoo_history (
                    ticker, date, open, high, low, close,
                    adj_close, volume, dividend, split
                )
                VALUES %s
                ON CONFLICT (ticker, date) DO UPDATE SET
                    open = EXCLUDED.open,
                    high = EXCLUDED.high,
                    low = EXCLUDED.low,
                    close = EXCLUDED.close,
                    adj_close = EXCLUDED.adj_close,
                    volume = EXCLUDED.volume,
                    dividend = EXCLUDED.dividend,
                    split = EXCLUDED.split,
                    updated_at = CURRENT_TIMESTAMP;
            '''
            
            execute_values(cursor, query, rows)
            conn.commit()
            logger.info(f"Inserted {len(rows)} price records for {self.ticker}")
            
        except Exception as e:
            conn.rollback()
            logger.error(f"Error storing prices: {str(e)}")
            raise
        finally:
            cursor.close()
            conn.close()


class FetchYahooFinanceTickerInfo(YahooFinanceBaseOperator):
    """
    Fetch fundamental metrics from Yahoo Finance.
    
    Fetches:
    - Market cap
    - P/E ratio
    - Dividend yield
    - Earnings per share
    - 52-week high/low
    - Beta
    - Average volume
    
    Example:
        task = FetchYahooFinanceTickerInfo(
            task_id='fetch_fundamentals_aapl',
            ticker='AAPL'
        )
    """
    
    def execute(self, context):
        """Fetch and store fundamental metrics."""
        logger.info(f"Fetching fundamentals for {self.ticker}")
        
        try:
            ticker_obj = yf.Ticker(self.ticker)
            info = ticker_obj.info
            
            if not info:
                logger.warning(f"No fundamental data returned for {self.ticker}")
                return {'status': 'no_data', 'ticker': self.ticker}
            
            # Store in PostgreSQL
            self._store_fundamentals_in_postgres(info)
            
            return {
                'status': 'success',
                'ticker': self.ticker,
                'metrics_retrieved': len(info)
            }
            
        except Exception as e:
            logger.error(f"Error fetching fundamentals for {self.ticker}: {str(e)}")
            raise AirflowException(f"Failed to fetch fundamentals for {self.ticker}: {str(e)}")
    
    def _store_fundamentals_in_postgres(self, info: Dict[str, Any]):
        """
        Store fundamental metrics in PostgreSQL.
        
        Args:
            info: Dictionary of fundamental metrics from yfinance
        """
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        try:
            query = '''
                INSERT INTO landing.yahoo_info
                (ticker, date, market_cap, pe_ratio, dividend_yield, earnings_per_share,
                 fifty_two_week_high, fifty_two_week_low, average_volume, beta, raw_response)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (ticker, date) DO UPDATE SET
                    market_cap = EXCLUDED.market_cap,
                    pe_ratio = EXCLUDED.pe_ratio,
                    dividend_yield = EXCLUDED.dividend_yield,
                    earnings_per_share = EXCLUDED.earnings_per_share,
                    fifty_two_week_high = EXCLUDED.fifty_two_week_high,
                    fifty_two_week_low = EXCLUDED.fifty_two_week_low,
                    average_volume = EXCLUDED.average_volume,
                    beta = EXCLUDED.beta,
                    raw_response = EXCLUDED.raw_response,
                    updated_at = CURRENT_TIMESTAMP
            '''
            
            cursor.execute(query, (
                self.ticker,
                datetime.date.today(),
                info.get('marketCap'),
                info.get('trailingPE'),
                info.get('dividendYield'),
                info.get('trailingEps'),
                info.get('fiftyTwoWeekHigh'),
                info.get('fiftyTwoWeekLow'),
                info.get('averageVolume'),
                info.get('beta'),
                json.dumps(info, default=str),
            ))
            
            conn.commit()
            logger.info(f"Inserted fundamental metrics for {self.ticker}")
            
        except Exception as e:
            conn.rollback()
            logger.error(f"Error storing fundamentals: {str(e)}")
            raise
        finally:
            cursor.close()
            conn.close()


class FetchYahooFinanceTickerFastInfo(YahooFinanceBaseOperator):
    """
    Fetch fundamental metrics from Yahoo Finance.
    
    Fetches:
    - Currency
    - Day high/low
    - Exchange
    - Average prices
    - Market cap
    - Previous close
    - Volume metrics
    - Timezone
    - Year change/high/low
    
    Example:
        task = FetchYahooFinanceTickerFastInfo(
            task_id='fetch_fast_info_aapl',
            ticker='AAPL'
        )
    """
    
    def execute(self, context):
        """Fetch and store fundamental metrics."""
        logger.info(f"Fetching fast info for {self.ticker}")
        
        try:
            ticker_obj = yf.Ticker(self.ticker)
            fast_info = ticker_obj.fast_info
            
            if not fast_info:
                logger.warning(f"No fast info data returned for {self.ticker}")
                return {'status': 'no_data', 'ticker': self.ticker}
            
            # Store in PostgreSQL
            self._store_fast_info_in_postgres(fast_info)
            
            return {
                'status': 'success',
                'ticker': self.ticker,
                'metrics_retrieved': len(dict(fast_info))
            }
            
        except Exception as e:
            logger.error(f"Error fetching fast info for {self.ticker}: {str(e)}")
            raise AirflowException(f"Failed to fetch fast info for {self.ticker}: {str(e)}")
    
    def _store_fast_info_in_postgres(self, fast_info: Dict[str, Any]):
        """
        Store fast info metrics in PostgreSQL.
        
        Args:
            fast_info: Dictionary of fast info metrics from yfinance
        """
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        try:
            query = '''
                INSERT INTO landing.yahoo_fast_info
                (ticker, date, currency, day_high, day_low, exchange, fifty_day_average, 
                 last_price, last_volume, market_cap, open, previous_close, quote_type, 
                 regular_market_previous_close, shares, ten_day_average_volume, 
                 three_month_average_volume, timezone, two_hundred_day_average, year_change, 
                 year_high, year_low)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (ticker, date) DO UPDATE SET
                    currency = EXCLUDED.currency,
                    day_high = EXCLUDED.day_high,
                    day_low = EXCLUDED.day_low,
                    exchange = EXCLUDED.exchange,
                    fifty_day_average = EXCLUDED.fifty_day_average,
                    last_price = EXCLUDED.last_price,
                    last_volume = EXCLUDED.last_volume,
                    market_cap = EXCLUDED.market_cap,
                    open = EXCLUDED.open,
                    previous_close = EXCLUDED.previous_close,
                    quote_type = EXCLUDED.quote_type,
                    regular_market_previous_close = EXCLUDED.regular_market_previous_close,
                    shares = EXCLUDED.shares,
                    ten_day_average_volume = EXCLUDED.ten_day_average_volume,
                    three_month_average_volume = EXCLUDED.three_month_average_volume,
                    timezone = EXCLUDED.timezone,
                    two_hundred_day_average = EXCLUDED.two_hundred_day_average,
                    year_change = EXCLUDED.year_change,
                    year_high = EXCLUDED.year_high,
                    year_low = EXCLUDED.year_low,
                    updated_at = CURRENT_TIMESTAMP
            '''
            
            cursor.execute(query, (
                self.ticker,
                datetime.date.today(),
                fast_info.get('currency'),
                fast_info.get('dayHigh'),
                fast_info.get('dayLow'),
                fast_info.get('exchange'),
                fast_info.get('fiftyDayAverage'),
                fast_info.get('lastPrice'),
                fast_info.get('lastVolume'),
                fast_info.get('marketCap'),
                fast_info.get('open'),
                fast_info.get('previousClose'),
                fast_info.get('quoteType'),
                fast_info.get('regularMarketPreviousClose'),
                fast_info.get('shares'),
                fast_info.get('tenDayAverageVolume'),
                fast_info.get('threeMonthAverageVolume'),
                fast_info.get('timezone'),
                fast_info.get('twoHundredDayAverage'),
                fast_info.get('yearChange'),
                fast_info.get('yearHigh'),
                fast_info.get('yearLow'),
            ))
            
            conn.commit()
            logger.info(f"Inserted fast info metrics for {self.ticker}")
            
        except Exception as e:
            conn.rollback()
            logger.error(f"Error storing fast info: {str(e)}")
            raise
        finally:
            cursor.close()
            conn.close()


class FetchYahooFinanceIncomeStatement(YahooFinanceBaseOperator):
    """Fetch Yahoo Finance income statement data and store it in PostgreSQL."""

    def execute(self, context):
        """Fetch and store income statement data."""
        logger.info("Fetching income statement for %s", self.ticker)

        try:
            income_stmt = yf.Ticker(self.ticker).income_stmt

            if income_stmt is None or income_stmt.empty:
                logger.warning("No income statement data for %s", self.ticker)
                return {"status": "no_data", "ticker": self.ticker}

            periods_stored = self._store_income_statement_in_postgres(income_stmt)

            return {
                "status": "success",
                "ticker": self.ticker,
                "metrics_retrieved": len(income_stmt.index),
                "periods_stored": periods_stored,
            }

        except Exception as e:
            logger.exception("Error fetching income statement for %s", self.ticker)
            raise AirflowException(
                f"Failed to fetch income statement for {self.ticker}: {e}"
            ) from e

    def _store_income_statement_in_postgres(self, income_stmt):
        """Transpose, normalize, and upsert income statement data."""
        conn = self.get_db_connection()

        try:
            with conn.cursor() as cursor:
                # Read the existing table columns to keep inserts compatible
                # with the fixed PostgreSQL schema.
                cursor.execute(
                    """
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_schema = %s
                      AND table_name = %s
                    """,
                    ("landing", "yahoo_income_statement"),
                )
                db_columns = {row[0] for row in cursor.fetchall()}

                if not db_columns:
                    raise ValueError(
                        "Table landing.yahoo_income_statement was not found "
                        "or has no columns."
                    )

                # Yahoo has metrics in rows and reporting dates in columns.
                periods = income_stmt.T.copy()

                # Normalize metric names, e.g. Total Revenue -> total_revenue.
                def normalize(name):
                    return re.sub(r"_+", "_", re.sub(
                        r"[^a-zA-Z0-9]+", "_", str(name).strip().lower()
                    )).strip("_")

                periods.columns = [normalize(col) for col in periods.columns]

                # Insert only metrics that have matching columns in the table.
                metric_columns = [
                    col for col in periods.columns
                    if col in db_columns and col not in {"ticker", "date", "updated_at"}
                ]

                skipped = [
                    str(col) for col in income_stmt.index
                    if normalize(col) not in metric_columns
                ]

                if skipped:
                    logger.warning(
                        "Skipping metrics without matching database columns for %s: %s",
                        self.ticker,
                        ", ".join(skipped),
                    )

                if not metric_columns:
                    logger.warning(
                        "No matching income statement columns found for %s",
                        self.ticker,
                    )
                    return 0

                periods = periods[metric_columns]
                rows = []

                for period, values in periods.iterrows():
                    # Convert reporting period safely; don't use Timestamp.replace().
                    period_date = pd.Timestamp(period).date()
                    row = [self.ticker, period_date]

                    for value in values:
                        if pd.isna(value):
                            row.append(None)
                        elif hasattr(value, "item"):
                            row.append(value.item())
                        else:
                            row.append(value)

                    rows.append(tuple(row))

                if not rows:
                    return 0

                columns = ["ticker", "date"] + metric_columns

                query = sql.SQL("""
                    INSERT INTO {}.{} ({})
                    VALUES %s
                    ON CONFLICT (ticker, date) DO UPDATE SET
                        {},
                        ingested_at = CURRENT_TIMESTAMP,
                        updated_at = CURRENT_TIMESTAMP
                """).format(
                    sql.Identifier("landing"),
                    sql.Identifier("yahoo_income_statement"),
                    sql.SQL(", ").join(map(sql.Identifier, columns)),
                    sql.SQL(", ").join(
                        sql.SQL("{} = EXCLUDED.{}").format(
                            sql.Identifier(col),
                            sql.Identifier(col),
                        )
                        for col in metric_columns
                    ),
                )

                execute_values(
                    cursor,
                    query.as_string(conn),
                    rows,
                    page_size=100,
                )

            conn.commit()
            logger.info(
                "Stored %d income statement periods for %s",
                len(rows),
                self.ticker,
            )
            return len(rows)

        except Exception:
            conn.rollback()
            logger.exception(
                "Error storing income statement for %s",
                self.ticker,
            )
            raise

        finally:
            conn.close()