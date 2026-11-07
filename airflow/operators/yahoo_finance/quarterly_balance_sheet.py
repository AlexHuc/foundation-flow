"""Fetch Yahoo Finance quarterly balance sheet data and store it in PostgreSQL."""

import logging

import pandas as pd
import yfinance as yf

from airflow.exceptions import AirflowException
from psycopg2 import sql
from psycopg2.extras import execute_values

from .base import YahooFinanceBaseOperator


logger = logging.getLogger(__name__)


class FetchYahooFinanceQuarterlyBalanceSheet(YahooFinanceBaseOperator):
    """Fetch and store quarterly Yahoo Finance balance sheets."""

    def execute(self, context):
        """Fetch quarterly balance sheet data."""
        logger.info(
            "Fetching quarterly balance sheet for %s",
            self.ticker,
        )

        try:
            quarterly_balance_sheet = (
                yf.Ticker(self.ticker).quarterly_balance_sheet
            )

            if (
                quarterly_balance_sheet is None
                or quarterly_balance_sheet.empty
            ):
                logger.warning(
                    "No quarterly balance sheet data for %s",
                    self.ticker,
                )
                return {
                    "status": "no_data",
                    "ticker": self.ticker,
                }

            periods_stored = (
                self._store_quarterly_balance_sheet_in_postgres(
                    quarterly_balance_sheet
                )
            )

            return {
                "status": "success",
                "ticker": self.ticker,
                "metrics_retrieved": len(quarterly_balance_sheet.index),
                "periods_stored": periods_stored,
            }

        except Exception as exc:
            logger.exception(
                "Error fetching quarterly balance sheet for %s",
                self.ticker,
            )
            raise AirflowException(
                f"Failed to fetch quarterly balance sheet "
                f"for {self.ticker}: {exc}"
            ) from exc

    def _store_quarterly_balance_sheet_in_postgres(
        self,
        quarterly_balance_sheet,
    ):
        """Transpose, normalize, and upsert quarterly balance sheets."""
        conn = self.get_db_connection()

        try:
            with conn.cursor() as cursor:

                # Retrieve the existing PostgreSQL table columns.
                cursor.execute(
                    """
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_schema = %s
                      AND table_name = %s
                    """,
                    ("landing", "yahoo_quarterly_balance_sheet"),
                )

                db_columns = {
                    row[0] for row in cursor.fetchall()
                }

                if not db_columns:
                    raise ValueError(
                        "Table landing.yahoo_quarterly_balance_sheet "
                        "was not found or has no columns."
                    )

                # Yahoo returns metrics in rows and dates in columns.
                # Transpose to one row per reporting period.
                periods = quarterly_balance_sheet.T.copy()

                # Reuse normalization from YahooFinanceBaseOperator.
                periods.columns = [
                    self.normalize_metric(col)
                    for col in periods.columns
                ]

                # Prevent ambiguous metric names.
                if periods.columns.has_duplicates:
                    raise ValueError(
                        "Duplicate quarterly balance sheet metrics "
                        "after normalization."
                    )

                # Select financial metrics matching PostgreSQL columns.
                # METADATA_COLUMNS is inherited from the base class.
                metric_columns = [
                    col
                    for col in periods.columns
                    if col in db_columns
                    and col not in self.METADATA_COLUMNS
                ]

                # Log metrics that do not exist in the database.
                skipped = [
                    str(metric)
                    for metric in quarterly_balance_sheet.index
                    if self.normalize_metric(metric)
                    not in metric_columns
                ]

                if skipped:
                    logger.warning(
                        "Skipping quarterly balance sheet metrics "
                        "without matching database columns "
                        "for %s: %s",
                        self.ticker,
                        ", ".join(skipped),
                    )

                if not metric_columns:
                    raise ValueError(
                        f"No matching quarterly balance sheet "
                        f"columns found for {self.ticker}"
                    )

                # Keep matching columns in Yahoo Finance order.
                periods = periods[metric_columns]

                rows = []
                seen_dates = set()

                for period, values in periods.iterrows():

                    # Validate the reporting period.
                    if pd.isna(period):
                        raise ValueError(
                            "Invalid quarterly balance sheet "
                            "reporting period."
                        )

                    # Convert pandas datetime to PostgreSQL DATE.
                    period_date = pd.Timestamp(period).date()

                    if period_date in seen_dates:
                        raise ValueError(
                            f"Duplicate quarterly balance sheet "
                            f"date: {period_date}"
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

                columns = [
                    "ticker",
                    "date",
                    *metric_columns,
                ]

                # Generate safe SQL UPDATE expressions.
                updates = sql.SQL(", ").join(
                    sql.SQL("{} = EXCLUDED.{}").format(
                        sql.Identifier(col),
                        sql.Identifier(col),
                    )
                    for col in metric_columns
                )

                # Insert new reporting periods or update existing ones.
                query = sql.SQL("""
                    INSERT INTO {}.{} ({})
                    VALUES %s

                    ON CONFLICT (ticker, date) DO UPDATE SET
                        {},
                        ingested_at = CURRENT_TIMESTAMP,
                        updated_at = CURRENT_TIMESTAMP
                """).format(
                    sql.Identifier("landing"),
                    sql.Identifier("yahoo_quarterly_balance_sheet"),
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
                "Stored %d quarterly balance sheet periods for %s",
                len(rows),
                self.ticker,
            )

            return len(rows)

        except Exception:
            conn.rollback()
            logger.exception(
                "Error storing quarterly balance sheet for %s",
                self.ticker,
            )
            raise

        finally:
            conn.close()