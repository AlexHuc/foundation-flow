"""Fetch Yahoo Finance analyst earnings estimates and store them in PostgreSQL."""

import logging

import pandas as pd
import yfinance as yf

from airflow.exceptions import AirflowException
from psycopg2 import sql
from psycopg2.extras import execute_values

from .base import YahooFinanceBaseOperator


logger = logging.getLogger(__name__)


class FetchYahooFinanceEarningsEstimate(YahooFinanceBaseOperator):
    """Fetch and upsert analyst earnings estimates."""

    def execute(self, context):
        """Fetch earnings estimates from Yahoo Finance."""
        logger.info(
            "Fetching earnings estimates for %s",
            self.ticker,
        )

        try:
            earnings_estimate = (
                yf.Ticker(self.ticker).earnings_estimate
            )

            if earnings_estimate is None or earnings_estimate.empty:
                logger.warning(
                    "No earnings estimates for %s",
                    self.ticker,
                )
                return {
                    "status": "no_data",
                    "ticker": self.ticker,
                }

            records_stored = self._store_earnings_estimate_in_postgres(
                earnings_estimate
            )

            return {
                "status": "success",
                "ticker": self.ticker,
                "records_retrieved": len(earnings_estimate),
                "records_processed": records_stored,
            }

        except Exception as exc:
            logger.exception(
                "Failed to fetch earnings estimates for %s",
                self.ticker,
            )
            raise AirflowException(
                f"Earnings estimate ingestion failed for "
                f"{self.ticker}: {exc}"
            ) from exc

    def _prepare_rows(self, earnings_estimate, db_columns):
        """Normalize metrics and prepare rows for PostgreSQL."""

        # Each row is a forecast period, not a reporting date.
        periods = earnings_estimate.copy()

        # Automatically normalize Yahoo Finance column names.
        periods.columns = [
            self.normalize_metric(column)
            for column in periods.columns
        ]

        if periods.columns.has_duplicates:
            raise ValueError(
                "Duplicate earnings estimate columns "
                "after normalization"
            )

        # Select only fields that exist in PostgreSQL.
        metric_columns = [
            column
            for column in periods.columns
            if column in db_columns
            and column not in self.METADATA_COLUMNS
            and column != "period"
        ]

        skipped = [
            str(metric)
            for metric in earnings_estimate.columns
            if self.normalize_metric(metric) not in metric_columns
        ]

        if skipped:
            logger.warning(
                "Skipping earnings estimate metrics for %s: %s",
                self.ticker,
                ", ".join(skipped),
            )

        if not metric_columns:
            raise AirflowException(
                f"No matching earnings estimate columns "
                f"for {self.ticker}"
            )

        snapshot_date = self.snapshot_date()

        rows = []
        seen_periods = set()

        for period, values in periods[metric_columns].iterrows():

            if pd.isna(period):
                raise ValueError("Invalid earnings estimate period")

            period = str(period).strip()

            if not period:
                raise ValueError(
                    "Earnings estimate period cannot be empty"
                )

            if period in seen_periods:
                raise ValueError(
                    f"Duplicate earnings estimate period: {period}"
                )

            seen_periods.add(period)

            row_values = []

            for column, value in values.items():

                if pd.isna(value):
                    row_values.append(None)

                elif column == "currency":
                    row_values.append(str(value).strip() or None)

                elif column == "number_of_analysts":
                    number = self.numeric_or_none(value)

                    if number is None:
                        row_values.append(None)
                    elif number < 0 or not number.is_integer():
                        raise ValueError(
                            f"Invalid analyst count: {number}"
                        )
                    else:
                        row_values.append(int(number))

                else:
                    row_values.append(
                        self.numeric_or_none(value)
                    )

            rows.append((
                self.ticker,
                snapshot_date,
                period,
                *row_values,
            ))

        return metric_columns, rows

    def _store_earnings_estimate_in_postgres(
        self,
        earnings_estimate,
    ):
        """Upsert earnings estimates using database column matching."""

        conn = self.get_db_connection()

        try:
            with conn.cursor() as cursor:

                # Discover columns from the existing PostgreSQL table.
                cursor.execute(
                    """
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_schema = %s
                      AND table_name = %s
                    """,
                    ("landing", "yahoo_earnings_estimate"),
                )

                db_columns = {
                    row[0] for row in cursor.fetchall()
                }

                if not db_columns:
                    raise ValueError(
                        "Table landing.yahoo_earnings_estimate "
                        "does not exist or has no columns"
                    )

                metric_columns, rows = self._prepare_rows(
                    earnings_estimate,
                    db_columns,
                )

                if not rows:
                    raise ValueError(
                        "No earnings estimate records to insert"
                    )

                columns = [
                    "ticker",
                    "date",
                    "period",
                    *metric_columns,
                ]

                # Generate the ON CONFLICT UPDATE assignments.
                updates = sql.SQL(", ").join(
                    sql.SQL("{} = EXCLUDED.{}").format(
                        sql.Identifier(column),
                        sql.Identifier(column),
                    )
                    for column in metric_columns
                )

                query = sql.SQL("""
                    INSERT INTO {}.{} ({})
                    VALUES %s

                    ON CONFLICT (ticker, date, period) DO UPDATE SET
                        {},
                        ingested_at = CURRENT_TIMESTAMP,
                        updated_at = CURRENT_TIMESTAMP
                """).format(
                    sql.Identifier("landing"),
                    sql.Identifier("yahoo_earnings_estimate"),
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
                "Stored %d earnings estimate records for %s",
                len(rows),
                self.ticker,
            )

            return len(rows)

        except Exception:
            conn.rollback()
            logger.exception(
                "Error storing earnings estimates for %s",
                self.ticker,
            )
            raise

        finally:
            conn.close()