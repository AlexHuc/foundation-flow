"""Fetch Yahoo Finance annual cash flow statements and store them in PostgreSQL."""

import logging

import pandas as pd
import yfinance as yf

from airflow.exceptions import AirflowException
from psycopg2 import sql
from psycopg2.extras import execute_values

from .base import YahooFinanceBaseOperator


logger = logging.getLogger(__name__)


class FetchYahooFinanceCashFlow(YahooFinanceBaseOperator):
    """Fetch and store annual Yahoo Finance cash flow statements."""

    def execute(self, context):
        """Fetch annual cash flow statement data."""
        logger.info(
            "Fetching annual cash flow statement for %s",
            self.ticker,
        )

        try:
            cashflow = yf.Ticker(self.ticker).cashflow

            if cashflow is None or cashflow.empty:
                logger.warning(
                    "No annual cash flow data for %s",
                    self.ticker,
                )
                return {
                    "status": "no_data",
                    "ticker": self.ticker,
                }

            periods_stored = self._store_cashflow_in_postgres(
                cashflow
            )

            return {
                "status": "success",
                "ticker": self.ticker,
                "metrics_retrieved": len(cashflow.index),
                "periods_stored": periods_stored,
            }

        except Exception as exc:
            logger.exception(
                "Error fetching annual cash flow for %s",
                self.ticker,
            )
            raise AirflowException(
                f"Failed to fetch annual cash flow "
                f"for {self.ticker}: {exc}"
            ) from exc

    def _store_cashflow_in_postgres(self, cashflow):
        """Transpose, normalize, and upsert cash flow statements."""
        conn = self.get_db_connection()

        try:
            with conn.cursor() as cursor:

                # Retrieve available PostgreSQL table columns.
                cursor.execute(
                    """
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_schema = %s
                      AND table_name = %s
                    """,
                    ("landing", "yahoo_cashflow"),
                )

                db_columns = {
                    row[0] for row in cursor.fetchall()
                }

                if not db_columns:
                    raise ValueError(
                        "Table landing.yahoo_cashflow "
                        "was not found or has no columns."
                    )

                # Yahoo Finance returns metrics in rows
                # and fiscal reporting dates in columns.
                periods = cashflow.T.copy()

                # Normalize metric names using the base class.
                periods.columns = [
                    self.normalize_metric(col)
                    for col in periods.columns
                ]

                # Prevent collisions after normalization.
                if periods.columns.has_duplicates:
                    raise ValueError(
                        "Duplicate cash flow metric names "
                        "after normalization."
                    )

                # Select metrics with matching database columns.
                metric_columns = [
                    col
                    for col in periods.columns
                    if col in db_columns
                    and col not in self.METADATA_COLUMNS
                ]

                # Log metrics not available in the database.
                skipped = [
                    str(metric)
                    for metric in cashflow.index
                    if self.normalize_metric(metric)
                    not in metric_columns
                ]

                if skipped:
                    logger.warning(
                        "Skipping cash flow metrics without "
                        "matching database columns for %s: %s",
                        self.ticker,
                        ", ".join(skipped),
                    )

                if not metric_columns:
                    raise ValueError(
                        f"No matching cash flow columns "
                        f"found for {self.ticker}"
                    )

                # Keep financial metrics in their original order.
                periods = periods[metric_columns]

                rows = []
                seen_dates = set()

                for period, values in periods.iterrows():

                    # Validate reporting dates before conversion.
                    if pd.isna(period):
                        raise ValueError(
                            "Invalid cash flow reporting period."
                        )

                    # Preserve Yahoo's fiscal period-end date.
                    period_date = pd.Timestamp(period).date()

                    if period_date in seen_dates:
                        raise ValueError(
                            f"Duplicate cash flow reporting date: "
                            f"{period_date}"
                        )

                    seen_dates.add(period_date)

                    row = [self.ticker, period_date]

                    # Convert missing financial values to SQL NULL.
                    for value in values:
                        if pd.isna(value):
                            row.append(None)
                        else:
                            row.append(self.clean_scalar(value))

                    rows.append(tuple(row))

                if not rows:
                    return 0

                # Build the INSERT column list.
                columns = [
                    "ticker",
                    "date",
                    *metric_columns,
                ]

                # Construct UPDATE expressions safely.
                updates = sql.SQL(", ").join(
                    sql.SQL("{} = EXCLUDED.{}").format(
                        sql.Identifier(col),
                        sql.Identifier(col),
                    )
                    for col in metric_columns
                )

                # Insert or update annual reporting periods.
                query = sql.SQL("""
                    INSERT INTO {}.{} ({})
                    VALUES %s

                    ON CONFLICT (ticker, date) DO UPDATE SET
                        {},
                        ingested_at = CURRENT_TIMESTAMP,
                        updated_at = CURRENT_TIMESTAMP
                """).format(
                    sql.Identifier("landing"),
                    sql.Identifier("yahoo_cashflow"),
                    sql.SQL(", ").join(
                        map(sql.Identifier, columns)
                    ),
                    updates,
                )

                # Batch insert or update.
                execute_values(
                    cursor,
                    query.as_string(conn),
                    rows,
                    page_size=100,
                )

            conn.commit()

            logger.info(
                "Stored %d annual cash flow periods for %s",
                len(rows),
                self.ticker,
            )

            return len(rows)

        except Exception:
            conn.rollback()
            logger.exception(
                "Error storing annual cash flow for %s",
                self.ticker,
            )
            raise

        finally:
            conn.close()