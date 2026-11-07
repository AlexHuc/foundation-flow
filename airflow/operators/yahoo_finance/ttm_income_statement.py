"""Fetch Yahoo Finance TTM income statement data and store it in PostgreSQL."""

import logging

import pandas as pd
import yfinance as yf

from airflow.exceptions import AirflowException
from psycopg2 import sql
from psycopg2.extras import execute_values

from .base import YahooFinanceBaseOperator


logger = logging.getLogger(__name__)


class FetchYahooFinanceTTMIncomeStatement(YahooFinanceBaseOperator):
    """Fetch and store trailing twelve months income statements."""

    def execute(self, context):
        """Fetch TTM income statement data."""
        logger.info(
            "Fetching TTM income statement for %s",
            self.ticker,
        )

        try:
            ttm_income_stmt = yf.Ticker(self.ticker).ttm_income_stmt

            if ttm_income_stmt is None or ttm_income_stmt.empty:
                logger.warning(
                    "No TTM income statement data for %s",
                    self.ticker,
                )
                return {
                    "status": "no_data",
                    "ticker": self.ticker,
                }

            periods_stored = (
                self._store_ttm_income_statement_in_postgres(
                    ttm_income_stmt
                )
            )

            return {
                "status": "success",
                "ticker": self.ticker,
                "metrics_retrieved": len(ttm_income_stmt.index),
                "periods_stored": periods_stored,
            }

        except Exception as exc:
            logger.exception(
                "Error fetching TTM income statement for %s",
                self.ticker,
            )
            raise AirflowException(
                f"Failed to fetch TTM income statement "
                f"for {self.ticker}: {exc}"
            ) from exc

    def _store_ttm_income_statement_in_postgres(self, ttm_income_stmt):
        """Transpose, normalize, and upsert TTM income statements."""
        conn = self.get_db_connection()

        try:
            with conn.cursor() as cursor:

                # Retrieve available columns from PostgreSQL.
                cursor.execute(
                    """
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_schema = %s
                      AND table_name = %s
                    """,
                    ("landing", "yahoo_ttm_income_statement"),
                )

                db_columns = {
                    row[0] for row in cursor.fetchall()
                }

                if not db_columns:
                    raise ValueError(
                        "Table landing.yahoo_ttm_income_statement "
                        "was not found or has no columns."
                    )

                # Yahoo metrics are rows; dates are columns.
                # Transpose to one row per reporting period.
                periods = ttm_income_stmt.T.copy()

                # Reuse normalization from YahooFinanceBaseOperator.
                periods.columns = [
                    self.normalize_metric(col)
                    for col in periods.columns
                ]

                if periods.columns.has_duplicates:
                    raise ValueError(
                        "Duplicate TTM income statement metrics "
                        "after normalization."
                    )

                # Select metrics matching the PostgreSQL schema.
                metric_columns = [
                    col
                    for col in periods.columns
                    if col in db_columns
                    and col not in self.METADATA_COLUMNS
                ]

                skipped = [
                    str(metric)
                    for metric in ttm_income_stmt.index
                    if self.normalize_metric(metric)
                    not in metric_columns
                ]

                if skipped:
                    logger.warning(
                        "Skipping TTM income statement metrics "
                        "without matching database columns "
                        "for %s: %s",
                        self.ticker,
                        ", ".join(skipped),
                    )

                if not metric_columns:
                    raise ValueError(
                        f"No matching TTM income statement "
                        f"columns found for {self.ticker}"
                    )

                # Preserve the selected column order.
                periods = periods[metric_columns]

                rows = []
                seen_dates = set()

                for period, values in periods.iterrows():

                    if pd.isna(period):
                        raise ValueError(
                            "Invalid TTM reporting period."
                        )

                    # Preserve the Yahoo reporting period-end date.
                    period_date = pd.Timestamp(period).date()

                    if period_date in seen_dates:
                        raise ValueError(
                            f"Duplicate TTM reporting date: "
                            f"{period_date}"
                        )

                    seen_dates.add(period_date)

                    row = [self.ticker, period_date]

                    for value in values:
                        if pd.isna(value):
                            row.append(None)
                        else:
                            row.append(self.clean_scalar(value))

                    rows.append(tuple(row))

                if not rows:
                    return 0

                columns = [
                    "ticker",
                    "date",
                    *metric_columns,
                ]

                # Safely construct the dynamic UPDATE assignments.
                updates = sql.SQL(", ").join(
                    sql.SQL("{} = EXCLUDED.{}").format(
                        sql.Identifier(col),
                        sql.Identifier(col),
                    )
                    for col in metric_columns
                )

                query = sql.SQL("""
                    INSERT INTO {}.{} ({})
                    VALUES %s

                    ON CONFLICT (ticker, date) DO UPDATE SET
                        {},
                        ingested_at = CURRENT_TIMESTAMP,
                        updated_at = CURRENT_TIMESTAMP
                """).format(
                    sql.Identifier("landing"),
                    sql.Identifier("yahoo_ttm_income_statement"),
                    sql.SQL(", ").join(
                        map(sql.Identifier, columns)
                    ),
                    updates,
                )

                execute_values(
                    cursor,
                    query.as_string(conn),
                    rows,
                    page_size=100,
                )

            conn.commit()

            logger.info(
                "Stored %d TTM income statement periods for %s",
                len(rows),
                self.ticker,
            )

            return len(rows)

        except Exception:
            conn.rollback()
            logger.exception(
                "Error storing TTM income statement for %s",
                self.ticker,
            )
            raise

        finally:
            conn.close()