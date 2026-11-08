"""
Fetch Yahoo Finance quarterly earnings history
and store it in PostgreSQL.
"""

import logging

import pandas as pd
import yfinance as yf

from airflow.exceptions import AirflowException
from psycopg2.extras import execute_values

from .base import YahooFinanceBaseOperator


logger = logging.getLogger(__name__)


class FetchYahooFinanceEarningsHistory(YahooFinanceBaseOperator):
    """Fetch and store Yahoo Finance quarterly earnings history."""

    COLUMN_MAPPING = {
        "epsActual": "eps_actual",
        "epsEstimate": "eps_estimate",
        "epsDifference": "eps_difference",
        "surprisePercent": "surprise_percent",
    }

    def execute(self, context):
        """Fetch quarterly earnings history data."""
        logger.info(
            "Fetching earnings history for %s",
            self.ticker,
        )

        try:
            earnings_history = yf.Ticker(
                self.ticker
            ).earnings_history

            if (
                earnings_history is None
                or earnings_history.empty
            ):
                logger.warning(
                    "No earnings history data for %s",
                    self.ticker,
                )
                return {
                    "status": "no_data",
                    "ticker": self.ticker,
                }

            rows = self._prepare_rows(earnings_history)

            records_stored = (
                self._store_earnings_history_in_postgres(rows)
            )

            return {
                "status": "success",
                "ticker": self.ticker,
                "records_retrieved": len(earnings_history),
                "records_processed": records_stored,
            }

        except Exception as exc:
            logger.exception(
                "Error fetching earnings history for %s",
                self.ticker,
            )
            raise AirflowException(
                f"Failed to fetch earnings history "
                f"for {self.ticker}: {exc}"
            ) from exc

    def _prepare_rows(self, earnings_history):
        """Validate and prepare earnings records for PostgreSQL."""

        # Each row represents a reporting quarter.
        df = earnings_history.copy()

        # Rename Yahoo's camelCase metrics to PostgreSQL snake_case.
        df = df.rename(columns=self.COLUMN_MAPPING)

        required_columns = set(self.COLUMN_MAPPING.values())

        missing = required_columns - set(df.columns)

        if missing:
            raise ValueError(
                f"Missing earnings history columns: {sorted(missing)}"
            )

        # Check for duplicate columns after renaming.
        if df.columns.has_duplicates:
            raise ValueError(
                "Duplicate earnings history columns after renaming."
            )

        # Log unexpected metrics without preventing ingestion.
        skipped = [
            str(column)
            for column in df.columns
            if column not in required_columns
        ]

        if skipped:
            logger.warning(
                "Skipping earnings history metrics for %s: %s",
                self.ticker,
                ", ".join(skipped),
            )

        rows = []
        seen_quarters = set()

        for quarter, values in df.iterrows():

            # Validate the reporting period.
            if pd.isna(quarter):
                raise ValueError(
                    "Invalid earnings history reporting quarter."
                )

            # Preserve the quarter date returned by Yahoo Finance.
            quarter_date = pd.Timestamp(quarter).date()

            if quarter_date in seen_quarters:
                raise ValueError(
                    f"Duplicate earnings history quarter: "
                    f"{quarter_date}"
                )

            seen_quarters.add(quarter_date)

            row = (
                self.ticker,
                quarter_date,
                self.numeric_or_none(values["eps_actual"]),
                self.numeric_or_none(values["eps_estimate"]),
                self.numeric_or_none(values["eps_difference"]),
                self.numeric_or_none(values["surprise_percent"]),
            )

            rows.append(row)

        return rows

    def _store_earnings_history_in_postgres(self, rows):
        """Batch-upsert quarterly earnings results."""

        if not rows:
            return 0

        query = """
            INSERT INTO landing.yahoo_earnings_history (
                ticker,
                quarter,
                eps_actual,
                eps_estimate,
                eps_difference,
                surprise_percent
            )
            VALUES %s

            ON CONFLICT (ticker, quarter) DO UPDATE SET
                eps_actual = EXCLUDED.eps_actual,
                eps_estimate = EXCLUDED.eps_estimate,
                eps_difference = EXCLUDED.eps_difference,
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
                "Stored %d earnings history records for %s",
                len(rows),
                self.ticker,
            )

            return len(rows)

        except Exception:
            conn.rollback()
            logger.exception(
                "Error storing earnings history for %s",
                self.ticker,
            )
            raise

        finally:
            conn.close()