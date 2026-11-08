"""Fetch Yahoo Finance earnings announcement dates and EPS results, then store them in PostgreSQL."""

import logging

import pandas as pd
import yfinance as yf

from airflow.exceptions import AirflowException
from psycopg2.extras import execute_values

from .base import YahooFinanceBaseOperator


logger = logging.getLogger(__name__)


class FetchYahooFinanceEarningsDates(YahooFinanceBaseOperator):
    """Fetch and store Yahoo Finance earnings dates."""

    def __init__(
        self,
        ticker: str,
        limit: int = 100,
        postgres_conn_id: str = "postgres_landing",
        **kwargs,
    ):
        super().__init__(
            ticker=ticker,
            postgres_conn_id=postgres_conn_id,
            **kwargs,
        )

        if not 1 <= limit <= 100:
            raise ValueError("limit must be between 1 and 100")

        self.limit = limit

    def execute(self, context):
        """Fetch earnings dates and store EPS results."""
        logger.info(
            "Fetching earnings dates for %s (limit=%d)",
            self.ticker,
            self.limit,
        )

        try:
            # Request historical and upcoming earnings dates.
            earnings_dates = yf.Ticker(
                self.ticker
            ).get_earnings_dates(limit=self.limit)

            if earnings_dates is None or earnings_dates.empty:
                logger.warning(
                    "No earnings dates returned for %s",
                    self.ticker,
                )
                return {
                    "status": "no_data",
                    "ticker": self.ticker,
                }

            rows = self._prepare_rows(earnings_dates)

            records_stored = self._store_earnings_dates_in_postgres(
                rows
            )

            return {
                "status": "success",
                "ticker": self.ticker,
                "records_retrieved": len(earnings_dates),
                "records_processed": records_stored,
            }

        except Exception as exc:
            logger.exception(
                "Error fetching earnings dates for %s",
                self.ticker,
            )
            raise AirflowException(
                f"Failed to fetch earnings dates "
                f"for {self.ticker}: {exc}"
            ) from exc

    def _prepare_rows(self, earnings_dates):
        """Validate and prepare earnings events for PostgreSQL."""

        # Earnings dates are already stored as DataFrame rows.
        df = earnings_dates.copy()

        # Reuse normalization from YahooFinanceBaseOperator.
        df.columns = [
            self.normalize_metric(col)
            for col in df.columns
        ]

        # The base normalizer converts Surprise(%) to surprise.
        # Rename it to an explicit database metric name.
        df = df.rename(
            columns={"surprise": "surprise_percent"}
        )

        if df.columns.has_duplicates:
            raise ValueError(
                "Duplicate earnings metric names after normalization."
            )

        required_columns = {
            "eps_estimate",
            "reported_eps",
            "surprise_percent",
        }

        missing = required_columns - set(df.columns)

        if missing:
            raise ValueError(
                f"Missing earnings date columns: {sorted(missing)}"
            )

        rows = []
        seen_dates = set()

        for earnings_date, values in df.iterrows():

            if pd.isna(earnings_date):
                raise ValueError(
                    "Invalid earnings announcement timestamp."
                )

            timestamp = pd.Timestamp(earnings_date)

            # A timezone-aware timestamp is required.
            # Do not silently assume a timezone for naive dates.
            if timestamp.tzinfo is None:
                raise ValueError(
                    f"Earnings date has no timezone: {timestamp}"
                )

            # Preserve the precise earnings timestamp.
            timestamp = timestamp.to_pydatetime()

            if timestamp in seen_dates:
                raise ValueError(
                    f"Duplicate earnings announcement: {timestamp}"
                )

            seen_dates.add(timestamp)

            row = (
                self.ticker,
                timestamp,
                self.numeric_or_none(values["eps_estimate"]),
                self.numeric_or_none(values["reported_eps"]),
                self.numeric_or_none(values["surprise_percent"]),
            )

            rows.append(row)

        return rows

    def _store_earnings_dates_in_postgres(self, rows):
        """Batch-upsert earnings events into PostgreSQL."""

        if not rows:
            return 0

        query = """
            INSERT INTO landing.yahoo_earnings_dates (
                ticker,
                earnings_date,
                eps_estimate,
                reported_eps,
                surprise_percent
            )
            VALUES %s

            ON CONFLICT (ticker, earnings_date) DO UPDATE SET
                eps_estimate = EXCLUDED.eps_estimate,
                reported_eps = EXCLUDED.reported_eps,
                surprise_percent = EXCLUDED.surprise_percent,
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
                    page_size=100,
                )

            conn.commit()

            logger.info(
                "Stored %d earnings date records for %s",
                len(rows),
                self.ticker,
            )

            return len(rows)

        except Exception:
            conn.rollback()
            logger.exception(
                "Error storing earnings dates for %s",
                self.ticker,
            )
            raise

        finally:
            conn.close()