"""Fetch Yahoo Finance quarterly cash flow statements and store them in PostgreSQL."""

import logging

import pandas as pd
import yfinance as yf

from airflow.exceptions import AirflowException
from psycopg2 import sql
from psycopg2.extras import execute_values

from .base import YahooFinanceBaseOperator


logger = logging.getLogger(__name__)


class FetchYahooFinanceQuarterlyCashFlow(YahooFinanceBaseOperator):
    """Fetch and store quarterly Yahoo Finance cash flow statements."""

    def execute(self, context):
        """Fetch quarterly cash flow statement data."""
        logger.info(
            "Fetching quarterly cash flow for %s",
            self.ticker,
        )

        try:
            quarterly_cashflow = (
                yf.Ticker(self.ticker).quarterly_cashflow
            )

            if quarterly_cashflow is None or quarterly_cashflow.empty:
                logger.warning(
                    "No quarterly cash flow data for %s",
                    self.ticker,
                )
                return {
                    "status": "no_data",
                    "ticker": self.ticker,
                }

            periods_stored = (
                self._store_quarterly_cashflow_in_postgres(
                    quarterly_cashflow
                )
            )

            return {
                "status": "success",
                "ticker": self.ticker,
                "metrics_retrieved": len(quarterly_cashflow.index),
                "periods_stored": periods_stored,
            }

        except Exception as exc:
            logger.exception(
                "Error fetching quarterly cash flow for %s",
                self.ticker,
            )
            raise AirflowException(
                f"Failed to fetch quarterly cash flow "
                f"for {self.ticker}: {exc}"
            ) from exc

    def _store_quarterly_cashflow_in_postgres(
        self,
        quarterly_cashflow,
    ):
        """Transpose, normalize, and upsert quarterly cash flow data."""
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
                    ("landing", "yahoo_quarterly_cashflow"),
                )

                db_columns = {
                    row[0] for row in cursor.fetchall()
                }

                if not db_columns:
                    raise ValueError(
                        "Table landing.yahoo_quarterly_cashflow "
                        "was not found or has no columns."
                    )

                # Yahoo returns metrics as rows and
                # reporting dates as columns.
                # Transpose to one row per fiscal quarter.
                periods = quarterly_cashflow.T.copy()

                # Reuse normalization from YahooFinanceBaseOperator.
                periods.columns = [
                    self.normalize_metric(col)
                    for col in periods.columns
                ]

                # Prevent duplicate metric names after normalization.
                if periods.columns.has_duplicates:
                    raise ValueError(
                        "Duplicate quarterly cash flow metric names "
                        "after normalization."
                    )

                # Select financial metrics matching the table schema.
                # METADATA_COLUMNS is inherited from the base class.
                metric_columns = [
                    col
                    for col in periods.columns
                    if col in db_columns
                    and col not in self.METADATA_COLUMNS
                ]

                # Log metrics that have no matching database column.
                skipped = [
                    str(metric)
                    for metric in quarterly_cashflow.index
                    if self.normalize_metric(metric)
                    not in metric_columns
                ]

                if skipped:
                    logger.warning(
                        "Skipping quarterly cash flow metrics "
                        "without matching database columns "
                        "for %s: %s",
                        self.ticker,
                        ", ".join(skipped),
                    )

                if not metric_columns:
                    raise ValueError(
                        f"No matching quarterly cash flow "
                        f"columns found for {self.ticker}"
                    )

                # Preserve the selected financial metric order.
                periods = periods[metric_columns]

                rows = []
                seen_dates = set()

                for period, values in periods.iterrows():

                    # Validate reporting date.
                    if pd.isna(period):
                        raise ValueError(
                            "Invalid quarterly cash flow reporting period."
                        )

                    # Convert pandas Timestamp into PostgreSQL DATE.
                    period_date = pd.Timestamp(period).date()

                    if period_date in seen_dates:
                        raise ValueError(
                            f"Duplicate quarterly cash flow "
                            f"reporting date: {period_date}"
                        )

                    seen_dates.add(period_date)

                    row = [self.ticker, period_date]

                    # Convert missing financial metrics to SQL NULL.
                    for value in values:
                        if pd.isna(value):
                            row.append(None)
                        else:
                            row.append(self.clean_scalar(value))

                    rows.append(tuple(row))

                if not rows:
                    return 0

                # Build the columns for INSERT.
                columns = [
                    "ticker",
                    "date",
                    *metric_columns,
                ]

                # Generate safe PostgreSQL UPDATE assignments.
                updates = sql.SQL(", ").join(
                    sql.SQL("{} = EXCLUDED.{}").format(
                        sql.Identifier(col),
                        sql.Identifier(col),
                    )
                    for col in metric_columns
                )

                # Insert new periods or update existing ones.
                query = sql.SQL("""
                    INSERT INTO {}.{} ({})
                    VALUES %s

                    ON CONFLICT (ticker, date) DO UPDATE SET
                        {},
                        ingested_at = CURRENT_TIMESTAMP,
                        updated_at = CURRENT_TIMESTAMP
                """).format(
                    sql.Identifier("landing"),
                    sql.Identifier("yahoo_quarterly_cashflow"),
                    sql.SQL(", ").join(
                        map(sql.Identifier, columns)
                    ),
                    updates,
                )

                # Batch upsert all reporting periods.
                execute_values(
                    cursor,
                    query.as_string(conn),
                    rows,
                    page_size=100,
                )

            conn.commit()

            logger.info(
                "Stored %d quarterly cash flow periods for %s",
                len(rows),
                self.ticker,
            )

            return len(rows)

        except Exception:
            conn.rollback()
            logger.exception(
                "Error storing quarterly cash flow for %s",
                self.ticker,
            )
            raise

        finally:
            conn.close()