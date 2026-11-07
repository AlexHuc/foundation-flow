"""Fetch Yahoo Finance quarterly income statements"""

import logging

import pandas as pd
import yfinance as yf

from airflow.exceptions import AirflowException
from psycopg2 import sql
from psycopg2.extras import execute_values

from .base import YahooFinanceBaseOperator


logger = logging.getLogger(__name__)


class FetchYahooFinanceQuarterlyIncomeStatement(YahooFinanceBaseOperator):
    """Fetch and store quarterly income statement data."""

    def execute(self, context):
        """Fetch and store quarterly income statement data."""
        logger.info(
            "Fetching quarterly income statement for %s",
            self.ticker,
        )

        try:
            quarterly_income_stmt = (
                yf.Ticker(self.ticker).quarterly_income_stmt
            )

            if (
                quarterly_income_stmt is None
                or quarterly_income_stmt.empty
            ):
                logger.warning(
                    "No quarterly income statement data for %s",
                    self.ticker,
                )
                return {
                    "status": "no_data",
                    "ticker": self.ticker,
                }

            periods_stored = (
                self._store_quarterly_income_statement_in_postgres(
                    quarterly_income_stmt
                )
            )

            return {
                "status": "success",
                "ticker": self.ticker,
                "metrics_retrieved": len(quarterly_income_stmt.index),
                "periods_stored": periods_stored,
            }

        except Exception as exc:
            logger.exception(
                "Error fetching quarterly income statement for %s",
                self.ticker,
            )
            raise AirflowException(
                f"Failed to fetch quarterly income statement "
                f"for {self.ticker}: {exc}"
            ) from exc

    def _store_quarterly_income_statement_in_postgres(
        self,
        quarterly_income_stmt,
    ):
        """Transpose, normalize, and upsert quarterly statements."""
        conn = self.get_db_connection()

        try:
            with conn.cursor() as cursor:

                # Read the existing PostgreSQL table columns.
                cursor.execute(
                    """
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_schema = %s
                      AND table_name = %s
                    """,
                    ("landing", "yahoo_quarterly_income_statement"),
                )

                db_columns = {
                    row[0] for row in cursor.fetchall()
                }

                if not db_columns:
                    raise ValueError(
                        "Table landing.yahoo_quarterly_income_statement "
                        "was not found or has no columns."
                    )

                # Yahoo returns metrics in rows and reporting
                # dates in columns. Transpose to one row per date.
                periods = quarterly_income_stmt.T.copy()

                periods.columns = [
                    self.normalize_metric(col)
                    for col in periods.columns
                ]

                # Avoid ambiguous names after normalization.
                if periods.columns.has_duplicates:
                    raise ValueError(
                        "Duplicate quarterly income statement "
                        "metrics after normalization."
                    )

                # Select only metrics matching the database schema.
                metric_columns = [
                    col
                    for col in periods.columns
                    if col in db_columns
                    and col not in self.METADATA_COLUMNS
                ]

                # Log metrics without corresponding table columns.
                skipped = [
                    str(metric)
                    for metric in quarterly_income_stmt.index
                    if self.normalize_metric(metric)
                    not in metric_columns
                ]

                if skipped:
                    logger.warning(
                        "Skipping quarterly income statement "
                        "metrics for %s: %s",
                        self.ticker,
                        ", ".join(skipped),
                    )

                if not metric_columns:
                    raise ValueError(
                        f"No matching quarterly income statement "
                        f"columns found for {self.ticker}"
                    )

                # Keep matching metrics in DataFrame column order.
                periods = periods[metric_columns]

                rows = []
                seen_dates = set()

                for period, values in periods.iterrows():

                    # Convert pandas reporting dates into SQL DATE.
                    period_date = pd.Timestamp(period).date()

                    if pd.isna(period_date):
                        raise ValueError(
                            "Invalid quarterly reporting date."
                        )

                    if period_date in seen_dates:
                        raise ValueError(
                            f"Duplicate quarterly reporting date: "
                            f"{period_date}"
                        )

                    seen_dates.add(period_date)

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

                # Build the INSERT dynamically using safe
                # PostgreSQL identifiers.
                columns = [
                    "ticker",
                    "date",
                    *metric_columns,
                ]

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
                    sql.Identifier("yahoo_quarterly_income_statement"),
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
                "Stored %d quarterly income statement periods "
                "for %s",
                len(rows),
                self.ticker,
            )

            return len(rows)

        except Exception:
            conn.rollback()
            logger.exception(
                "Error storing quarterly income statement for %s",
                self.ticker,
            )
            raise

        finally:
            conn.close()