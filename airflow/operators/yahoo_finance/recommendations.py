"""Fetch Yahoo Finance analyst recommendations and store them in PostgreSQL."""

import logging

import pandas as pd
import yfinance as yf

from airflow.exceptions import AirflowException
from psycopg2 import sql
from psycopg2.extras import execute_values

from .base import YahooFinanceBaseOperator


logger = logging.getLogger(__name__)


class FetchYahooFinanceRecommendations(YahooFinanceBaseOperator):
    """Fetch and upsert analyst recommendation counts."""

    def execute(self, context):
        """Fetch recommendations from Yahoo Finance."""
        logger.info(
            "Fetching analyst recommendations for %s",
            self.ticker,
        )

        try:
            recommendations = (
                yf.Ticker(self.ticker).recommendations
            )

            if recommendations is None or recommendations.empty:
                logger.warning(
                    "No analyst recommendations for %s",
                    self.ticker,
                )
                return {
                    "status": "no_data",
                    "ticker": self.ticker,
                }

            records_stored = (
                self._store_recommendations_in_postgres(
                    recommendations
                )
            )

            return {
                "status": "success",
                "ticker": self.ticker,
                "records_retrieved": len(recommendations),
                "records_processed": records_stored,
            }

        except Exception as exc:
            logger.exception(
                "Failed to fetch recommendations for %s",
                self.ticker,
            )
            raise AirflowException(
                f"Recommendations ingestion failed for "
                f"{self.ticker}: {exc}"
            ) from exc

    def _prepare_rows(self, recommendations, db_columns):
        """Normalize metrics and prepare rows for PostgreSQL."""

        # Each row represents a relative recommendation month.
        # The period is a DataFrame column, not the index.
        periods = recommendations.copy()

        # Automatically normalize Yahoo Finance column names.
        periods.columns = [
            self.normalize_metric(column)
            for column in periods.columns
        ]

        if periods.columns.has_duplicates:
            raise ValueError(
                "Duplicate recommendations columns "
                "after normalization"
            )

        # The period column is required for the primary key.
        if "period" not in periods.columns:
            raise ValueError(
                "Missing period column in recommendations"
            )

        # Select only metric columns that exist in PostgreSQL.
        metric_columns = [
            column
            for column in periods.columns
            if column in db_columns
            and column not in self.METADATA_COLUMNS
            and column != "period"
        ]

        # Log metrics not present in the database.
        skipped = [
            str(metric)
            for metric in recommendations.columns
            if self.normalize_metric(metric) not in metric_columns
            and self.normalize_metric(metric) != "period"
        ]

        if skipped:
            logger.warning(
                "Skipping recommendation metrics for %s: %s",
                self.ticker,
                ", ".join(skipped),
            )

        if not metric_columns:
            raise AirflowException(
                f"No matching recommendation columns "
                f"for {self.ticker}"
            )

        # Use one UTC snapshot date for all recommendation periods.
        snapshot_date = self.snapshot_date()

        rows = []
        seen_periods = set()

        for _, values in periods.iterrows():

            # Read the period from the DataFrame column.
            period = values["period"]

            if pd.isna(period):
                raise ValueError(
                    "Invalid recommendations period"
                )

            period = str(period).strip()

            if not period:
                raise ValueError(
                    "Recommendations period cannot be empty"
                )

            if period in seen_periods:
                raise ValueError(
                    f"Duplicate recommendations period: {period}"
                )

            seen_periods.add(period)

            row_values = []

            for column in metric_columns:
                value = values[column]

                if pd.isna(value):
                    row_values.append(None)

                else:
                    # Recommendation metrics represent analyst counts.
                    number = self.numeric_or_none(value)

                    if number is None:
                        row_values.append(None)

                    elif number < 0 or not number.is_integer():
                        raise ValueError(
                            f"Invalid recommendation count "
                            f"for {column}: {number}"
                        )

                    else:
                        row_values.append(int(number))

            rows.append((
                self.ticker,
                snapshot_date,
                period,
                *row_values,
            ))

        return metric_columns, rows

    def _store_recommendations_in_postgres(
        self,
        recommendations,
    ):
        """Upsert recommendations using database column matching."""

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
                    ("landing", "yahoo_recommendations"),
                )

                db_columns = {
                    row[0] for row in cursor.fetchall()
                }

                if not db_columns:
                    raise ValueError(
                        "Table landing.yahoo_recommendations "
                        "does not exist or has no columns"
                    )

                metric_columns, rows = self._prepare_rows(
                    recommendations,
                    db_columns,
                )

                if not rows:
                    raise ValueError(
                        "No recommendation records to insert"
                    )

                # Primary key columns and matching metrics.
                columns = [
                    "ticker",
                    "date",
                    "period",
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

                    ON CONFLICT (ticker, date, period) DO UPDATE SET
                        {},
                        ingested_at = CURRENT_TIMESTAMP,
                        updated_at = CURRENT_TIMESTAMP
                """).format(
                    sql.Identifier("landing"),
                    sql.Identifier("yahoo_recommendations"),
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
                "Stored %d recommendation records for %s",
                len(rows),
                self.ticker,
            )

            return len(rows)

        except Exception:
            conn.rollback()
            logger.exception(
                "Error storing recommendations for %s",
                self.ticker,
            )
            raise

        finally:
            conn.close()