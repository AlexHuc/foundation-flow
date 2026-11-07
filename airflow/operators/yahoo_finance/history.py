"""Fetch daily OHLCV stock prices from Yahoo Finance."""

import logging

import pandas as pd
import yfinance as yf

from airflow.exceptions import AirflowException
from psycopg2.extras import execute_values

from .base import YahooFinanceBaseOperator


logger = logging.getLogger(__name__)


class FetchYahooFinanceHistory(YahooFinanceBaseOperator):
    """Fetch and upsert daily OHLCV history into PostgreSQL."""

    def __init__(
        self,
        ticker: str,
        period: str = "5y",
        interval: str = "1d",
        postgres_conn_id: str = "postgres_landing",
        **kwargs,
    ):
        super().__init__(
            ticker=ticker,
            postgres_conn_id=postgres_conn_id,
            **kwargs,
        )

        if interval != "1d":
            raise ValueError(
                "landing.yahoo_history supports only interval='1d'. "
                "Use a separate timestamp-based table for intraday prices."
            )

        self.period = period
        self.interval = interval

    def execute(self, context):
        """Fetch, validate, and store historical prices."""
        logger.info(
            "Fetching history for %s (period=%s, interval=%s)",
            self.ticker,
            self.period,
            self.interval,
        )

        try:
            df = yf.Ticker(self.ticker).history(
                period=self.period,
                interval=self.interval,
                auto_adjust=False,
                actions=True,
            )

            if df is None or df.empty:
                logger.warning("No history data for %s", self.ticker)
                return {"status": "no_data", "ticker": self.ticker}

            rows = self._prepare_rows(df)
            records_stored = self._store_prices_in_postgres(rows)

            return {
                "status": "success",
                "ticker": self.ticker,
                "records_processed": records_stored,
            }

        except Exception as exc:
            logger.exception(
                "Failed to fetch history for %s", self.ticker
            )
            raise AirflowException(
                f"History ingestion failed for {self.ticker}: {exc}"
            ) from exc

    def _prepare_rows(self, df):
        """Validate daily observations and prepare database rows."""
        required_columns = {
            "Open", "High", "Low", "Close", "Adj Close", "Volume"
        }

        missing = required_columns - set(df.columns)

        if missing:
            raise ValueError(
                f"Missing required history columns: {sorted(missing)}"
            )

        rows = []
        seen_dates = set()

        for timestamp, values in df.iterrows():
            period_date = pd.Timestamp(timestamp).date()

            if pd.isna(period_date):
                raise ValueError("History contains an invalid date")

            if period_date in seen_dates:
                raise ValueError(
                    f"Duplicate daily observation: {period_date}"
                )

            seen_dates.add(period_date)

            prices = []

            for column in ("Open", "High", "Low", "Close", "Adj Close"):
                value = self.clean_scalar(values[column])

                if value is None:
                    raise ValueError(
                        f"Missing {column} for {self.ticker} "
                        f"on {period_date}"
                    )

                prices.append(float(value))

            volume = self.clean_scalar(values["Volume"])

            if volume is None or float(volume) < 0:
                raise ValueError(
                    f"Invalid volume for {self.ticker} on {period_date}"
                )

            if not float(volume).is_integer():
                raise ValueError(
                    f"Non-integer volume for {self.ticker} on {period_date}"
                )

            rows.append((
                self.ticker,
                period_date,
                *prices,
                int(volume),
                self.clean_scalar(values.get("Dividends", 0)),
                self.clean_scalar(values.get("Stock Splits", 0)),
            ))

        return rows

    def _store_prices_in_postgres(self, rows):
        """Batch-upsert daily history into landing.yahoo_history."""
        if not rows:
            return 0

        query = """
            INSERT INTO landing.yahoo_history (
                ticker,
                date,
                open,
                high,
                low,
                close,
                adj_close,
                volume,
                dividend,
                split
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
                ingested_at = CURRENT_TIMESTAMP,
                updated_at = CURRENT_TIMESTAMP
        """

        conn = self.get_db_connection()

        try:
            with conn.cursor() as cursor:
                execute_values(
                    cursor,
                    query,
                    rows,
                    page_size=1000,
                )

            conn.commit()

            logger.info(
                "Stored %d history records for %s",
                len(rows),
                self.ticker,
            )
            return len(rows)

        except Exception:
            conn.rollback()
            logger.exception(
                "Error storing history for %s", self.ticker
            )
            raise

        finally:
            conn.close()