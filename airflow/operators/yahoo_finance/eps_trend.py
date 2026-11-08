"""Fetch Yahoo Finance analyst EPS trends and store them in PostgreSQL."""

import logging

import pandas as pd
import yfinance as yf

from airflow.exceptions import AirflowException
from psycopg2 import sql
from psycopg2.extras import execute_values

from .base import YahooFinanceBaseOperator


logger = logging.getLogger(__name__)


class FetchYahooFinanceEPSTrend(YahooFinanceBaseOperator):
    """Fetch and upsert analyst EPS estimate trends."""

    def execute(self, context):
        """Fetch EPS trends from Yahoo Finance."""
        logger.info(
            "Fetching EPS trends for %s",
            self.ticker,
        )

        try:
            eps_trend = yf.Ticker(self.ticker).eps_trend

            if eps_trend is None or eps_trend.empty:
                logger.warning(
                    "No EPS trends for %s",
                    self.ticker,
                )
                return {
                    "status": "no_data",
                    "ticker": self.ticker,
                }

            records_stored = self._store_eps_trend_in_postgres(
                eps_trend
            )

            return {
                "status": "success",
                "ticker": self.ticker,
                "records_retrieved": len(eps_trend),
                "records_processed": records_stored,
            }

        except Exception as exc:
            logger.exception(
                "Failed to fetch EPS trends for %s",
                self.ticker,
            )
            raise AirflowException(
                f"EPS trend ingestion failed for "
                f"{self.ticker}: {exc}"
            ) from exc

    def _prepare_rows(self, eps_trend, db_columns):
        """Normalize metrics and prepare rows for PostgreSQL."""

        # Each row represents a relative forecast period.
        # No transpose is necessary.
        periods = eps_trend.copy()

        # Automatically normalize Yahoo Finance column names.
        periods.columns = [
            self.normalize_metric(column)
            for column in periods.columns
        ]

        if periods.columns.has_duplicates:
            raise ValueError(
                "Duplicate EPS trend columns "
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

        # Log any Yahoo Finance metrics missing from PostgreSQL.
        skipped = [
            str(metric)
            for metric in eps_trend.columns
            if self.normalize_metric(metric) not in metric_columns
        ]

        if skipped:
            logger.warning(
                "Skipping EPS trend metrics for %s: %s",
                self.ticker,
                ", ".join(skipped),
            )

        if not metric_columns:
            raise AirflowException(
                f"No matching EPS trend columns "
                f"for {self.ticker}"
            )

        # Use one UTC snapshot date for all forecast periods.
        snapshot_date = self.snapshot_date()

        rows = []
        seen_periods = set()

        for period, values in periods[metric_columns].iterrows():

            if pd.isna(period):
                raise ValueError(
                    "Invalid EPS trend period"
                )

            period = str(period).strip()

            if not period:
                raise ValueError(
                    "EPS trend period cannot be empty"
                )

            if period in seen_periods:
                raise ValueError(
                    f"Duplicate EPS trend period: {period}"
                )

            seen_periods.add(period)

            row_values = []

            for column, value in values.items():

                if pd.isna(value):
                    row_values.append(None)

                elif column == "currency":
                    row_values.append(
                        str(value).strip() or None
                    )

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

    def _store_eps_trend_in_postgres(self, eps_trend):
        """Upsert EPS trends using database column matching."""

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
                    ("landing", "yahoo_eps_trend"),
                )

                db_columns = {
                    row[0] for row in cursor.fetchall()
                }

                if not db_columns:
                    raise ValueError(
                        "Table landing.yahoo_eps_trend "
                        "does not exist or has no columns"
                    )

                metric_columns, rows = self._prepare_rows(
                    eps_trend,
                    db_columns,
                )

                if not rows:
                    raise ValueError(
                        "No EPS trend records to insert"
                    )

                # Primary key columns and matching metrics.
                columns = [
                    "ticker",
                    "date",
                    "period",
                    *metric_columns,
                ]

                # Dynamically generate the UPDATE assignments.
                updates = sql.SQL(", ").join(
                    sql.SQL("{} = EXCLUDED.{}").format(
                        sql.Identifier(column),
                        sql.Identifier(column),
                    )
                    for column in metric_columns
                )

                # Dynamically generate the PostgreSQL upsert.
                query = sql.SQL("""
                    INSERT INTO {}.{} ({})
                    VALUES %s

                    ON CONFLICT (ticker, date, period) DO UPDATE SET
                        {},
                        ingested_at = CURRENT_TIMESTAMP,
                        updated_at = CURRENT_TIMESTAMP
                """).format(
                    sql.Identifier("landing"),
                    sql.Identifier("yahoo_eps_trend"),
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
                "Stored %d EPS trend records for %s",
                len(rows),
                self.ticker,
            )

            return len(rows)

        except Exception:
            conn.rollback()
            logger.exception(
                "Error storing EPS trends for %s",
                self.ticker,
            )
            raise

        finally:
            conn.close()