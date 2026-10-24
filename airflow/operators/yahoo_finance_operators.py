"""
Custom Airflow Operators for Yahoo Finance Data Ingestion

These operators handle fetching data from Yahoo Finance API and storing
raw responses in PostgreSQL for later transformation by dbt.

Classes:
    - FetchYahooFinancePricesOperator: Fetch OHLCV prices
    - FetchYahooFinanceFundamentalsOperator: Fetch fundamental metrics
    - FetchYahooFinanceDividendsOperator: Fetch dividend history
"""

from airflow.exceptions import AirflowException
from airflow.models import BaseOperator
from psycopg2.extras import execute_values
from typing import Dict, Any
import yfinance as yf
import requests
import logging
import json

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
    
    def __init__(self, ticker: str, postgres_conn_id: str = 'postgres_raw', **kwargs):
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


class FetchYahooFinancePricesOperator(YahooFinanceBaseOperator):
    """
    Fetch OHLCV (Open, High, Low, Close, Volume) data from Yahoo Finance.
    
    This operator:
    - Fetches historical price data for a stock
    - Stores raw response in PostgreSQL
    - Handles idempotency (can be rerun safely)
    - Validates data quality
    
    Example:
        task = FetchYahooFinancePricesOperator(
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
        postgres_conn_id: str = 'postgres_raw',
        **kwargs
    ):
        """
        Initialize prices fetch operator.
        
        Args:
            ticker: Stock ticker (e.g., 'AAPL')
            period: Data period ('5y', '1y', '1mo', '1d')
            interval: Data interval ('1m', '5m', '15m', '1h', '1d', '1wk', '1mo')
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
            df: DataFrame with OHLCV data from yfinance
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
                    int(row['Volume']),
                    float(row.get('Adj Close', row['Close'])),
                    json.dumps(row.to_dict(), default=str),  # Raw response
                ))
            
            # Upsert (insert or update) data - idempotent operation
            query = '''
                INSERT INTO raw.yahoo_prices_raw 
                (ticker, date, open, high, low, close, volume, adj_close, raw_response)
                VALUES %s
                ON CONFLICT (ticker, date) DO UPDATE SET
                    open = EXCLUDED.open,
                    high = EXCLUDED.high,
                    low = EXCLUDED.low,
                    close = EXCLUDED.close,
                    volume = EXCLUDED.volume,
                    adj_close = EXCLUDED.adj_close,
                    raw_response = EXCLUDED.raw_response,
                    updated_at = CURRENT_TIMESTAMP
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


class FetchYahooFinanceFundamentalsOperator(YahooFinanceBaseOperator):
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
        task = FetchYahooFinanceFundamentalsOperator(
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
                INSERT INTO raw.yahoo_fundamentals_raw 
                (ticker, market_cap, pe_ratio, dividend_yield, earnings_per_share,
                 fifty_two_week_high, fifty_two_week_low, average_volume, beta, raw_response)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (ticker) DO UPDATE SET
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