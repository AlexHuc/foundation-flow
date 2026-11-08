"""Fetch Yahoo Finance insider purchases and store them in PostgreSQL."""

import logging
from decimal import Decimal

import pandas as pd
import yfinance as yf

from airflow.exceptions import AirflowException
from psycopg2 import sql
from psycopg2.extras import execute_values

from .base import YahooFinanceBaseOperator


logger = logging.getLogger(__name__)


class FetchYahooFinanceInsiderPurchases(YahooFinanceBaseOperator):
    """Fetch and upsert six-month insider purchase summaries."""

    def execute(self, context):
        """Fetch insider purchases from Yahoo Finance."""
        logger.info(
            "Fetching insider purchases for %s",
            self.ticker,
        )

        try:
            insider_purchases = (
                yf.Ticker(self.ticker).insider_purchases
            )

            if (
                insider_purchases is None
                or insider_purchases.empty
            ):
                logger.warning(
                    "No insider purchases data for %s",
                    self.ticker,
                )
                return {
                    "status": "no_data",
                    "ticker": self.ticker,
                }

            records_stored = (
                self._store_insider_purchases_in_postgres(
                    insider_purchases
                )
            )

            return {
                "status": "success",
                "ticker": self.ticker,
                "records_retrieved": len(insider_purchases),
                "records_processed": records_stored,
            }

        except Exception as exc:
            logger.exception(
                "Failed to fetch insider purchases for %s",
                self.ticker,
            )
            raise AirflowException(
                f"Insider purchases ingestion failed for "
                f"{self.ticker}: {exc}"
            ) from exc

    def _prepare_rows(self, insider_purchases, db_columns):
        """Normalize metrics and prepare rows for PostgreSQL."""

        # Each row represents a six-month insider activity metric.
        # No transpose is necessary.
        purchases = insider_purchases.copy()

        # Automatically normalize Yahoo Finance column names.
        purchases.columns = [
            self.normalize_metric(column)
            for column in purchases.columns
        ]

        if purchases.columns.has_duplicates:
            raise ValueError(
                "Duplicate insider purchases columns "
                "after normalization"
            )

        # The summary label identifies each metric.
        key_columns = {
            "insider_purchases_last_6m",
        }

        missing = key_columns - set(purchases.columns)

        if missing:
            raise ValueError(
                f"Missing insider purchases columns: "
                f"{sorted(missing)}"
            )

        # Verify required PostgreSQL columns.
        required_db_columns = {
            "ticker",
            "date",
            *key_columns,
        }

        if not required_db_columns.issubset(db_columns):
            raise ValueError(
                "Missing required insider purchases "
                "primary key columns"
            )

        # Automatically identify matching metric columns.
        metric_columns = [
            column
            for column in purchases.columns
            if column in db_columns
            and column not in self.METADATA_COLUMNS
            and column not in key_columns
        ]

        # Identify Yahoo Finance metrics missing from PostgreSQL.
        skipped = [
            str(column)
            for column in insider_purchases.columns
            if self.normalize_metric(column) not in metric_columns
            and self.normalize_metric(column) not in key_columns
        ]

        if skipped:
            logger.warning(
                "Skipping insider purchases metrics "
                "for %s: %s",
                self.ticker,
                ", ".join(skipped),
            )

        if not metric_columns:
            raise AirflowException(
                f"No matching insider purchases metrics "
                f"for {self.ticker}"
            )

        # Use one UTC snapshot date for all summary metrics.
        snapshot_date = self.snapshot_date()

        rows = []
        seen_metrics = set()

        for _, values in purchases.iterrows():

            # Read the metric name from the DataFrame column.
            metric_name = values["insider_purchases_last_6m"]

            if pd.isna(metric_name):
                raise ValueError(
                    "Missing insider purchases metric name"
                )

            metric_name = str(metric_name).strip()

            if not metric_name:
                raise ValueError(
                    "Insider purchases metric name cannot be empty"
                )

            # Prevent duplicate primary keys in the same batch.
            if metric_name in seen_metrics:
                raise ValueError(
                    f"Duplicate insider purchases metric: "
                    f"{metric_name}"
                )

            seen_metrics.add(metric_name)

            row_values = []

            for column in metric_columns:
                value = values[column]

                if pd.isna(value):
                    row_values.append(None)

                elif column == "trans":
                    # Transaction counts must be whole numbers.
                    number = self.numeric_or_none(value)

                    if number is None:
                        row_values.append(None)

                    elif number < 0 or not number.is_integer():
                        raise ValueError(
                            f"Invalid transaction count "
                            f"for {metric_name}: {number}"
                        )

                    else:
                        row_values.append(int(number))

                else:
                    # Shares contains both share counts and
                    # fractional percentage metrics.
                    #
                    # Decimal preserves the scalar's decimal
                    # representation for PostgreSQL NUMERIC.
                    number = self.clean_scalar(value)

                    if number is None:
                        row_values.append(None)

                    else:
                        row_values.append(
                            Decimal(str(number))
                        )

            rows.append((
                self.ticker,
                snapshot_date,
                metric_name,
                *row_values,
            ))

        return metric_columns, rows

    def _store_insider_purchases_in_postgres(
        self,
        insider_purchases,
    ):
        """Upsert insider purchases using database column matching."""

        conn = self.get_db_connection()

        try:
            with conn.cursor() as cursor:

                # Discover the existing PostgreSQL table columns.
                cursor.execute(
                    """
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_schema = %s
                      AND table_name = %s
                    """,
                    ("landing", "yahoo_insider_purchases"),
                )

                db_columns = {
                    row[0] for row in cursor.fetchall()
                }

                if not db_columns:
                    raise ValueError(
                        "Table landing.yahoo_insider_purchases "
                        "does not exist or has no columns"
                    )

                metric_columns, rows = self._prepare_rows(
                    insider_purchases,
                    db_columns,
                )

                if not rows:
                    raise ValueError(
                        "No insider purchases records to insert"
                    )

                # Primary key fields followed by matching metrics.
                columns = [
                    "ticker",
                    "date",
                    "insider_purchases_last_6m",
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

                # Dynamically generate the PostgreSQL upsert.
                query = sql.SQL("""
                    INSERT INTO {}.{} ({})
                    VALUES %s

                    ON CONFLICT (
                        ticker,
                        date,
                        insider_purchases_last_6m
                    )
                    DO UPDATE SET
                        {},
                        ingested_at = CURRENT_TIMESTAMP,
                        updated_at = CURRENT_TIMESTAMP
                """).format(
                    sql.Identifier("landing"),
                    sql.Identifier("yahoo_insider_purchases"),
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
                "Stored %d insider purchases metrics for %s",
                len(rows),
                self.ticker,
            )

            return len(rows)

        except Exception:
            conn.rollback()
            logger.exception(
                "Error storing insider purchases for %s",
                self.ticker,
            )
            raise

        finally:
            conn.close()