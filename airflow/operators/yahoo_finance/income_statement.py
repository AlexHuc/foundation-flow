"""Fetch annual Yahoo Finance income statements."""

import logging
import pandas as pd
import yfinance as yf

from airflow.exceptions import AirflowException
from psycopg2 import sql
from psycopg2.extras import execute_values

from .base import YahooFinanceBaseOperator


logger = logging.getLogger(__name__)


class FetchYahooFinanceIncomeStatement(YahooFinanceBaseOperator):
    """Fetch and upsert annual income statements into PostgreSQL."""

    def execute(self, context):
        """Fetch and store income statement reporting periods."""
        logger.info(
            "Fetching income statement for %s", self.ticker
        )

        try:
            income_stmt = yf.Ticker(self.ticker).income_stmt

            if income_stmt is None or income_stmt.empty:
                logger.warning(
                    "No income statement for %s", self.ticker
                )
                return {"status": "no_data", "ticker": self.ticker}

            periods_stored = (
                self._store_income_statement_in_postgres(income_stmt)
            )

            return {
                "status": "success",
                "ticker": self.ticker,
                "metrics_retrieved": len(income_stmt.index),
                "periods_stored": periods_stored,
            }

        except Exception as exc:
            logger.exception(
                "Failed to fetch income statement for %s",
                self.ticker,
            )
            raise AirflowException(
                f"Income statement ingestion failed for "
                f"{self.ticker}: {exc}"
            ) from exc

    def _prepare_rows(self, income_stmt, db_columns):
        """Transpose, normalize, and prepare reporting periods."""
        periods = income_stmt.T.copy()

        periods.columns = [
            self.normalize_metric(column)
            for column in periods.columns
        ]

        if periods.columns.has_duplicates:
            raise ValueError(
                "Duplicate metric names after normalization"
            )

        metric_columns = [
            column
            for column in periods.columns
            if column in db_columns
            and column not in self.METADATA_COLUMNS
        ]

        skipped = [
            str(metric)
            for metric in income_stmt.index
            if self.normalize_metric(metric) not in metric_columns
        ]

        if skipped:
            logger.warning(
                "Skipping income statement metrics for %s: %s",
                self.ticker,
                ", ".join(skipped),
            )

        if not metric_columns:
            raise AirflowException(
                f"No matching income statement columns for {self.ticker}"
            )

        periods = periods[metric_columns]
        rows = []
        seen_dates = set()

        for period, values in periods.iterrows():
            period_date = pd.Timestamp(period).date()

            if pd.isna(period_date):
                raise ValueError("Invalid income statement period date")

            if period_date in seen_dates:
                raise ValueError(
                    f"Duplicate income statement date: {period_date}"
                )

            seen_dates.add(period_date)

            row_values = [
                None if pd.isna(value) else self.clean_scalar(value)
                for value in values
            ]

            rows.append((
                self.ticker,
                period_date,
                *row_values,
            ))

        return metric_columns, rows

    def _store_income_statement_in_postgres(self, income_stmt):
        """Upsert reporting periods using matching database columns."""
        conn = self.get_db_connection()

        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_schema = %s
                      AND table_name = %s
                    """,
                    ("landing", "yahoo_income_statement"),
                )

                db_columns = {
                    row[0] for row in cursor.fetchall()
                }

                if not db_columns:
                    raise ValueError(
                        "Table landing.yahoo_income_statement "
                        "does not exist or has no columns"
                    )

                metric_columns, rows = self._prepare_rows(
                    income_stmt,
                    db_columns,
                )

                if not rows:
                    raise ValueError(
                        "No income statement periods to insert"
                    )

                columns = [
                    "ticker",
                    "date",
                    *metric_columns,
                ]

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

                    ON CONFLICT (ticker, date) DO UPDATE SET
                        {},
                        ingested_at = CURRENT_TIMESTAMP,
                        updated_at = CURRENT_TIMESTAMP
                """).format(
                    sql.Identifier("landing"),
                    sql.Identifier("yahoo_income_statement"),
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
                "Stored %d income statement periods for %s",
                len(rows),
                self.ticker,
            )

            return len(rows)

        except Exception:
            conn.rollback()
            logger.exception(
                "Error storing income statement for %s",
                self.ticker,
            )
            raise

        finally:
            conn.close()