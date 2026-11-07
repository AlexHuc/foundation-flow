"""Fetch Yahoo Finance TTM cash flow statements and store them in PostgreSQL."""

import logging

import pandas as pd
import yfinance as yf

from airflow.exceptions import AirflowException
from psycopg2 import sql
from psycopg2.extras import execute_values

from .base import YahooFinanceBaseOperator


logger = logging.getLogger(__name__)


class FetchYahooFinanceTTMCashFlow(YahooFinanceBaseOperator):
    """Fetch and store Yahoo Finance TTM cash flow statements."""

    def execute(self, context):
        """Fetch trailing twelve months cash flow data."""
        logger.info(
            "Fetching TTM cash flow for %s",
            self.ticker,
        )

        try:
            ttm_cashflow = yf.Ticker(self.ticker).ttm_cashflow

            if ttm_cashflow is None or ttm_cashflow.empty:
                logger.warning(
                    "No TTM cash flow data for %s",
                    self.ticker,
                )
                return {
                    "status": "no_data",
                    "ticker": self.ticker,
                }

            periods_stored = self._store_ttm_cashflow_in_postgres(
                ttm_cashflow
            )

            return {
                "status": "success",
                "ticker": self.ticker,
                "metrics_retrieved": len(ttm_cashflow.index),
                "periods_stored": periods_stored,
            }

        except Exception as exc:
            logger.exception(
                "Error fetching TTM cash flow for %s",
                self.ticker,
            )
            raise AirflowException(
                f"Failed to fetch TTM cash flow "
                f"for {self.ticker}: {exc}"
            ) from exc

    def _store_ttm_cashflow_in_postgres(self, ttm_cashflow):
        """Transpose, normalize, and upsert TTM cash flow data."""
        conn = self.get_db_connection()

        try:
            with conn.cursor() as cursor:

                # Retrieve existing PostgreSQL table columns.
                cursor.execute(
                    """
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_schema = %s
                      AND table_name = %s
                    """,
                    ("landing", "yahoo_ttm_cashflow"),
                )

                db_columns = {
                    row[0] for row in cursor.fetchall()
                }

                if not db_columns:
                    raise ValueError(
                        "Table landing.yahoo_ttm_cashflow "
                        "was not found or has no columns."
                    )

                # Yahoo returns metrics as rows and reporting
                # dates as columns. Transpose to one row per date.
                periods = ttm_cashflow.T.copy()

                # Reuse normalization from YahooFinanceBaseOperator.
                periods.columns = [
                    self.normalize_metric(col)
                    for col in periods.columns
                ]

                # Check for duplicate names after normalization.
                if periods.columns.has_duplicates:
                    raise ValueError(
                        "Duplicate TTM cash flow metric names "
                        "after normalization."
                    )

                # Match financial metrics to PostgreSQL columns.
                # METADATA_COLUMNS is inherited from the base class.
                metric_columns = [
                    col
                    for col in periods.columns
                    if col in db_columns
                    and col not in self.METADATA_COLUMNS
                ]

                # Identify metrics without a database column.
                skipped = [
                    str(metric)
                    for metric in ttm_cashflow.index
                    if self.normalize_metric(metric)
                    not in metric_columns
                ]

                if skipped:
                    logger.warning(
                        "Skipping TTM cash flow metrics without "
                        "matching database columns for %s: %s",
                        self.ticker,
                        ", ".join(skipped),
                    )

                if not metric_columns:
                    raise ValueError(
                        f"No matching TTM cash flow columns "
                        f"found for {self.ticker}"
                    )

                # Preserve the selected metric order.
                periods = periods[metric_columns]

                rows = []
                seen_dates = set()

                for period, values in periods.iterrows():

                    # Validate the reporting period.
                    if pd.isna(period):
                        raise ValueError(
                            "Invalid TTM cash flow reporting period."
                        )

                    # Convert pandas Timestamp to PostgreSQL DATE.
                    period_date = pd.Timestamp(period).date()

                    if period_date in seen_dates:
                        raise ValueError(
                            f"Duplicate TTM cash flow reporting "
                            f"date: {period_date}"
                        )

                    seen_dates.add(period_date)

                    row = [self.ticker, period_date]

                    # Convert missing values to SQL NULL and
                    # NumPy scalars to standard Python values.
                    for value in values:
                        if pd.isna(value):
                            row.append(None)
                        else:
                            row.append(self.clean_scalar(value))

                    rows.append(tuple(row))

                if not rows:
                    return 0

                # Build the INSERT columns.
                columns = [
                    "ticker",
                    "date",
                    *metric_columns,
                ]

                # Safely generate SQL UPDATE expressions.
                updates = sql.SQL(", ").join(
                    sql.SQL("{} = EXCLUDED.{}").format(
                        sql.Identifier(col),
                        sql.Identifier(col),
                    )
                    for col in metric_columns
                )

                # Upsert TTM cash flow statements.
                query = sql.SQL("""
                    INSERT INTO {}.{} ({})
                    VALUES %s

                    ON CONFLICT (ticker, date) DO UPDATE SET
                        {},
                        ingested_at = CURRENT_TIMESTAMP,
                        updated_at = CURRENT_TIMESTAMP
                """).format(
                    sql.Identifier("landing"),
                    sql.Identifier("yahoo_ttm_cashflow"),
                    sql.SQL(", ").join(
                        map(sql.Identifier, columns)
                    ),
                    updates,
                )

                # Batch insert or update reporting periods.
                execute_values(
                    cursor,
                    query.as_string(conn),
                    rows,
                    page_size=100,
                )

            conn.commit()

            logger.info(
                "Stored %d TTM cash flow periods for %s",
                len(rows),
                self.ticker,
            )

            return len(rows)

        except Exception:
            conn.rollback()
            logger.exception(
                "Error storing TTM cash flow for %s",
                self.ticker,
            )
            raise

        finally:
            conn.close()