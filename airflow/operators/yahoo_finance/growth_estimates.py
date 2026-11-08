"""Fetch Yahoo Finance growth estimates and store them in PostgreSQL."""

import logging

import pandas as pd
import yfinance as yf

from airflow.exceptions import AirflowException
from psycopg2 import sql
from psycopg2.extras import execute_values

from .base import YahooFinanceBaseOperator


logger = logging.getLogger(__name__)


class FetchYahooFinanceGrowthEstimates(YahooFinanceBaseOperator):
    """Fetch and upsert stock and index growth estimates."""

    def execute(self, context):
        """Fetch growth estimates from Yahoo Finance."""
        logger.info(
            "Fetching growth estimates for %s",
            self.ticker,
        )

        try:
            growth_estimates = (
                yf.Ticker(self.ticker).growth_estimates
            )

            if growth_estimates is None or growth_estimates.empty:
                logger.warning(
                    "No growth estimates for %s",
                    self.ticker,
                )
                return {
                    "status": "no_data",
                    "ticker": self.ticker,
                }

            records_stored = self._store_growth_estimates_in_postgres(
                growth_estimates
            )

            return {
                "status": "success",
                "ticker": self.ticker,
                "records_retrieved": len(growth_estimates),
                "records_processed": records_stored,
            }

        except Exception as exc:
            logger.exception(
                "Failed to fetch growth estimates for %s",
                self.ticker,
            )
            raise AirflowException(
                f"Growth estimates ingestion failed for "
                f"{self.ticker}: {exc}"
            ) from exc

    def _prepare_rows(self, growth_estimates, db_columns):
        """Normalize metrics and prepare rows for PostgreSQL."""

        # Each row represents a forecast period.
        # No transpose is necessary.
        periods = growth_estimates.copy()

        # Automatically normalize Yahoo Finance column names.
        periods.columns = [
            self.normalize_metric(column)
            for column in periods.columns
        ]

        if periods.columns.has_duplicates:
            raise ValueError(
                "Duplicate growth estimate columns "
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

        # Log metrics that do not match PostgreSQL columns.
        skipped = [
            str(metric)
            for metric in growth_estimates.columns
            if self.normalize_metric(metric) not in metric_columns
        ]

        if skipped:
            logger.warning(
                "Skipping growth estimate metrics for %s: %s",
                self.ticker,
                ", ".join(skipped),
            )

        if not metric_columns:
            raise AirflowException(
                f"No matching growth estimate columns "
                f"for {self.ticker}"
            )

        # Use a consistent UTC snapshot date.
        snapshot_date = self.snapshot_date()

        rows = []
        seen_periods = set()

        for period, values in periods[metric_columns].iterrows():

            if pd.isna(period):
                raise ValueError(
                    "Invalid growth estimate period"
                )

            period = str(period).strip()

            if not period:
                raise ValueError(
                    "Growth estimate period cannot be empty"
                )

            if period in seen_periods:
                raise ValueError(
                    f"Duplicate growth estimate period: {period}"
                )

            seen_periods.add(period)

            row_values = []

            for column, value in values.items():

                if pd.isna(value):
                    row_values.append(None)

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

    def _store_growth_estimates_in_postgres(
        self,
        growth_estimates,
    ):
        """Upsert growth estimates using database column matching."""

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
                    ("landing", "yahoo_growth_estimates"),
                )

                db_columns = {
                    row[0] for row in cursor.fetchall()
                }

                if not db_columns:
                    raise ValueError(
                        "Table landing.yahoo_growth_estimates "
                        "does not exist or has no columns"
                    )

                metric_columns, rows = self._prepare_rows(
                    growth_estimates,
                    db_columns,
                )

                if not rows:
                    raise ValueError(
                        "No growth estimate records to insert"
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
                    sql.Identifier("yahoo_growth_estimates"),
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
                "Stored %d growth estimate records for %s",
                len(rows),
                self.ticker,
            )

            return len(rows)

        except Exception:
            conn.rollback()
            logger.exception(
                "Error storing growth estimates for %s",
                self.ticker,
            )
            raise

        finally:
            conn.close()