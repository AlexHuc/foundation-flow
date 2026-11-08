"""Fetch Yahoo Finance major holders data and store it in PostgreSQL."""

import logging

import pandas as pd
import yfinance as yf

from airflow.exceptions import AirflowException
from psycopg2 import sql
from psycopg2.extras import execute_values

from .base import YahooFinanceBaseOperator


logger = logging.getLogger(__name__)


class FetchYahooFinanceMajorHolders(YahooFinanceBaseOperator):
    """Fetch and upsert major holder ownership statistics."""

    def execute(self, context):
        """Fetch major holders data from Yahoo Finance."""
        logger.info(
            "Fetching major holders for %s",
            self.ticker,
        )

        try:
            major_holders = yf.Ticker(self.ticker).major_holders

            if major_holders is None or major_holders.empty:
                logger.warning(
                    "No major holders data for %s",
                    self.ticker,
                )
                return {
                    "status": "no_data",
                    "ticker": self.ticker,
                }

            records_stored = self._store_major_holders_in_postgres(
                major_holders
            )

            return {
                "status": "success",
                "ticker": self.ticker,
                "metrics_retrieved": len(major_holders.index),
                "records_processed": records_stored,
            }

        except Exception as exc:
            logger.exception(
                "Failed to fetch major holders for %s",
                self.ticker,
            )
            raise AirflowException(
                f"Major holders ingestion failed for "
                f"{self.ticker}: {exc}"
            ) from exc

    def _prepare_rows(self, major_holders, db_columns):
        """Transpose, normalize, and prepare rows for PostgreSQL."""

        # Yahoo returns metrics in the Breakdown index
        # and their values in the Value column.
        if "Value" not in major_holders.columns:
            raise ValueError(
                "Missing Value column in major holders data"
            )

        # Transpose to one row with metrics as columns.
        holders = major_holders[["Value"]].T.copy()

        # Automatically normalize Yahoo Finance metric names.
        holders.columns = [
            self.normalize_metric(column)
            for column in holders.columns
        ]

        if holders.columns.has_duplicates:
            raise ValueError(
                "Duplicate major holders columns "
                "after normalization"
            )

        # Select only metrics that exist in PostgreSQL.
        metric_columns = [
            column
            for column in holders.columns
            if column in db_columns
            and column not in self.METADATA_COLUMNS
        ]

        # Log metrics not present in the database.
        skipped = [
            str(metric)
            for metric in major_holders.index
            if self.normalize_metric(metric) not in metric_columns
        ]

        if skipped:
            logger.warning(
                "Skipping major holders metrics for %s: %s",
                self.ticker,
                ", ".join(skipped),
            )

        if not metric_columns:
            raise AirflowException(
                f"No matching major holders columns "
                f"for {self.ticker}"
            )

        # Use the current UTC snapshot date.
        snapshot_date = self.snapshot_date()

        rows = []

        for _, values in holders[metric_columns].iterrows():

            row_values = []

            for column, value in values.items():

                if pd.isna(value):
                    row_values.append(None)

                elif column == "institutions_count":
                    # The count may arrive as a float (e.g. 7748.0).
                    number = self.numeric_or_none(value)

                    if number is None:
                        row_values.append(None)

                    elif number < 0 or not number.is_integer():
                        raise ValueError(
                            f"Invalid institutional holder count: "
                            f"{number}"
                        )

                    else:
                        row_values.append(int(number))

                else:
                    # Ownership percentages are decimal fractions.
                    row_values.append(
                        self.numeric_or_none(value)
                    )

            rows.append((
                self.ticker,
                snapshot_date,
                *row_values,
            ))

        return metric_columns, rows

    def _store_major_holders_in_postgres(self, major_holders):
        """Upsert major holders using database column matching."""

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
                    ("landing", "yahoo_major_holders"),
                )

                db_columns = {
                    row[0] for row in cursor.fetchall()
                }

                if not db_columns:
                    raise ValueError(
                        "Table landing.yahoo_major_holders "
                        "does not exist or has no columns"
                    )

                # Verify that the primary key columns exist.
                if not {"ticker", "date"}.issubset(db_columns):
                    raise ValueError(
                        "Missing required major holders "
                        "primary key columns"
                    )

                metric_columns, rows = self._prepare_rows(
                    major_holders,
                    db_columns,
                )

                if not rows:
                    raise ValueError(
                        "No major holders records to insert"
                    )

                # Primary key columns followed by matching metrics.
                columns = [
                    "ticker",
                    "date",
                    *metric_columns,
                ]

                # Dynamically generate UPDATE assignments.
                updates = sql.SQL(", ").join(
                    sql.SQL("{} = EXCLUDED.{}").format(
                        sql.Identifier(column),
                        sql.Identifier(column),
                    )
                    for column in metric_columns
                )

                # Dynamically generate PostgreSQL upsert.
                query = sql.SQL("""
                    INSERT INTO {}.{} ({})
                    VALUES %s

                    ON CONFLICT (ticker, date) DO UPDATE SET
                        {},
                        ingested_at = CURRENT_TIMESTAMP,
                        updated_at = CURRENT_TIMESTAMP
                """).format(
                    sql.Identifier("landing"),
                    sql.Identifier("yahoo_major_holders"),
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
                "Stored %d major holders snapshots for %s",
                len(rows),
                self.ticker,
            )

            return len(rows)

        except Exception:
            conn.rollback()
            logger.exception(
                "Error storing major holders for %s",
                self.ticker,
            )
            raise

        finally:
            conn.close()