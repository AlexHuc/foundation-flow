"""Fetch Yahoo Finance analyst upgrades and downgrades into PostgreSQL."""

import logging

import pandas as pd
import yfinance as yf

from airflow.exceptions import AirflowException
from psycopg2 import sql
from psycopg2.extras import execute_values

from .base import YahooFinanceBaseOperator


logger = logging.getLogger(__name__)


class FetchYahooFinanceUpgradesDowngrades(YahooFinanceBaseOperator):
    """Fetch and upsert analyst ratings and price target changes."""

    def execute(self, context):
        """Fetch analyst upgrades and downgrades from Yahoo Finance."""
        logger.info(
            "Fetching analyst upgrades and downgrades for %s",
            self.ticker,
        )

        try:
            upgrades_downgrades = (
                yf.Ticker(self.ticker).upgrades_downgrades
            )

            if (
                upgrades_downgrades is None
                or upgrades_downgrades.empty
            ):
                logger.warning(
                    "No analyst upgrades or downgrades for %s",
                    self.ticker,
                )
                return {
                    "status": "no_data",
                    "ticker": self.ticker,
                }

            records_stored = (
                self._store_upgrades_downgrades_in_postgres(
                    upgrades_downgrades
                )
            )

            return {
                "status": "success",
                "ticker": self.ticker,
                "records_retrieved": len(upgrades_downgrades),
                "records_processed": records_stored,
            }

        except Exception as exc:
            logger.exception(
                "Failed to fetch analyst upgrades and downgrades "
                "for %s",
                self.ticker,
            )
            raise AirflowException(
                f"Upgrades and downgrades ingestion failed "
                f"for {self.ticker}: {exc}"
            ) from exc

    def _prepare_rows(self, upgrades_downgrades, db_columns):
        """Normalize analyst metrics and prepare rows for PostgreSQL."""

        # Each DataFrame row represents an analyst event.
        # GradeDate is the index, so no transpose is necessary.
        events = upgrades_downgrades.copy()

        # Automatically normalize Yahoo Finance column names.
        events.columns = [
            self.normalize_metric(column)
            for column in events.columns
        ]

        if events.columns.has_duplicates:
            raise ValueError(
                "Duplicate upgrades/downgrades columns "
                "after normalization"
            )

        # Firm is part of the PostgreSQL primary key.
        if "firm" not in events.columns:
            raise ValueError(
                "Missing firm column in upgrades/downgrades"
            )

        # Select only metric columns available in PostgreSQL.
        # Exclude the primary key fields.
        metric_columns = [
            column
            for column in events.columns
            if column in db_columns
            and column not in self.METADATA_COLUMNS
            and column not in ("firm", "grade_date")
        ]

        # Identify metrics with no matching PostgreSQL column.
        skipped = [
            str(metric)
            for metric in upgrades_downgrades.columns
            if self.normalize_metric(metric) not in metric_columns
            and self.normalize_metric(metric) != "firm"
        ]

        if skipped:
            logger.warning(
                "Skipping upgrades/downgrades metrics "
                "for %s: %s",
                self.ticker,
                ", ".join(skipped),
            )

        if not metric_columns:
            raise AirflowException(
                f"No matching upgrades/downgrades columns "
                f"for {self.ticker}"
            )

        # Ensure PostgreSQL has the complete primary key.
        required_db_columns = {
            "ticker",
            "grade_date",
            "firm",
        }

        if not required_db_columns.issubset(db_columns):
            raise ValueError(
                "Missing required PostgreSQL primary key columns"
            )

        rows = []
        seen_events = set()

        for grade_date, values in events.iterrows():

            # Validate the analyst event timestamp.
            if pd.isna(grade_date):
                raise ValueError(
                    "Invalid analyst grade date"
                )

            grade_timestamp = pd.Timestamp(grade_date)

            # The target column is TIMESTAMP WITHOUT TIME ZONE.
            # Reject timezone-aware values rather than silently
            # discarding their timezone information.
            if grade_timestamp.tzinfo is not None:
                raise ValueError(
                    "Timezone-aware grade date received. "
                    "Review the PostgreSQL timestamp schema."
                )

            grade_timestamp = grade_timestamp.to_pydatetime()

            # Validate the analyst firm.
            firm = values["firm"]

            if pd.isna(firm):
                raise ValueError(
                    "Missing analyst firm"
                )

            firm = str(firm).strip()

            if not firm:
                raise ValueError(
                    "Analyst firm cannot be empty"
                )

            event_key = (grade_timestamp, firm)

            if event_key in seen_events:
                raise ValueError(
                    "Duplicate analyst event for "
                    f"{firm} at {grade_timestamp}"
                )

            seen_events.add(event_key)

            row_values = []

            for column in metric_columns:
                value = values[column]

                if pd.isna(value):
                    row_values.append(None)

                elif column in (
                    "current_price_target",
                    "prior_price_target",
                ):
                    # Price targets are numeric values.
                    row_values.append(
                        self.numeric_or_none(value)
                    )

                else:
                    # Ratings and actions are text values.
                    row_values.append(
                        str(value).strip() or None
                    )

            rows.append((
                self.ticker,
                grade_timestamp,
                firm,
                *row_values,
            ))

        return metric_columns, rows

    def _store_upgrades_downgrades_in_postgres(
        self,
        upgrades_downgrades,
    ):
        """Upsert analyst events using matching database columns."""

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
                    ("landing", "yahoo_upgrades_downgrades"),
                )

                db_columns = {
                    row[0] for row in cursor.fetchall()
                }

                if not db_columns:
                    raise ValueError(
                        "Table landing.yahoo_upgrades_downgrades "
                        "does not exist or has no columns"
                    )

                metric_columns, rows = self._prepare_rows(
                    upgrades_downgrades,
                    db_columns,
                )

                if not rows:
                    raise ValueError(
                        "No upgrades/downgrades records to insert"
                    )

                # Primary key columns followed by matching metrics.
                columns = [
                    "ticker",
                    "grade_date",
                    "firm",
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

                    ON CONFLICT (ticker, grade_date, firm)
                    DO UPDATE SET
                        {},
                        ingested_at = CURRENT_TIMESTAMP,
                        updated_at = CURRENT_TIMESTAMP
                """).format(
                    sql.Identifier("landing"),
                    sql.Identifier("yahoo_upgrades_downgrades"),
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
                "Stored %d analyst events for %s",
                len(rows),
                self.ticker,
            )

            return len(rows)

        except Exception:
            conn.rollback()
            logger.exception(
                "Error storing analyst upgrades/downgrades "
                "for %s",
                self.ticker,
            )
            raise

        finally:
            conn.close()