"""Fetch Yahoo Finance institutional holders and store them in PostgreSQL."""

import logging

import pandas as pd
import yfinance as yf

from airflow.exceptions import AirflowException
from psycopg2 import sql
from psycopg2.extras import execute_values

from .base import YahooFinanceBaseOperator


logger = logging.getLogger(__name__)


class FetchYahooFinanceInstitutionalHolders(YahooFinanceBaseOperator):
    """Fetch and upsert institutional ownership records."""

    def execute(self, context):
        """Fetch institutional holders from Yahoo Finance."""
        logger.info(
            "Fetching institutional holders for %s",
            self.ticker,
        )

        try:
            institutional_holders = (
                yf.Ticker(self.ticker).institutional_holders
            )

            if (
                institutional_holders is None
                or institutional_holders.empty
            ):
                logger.warning(
                    "No institutional holders for %s",
                    self.ticker,
                )
                return {
                    "status": "no_data",
                    "ticker": self.ticker,
                }

            records_stored = (
                self._store_institutional_holders_in_postgres(
                    institutional_holders
                )
            )

            return {
                "status": "success",
                "ticker": self.ticker,
                "records_retrieved": len(institutional_holders),
                "records_processed": records_stored,
            }

        except Exception as exc:
            logger.exception(
                "Failed to fetch institutional holders for %s",
                self.ticker,
            )
            raise AirflowException(
                f"Institutional holders ingestion failed for "
                f"{self.ticker}: {exc}"
            ) from exc

    def _prepare_rows(self, institutional_holders, db_columns):
        """Normalize metrics and prepare rows for PostgreSQL."""

        # Each row represents an institutional investor.
        # No transpose is necessary.
        holders = institutional_holders.copy()

        # Automatically normalize Yahoo Finance column names.
        holders.columns = [
            self.normalize_metric(column)
            for column in holders.columns
        ]

        if holders.columns.has_duplicates:
            raise ValueError(
                "Duplicate institutional holders columns "
                "after normalization"
            )

        # These fields are required for the primary key.
        key_columns = {
            "date_reported",
            "holder",
        }

        missing = key_columns - set(holders.columns)

        if missing:
            raise ValueError(
                f"Missing institutional holders columns: "
                f"{sorted(missing)}"
            )

        # Verify the PostgreSQL primary key columns.
        required_db_columns = {
            "ticker",
            "date",
            *key_columns,
        }

        if not required_db_columns.issubset(db_columns):
            raise ValueError(
                "Missing required institutional holders "
                "primary key columns"
            )

        # Automatically identify matching financial metrics.
        metric_columns = [
            column
            for column in holders.columns
            if column in db_columns
            and column not in self.METADATA_COLUMNS
            and column not in key_columns
        ]

        # Identify Yahoo Finance metrics missing from PostgreSQL.
        skipped = [
            str(metric)
            for metric in institutional_holders.columns
            if self.normalize_metric(metric) not in metric_columns
            and self.normalize_metric(metric) not in key_columns
        ]

        if skipped:
            logger.warning(
                "Skipping institutional holders metrics "
                "for %s: %s",
                self.ticker,
                ", ".join(skipped),
            )

        if not metric_columns:
            raise AirflowException(
                f"No matching institutional holders columns "
                f"for {self.ticker}"
            )

        # Use one UTC snapshot date for all institutions.
        snapshot_date = self.snapshot_date()

        rows = []
        seen_holders = set()

        for _, values in holders.iterrows():

            # Validate the reporting date.
            date_reported = values["date_reported"]

            if pd.isna(date_reported):
                raise ValueError(
                    "Invalid institutional holdings reporting date"
                )

            date_reported = pd.Timestamp(
                date_reported
            ).date()

            # Validate the institutional holder name.
            holder = values["holder"]

            if pd.isna(holder):
                raise ValueError(
                    "Missing institutional holder name"
                )

            holder = str(holder).strip()

            if not holder:
                raise ValueError(
                    "Institutional holder name cannot be empty"
                )

            # Prevent duplicate primary keys in the same batch.
            holder_key = (date_reported, holder)

            if holder_key in seen_holders:
                raise ValueError(
                    f"Duplicate institutional holder: "
                    f"{holder} on {date_reported}"
                )

            seen_holders.add(holder_key)

            row_values = []

            for column in metric_columns:
                value = values[column]

                if pd.isna(value):
                    row_values.append(None)

                elif column in ("shares", "value"):
                    # Preserve integer share counts and market values.
                    number = self.clean_scalar(value)

                    if number is None:
                        row_values.append(None)

                    elif (
                        isinstance(number, bool)
                        or number != int(number)
                    ):
                        raise ValueError(
                            f"Invalid {column} for {holder}: "
                            f"{number}"
                        )

                    else:
                        row_values.append(int(number))

                else:
                    # pct_held and pct_change are decimal fractions.
                    row_values.append(
                        self.numeric_or_none(value)
                    )

            rows.append((
                self.ticker,
                snapshot_date,
                date_reported,
                holder,
                *row_values,
            ))

        return metric_columns, rows

    def _store_institutional_holders_in_postgres(
        self,
        institutional_holders,
    ):
        """Upsert holders using automatic database column matching."""

        conn = self.get_db_connection()

        try:
            with conn.cursor() as cursor:

                # Discover the PostgreSQL table columns.
                cursor.execute(
                    """
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_schema = %s
                      AND table_name = %s
                    """,
                    ("landing", "yahoo_institutional_holders"),
                )

                db_columns = {
                    row[0] for row in cursor.fetchall()
                }

                if not db_columns:
                    raise ValueError(
                        "Table landing.yahoo_institutional_holders "
                        "does not exist or has no columns"
                    )

                metric_columns, rows = self._prepare_rows(
                    institutional_holders,
                    db_columns,
                )

                if not rows:
                    raise ValueError(
                        "No institutional holders records to insert"
                    )

                # Primary key fields followed by matching metrics.
                columns = [
                    "ticker",
                    "date",
                    "date_reported",
                    "holder",
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
                        date_reported,
                        holder
                    )
                    DO UPDATE SET
                        {},
                        ingested_at = CURRENT_TIMESTAMP,
                        updated_at = CURRENT_TIMESTAMP
                """).format(
                    sql.Identifier("landing"),
                    sql.Identifier("yahoo_institutional_holders"),
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
                "Stored %d institutional holders records for %s",
                len(rows),
                self.ticker,
            )

            return len(rows)

        except Exception:
            conn.rollback()
            logger.exception(
                "Error storing institutional holders for %s",
                self.ticker,
            )
            raise

        finally:
            conn.close()