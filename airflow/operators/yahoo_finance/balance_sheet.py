"""Fetch Yahoo Finance annual balance sheet data and store it in PostgreSQL."""

import logging

import pandas as pd
import yfinance as yf

from airflow.exceptions import AirflowException
from psycopg2 import sql
from psycopg2.extras import execute_values

from .base import YahooFinanceBaseOperator


logger = logging.getLogger(__name__)


class FetchYahooFinanceBalanceSheet(YahooFinanceBaseOperator):
    """Fetch and store annual Yahoo Finance balance sheets."""

    def execute(self, context):
        """Fetch annual balance sheet data."""
        logger.info(
            "Fetching annual balance sheet for %s",
            self.ticker,
        )

        try:
            balance_sheet = yf.Ticker(self.ticker).balance_sheet

            if balance_sheet is None or balance_sheet.empty:
                logger.warning(
                    "No annual balance sheet data for %s",
                    self.ticker,
                )
                return {
                    "status": "no_data",
                    "ticker": self.ticker,
                }

            periods_stored = self._store_balance_sheet_in_postgres(
                balance_sheet
            )

            return {
                "status": "success",
                "ticker": self.ticker,
                "metrics_retrieved": len(balance_sheet.index),
                "periods_stored": periods_stored,
            }

        except Exception as exc:
            logger.exception(
                "Error fetching annual balance sheet for %s",
                self.ticker,
            )
            raise AirflowException(
                f"Failed to fetch annual balance sheet "
                f"for {self.ticker}: {exc}"
            ) from exc

    def _store_balance_sheet_in_postgres(self, balance_sheet):
        """Transpose, normalize, and upsert balance sheet data."""
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
                    ("landing", "yahoo_balance_sheet"),
                )

                db_columns = {
                    row[0] for row in cursor.fetchall()
                }

                if not db_columns:
                    raise ValueError(
                        "Table landing.yahoo_balance_sheet "
                        "was not found or has no columns."
                    )

                # Yahoo returns metrics in rows and dates in columns.
                # Transpose to one row per reporting period.
                periods = balance_sheet.T.copy()

                # Reuse normalization from YahooFinanceBaseOperator.
                periods.columns = [
                    self.normalize_metric(col)
                    for col in periods.columns
                ]

                # Prevent ambiguous column names.
                if periods.columns.has_duplicates:
                    raise ValueError(
                        "Duplicate balance sheet metric names "
                        "after normalization."
                    )

                # Select only the financial metrics matching
                # columns in the PostgreSQL table.
                metric_columns = [
                    col
                    for col in periods.columns
                    if col in db_columns
                    and col not in self.METADATA_COLUMNS
                ]

                # Log Yahoo metrics not present in PostgreSQL.
                skipped = [
                    str(metric)
                    for metric in balance_sheet.index
                    if self.normalize_metric(metric)
                    not in metric_columns
                ]

                if skipped:
                    logger.warning(
                        "Skipping balance sheet metrics "
                        "without matching database columns "
                        "for %s: %s",
                        self.ticker,
                        ", ".join(skipped),
                    )

                if not metric_columns:
                    raise ValueError(
                        f"No matching balance sheet columns "
                        f"found for {self.ticker}"
                    )

                # Keep matching metrics in DataFrame order.
                periods = periods[metric_columns]

                rows = []
                seen_dates = set()

                for period, values in periods.iterrows():

                    # Validate the reporting period before conversion.
                    if pd.isna(period):
                        raise ValueError(
                            "Invalid balance sheet reporting period."
                        )

                    # Preserve Yahoo's fiscal reporting date.
                    period_date = pd.Timestamp(period).date()

                    if period_date in seen_dates:
                        raise ValueError(
                            f"Duplicate balance sheet date: "
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

                # Generate safe SQL identifiers for all columns.
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
                    sql.Identifier("yahoo_balance_sheet"),
                    sql.SQL(", ").join(
                        map(sql.Identifier, columns)
                    ),
                    updates,
                )

                # Batch insert or update all reporting periods.
                execute_values(
                    cursor,
                    query.as_string(conn),
                    rows,
                    page_size=100,
                )

            conn.commit()

            logger.info(
                "Stored %d annual balance sheet periods for %s",
                len(rows),
                self.ticker,
            )

            return len(rows)

        except Exception:
            conn.rollback()
            logger.exception(
                "Error storing annual balance sheet for %s",
                self.ticker,
            )
            raise

        finally:
            conn.close()