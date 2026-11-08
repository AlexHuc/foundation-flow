"""Fetch Yahoo Finance insider roster holders and store them in PostgreSQL."""

import logging

import pandas as pd
import yfinance as yf

from airflow.exceptions import AirflowException
from psycopg2 import sql
from psycopg2.extras import execute_values

from .base import YahooFinanceBaseOperator


logger = logging.getLogger(__name__)


class FetchYahooFinanceInsiderRosterHolders(YahooFinanceBaseOperator):
    """Fetch and upsert insider roster and direct ownership records."""

    def execute(self, context):
        """Fetch insider roster holders from Yahoo Finance."""
        logger.info(
            "Fetching insider roster holders for %s",
            self.ticker,
        )

        try:
            insider_roster_holders = (
                yf.Ticker(self.ticker).insider_roster_holders
            )

            if (
                insider_roster_holders is None
                or insider_roster_holders.empty
            ):
                logger.warning(
                    "No insider roster holders data for %s",
                    self.ticker,
                )
                return {
                    "status": "no_data",
                    "ticker": self.ticker,
                }

            records_stored = (
                self._store_insider_roster_holders_in_postgres(
                    insider_roster_holders
                )
            )

            return {
                "status": "success",
                "ticker": self.ticker,
                "records_retrieved": len(insider_roster_holders),
                "records_processed": records_stored,
            }

        except Exception as exc:
            logger.exception(
                "Failed to fetch insider roster holders for %s",
                self.ticker,
            )
            raise AirflowException(
                f"Insider roster holders ingestion failed for "
                f"{self.ticker}: {exc}"
            ) from exc

    def _prepare_rows(self, insider_roster_holders, db_columns):
        """Normalize metrics and prepare rows for PostgreSQL."""

        # Each row represents a company insider.
        # No transpose is necessary.
        holders = insider_roster_holders.copy()

        # Automatically normalize Yahoo Finance column names.
        holders.columns = [
            self.normalize_metric(column)
            for column in holders.columns
        ]

        if holders.columns.has_duplicates:
            raise ValueError(
                "Duplicate insider roster columns "
                "after normalization"
            )

        # Name is required for the primary key.
        key_columns = {"name"}

        missing = key_columns - set(holders.columns)

        if missing:
            raise ValueError(
                f"Missing insider roster columns: "
                f"{sorted(missing)}"
            )

        # Verify required PostgreSQL primary key columns.
        required_db_columns = {
            "ticker",
            "date",
            "name",
        }

        if not required_db_columns.issubset(db_columns):
            raise ValueError(
                "Missing required insider roster "
                "primary key columns"
            )

        # Automatically identify matching source metrics.
        metric_columns = [
            column
            for column in holders.columns
            if column in db_columns
            and column not in self.METADATA_COLUMNS
            and column not in key_columns
        ]

        # Log Yahoo Finance columns not found in PostgreSQL.
        skipped = [
            str(column)
            for column in insider_roster_holders.columns
            if self.normalize_metric(column) not in metric_columns
            and self.normalize_metric(column) not in key_columns
        ]

        if skipped:
            logger.warning(
                "Skipping insider roster metrics for %s: %s",
                self.ticker,
                ", ".join(skipped),
            )

        if not metric_columns:
            raise AirflowException(
                f"No matching insider roster columns "
                f"for {self.ticker}"
            )

        # Use one UTC snapshot date for all roster records.
        snapshot_date = self.snapshot_date()

        rows = []
        seen_names = set()

        for _, values in holders.iterrows():

            # Validate the insider name.
            name = values["name"]

            if pd.isna(name):
                raise ValueError(
                    "Missing insider name in roster"
                )

            name = str(name).strip()

            if not name:
                raise ValueError(
                    "Insider name cannot be empty"
                )

            # Prevent duplicate primary keys in one batch.
            if name in seen_names:
                raise ValueError(
                    f"Duplicate insider roster name: {name}"
                )

            seen_names.add(name)

            row_values = []

            for column in metric_columns:
                value = values[column]

                if pd.isna(value):
                    row_values.append(None)

                elif column in (
                    "latest_transaction_date",
                    "position_direct_date",
                ):
                    # Date fields from Yahoo Finance.
                    row_values.append(
                        pd.Timestamp(value).date()
                    )

                elif column == "shares_owned_directly":
                    # Direct share ownership must be a whole number.
                    number = self.clean_scalar(value)

                    if number is None:
                        row_values.append(None)

                    elif (
                        isinstance(number, bool)
                        or number != int(number)
                        or number < 0
                    ):
                        raise ValueError(
                            f"Invalid shares_owned_directly "
                            f"for {name}: {number}"
                        )

                    else:
                        row_values.append(int(number))

                else:
                    # Position, URL, and transaction description
                    # are text fields. Blank strings become NULL.
                    row_values.append(
                        str(value).strip() or None
                    )

            rows.append((
                self.ticker,
                snapshot_date,
                name,
                *row_values,
            ))

        return metric_columns, rows

    def _store_insider_roster_holders_in_postgres(
        self,
        insider_roster_holders,
    ):
        """Upsert insider roster using database column matching."""

        conn = self.get_db_connection()

        try:
            with conn.cursor() as cursor:

                # Discover columns from the PostgreSQL table.
                cursor.execute(
                    """
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_schema = %s
                      AND table_name = %s
                    """,
                    ("landing", "yahoo_insider_roster_holders"),
                )

                db_columns = {
                    row[0] for row in cursor.fetchall()
                }

                if not db_columns:
                    raise ValueError(
                        "Table landing.yahoo_insider_roster_holders "
                        "does not exist or has no columns"
                    )

                metric_columns, rows = self._prepare_rows(
                    insider_roster_holders,
                    db_columns,
                )

                if not rows:
                    raise ValueError(
                        "No insider roster records to insert"
                    )

                # Primary key columns and matching source metrics.
                columns = [
                    "ticker",
                    "date",
                    "name",
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

                    ON CONFLICT (ticker, date, name)
                    DO UPDATE SET
                        {},
                        ingested_at = CURRENT_TIMESTAMP,
                        updated_at = CURRENT_TIMESTAMP
                """).format(
                    sql.Identifier("landing"),
                    sql.Identifier("yahoo_insider_roster_holders"),
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
                "Stored %d insider roster records for %s",
                len(rows),
                self.ticker,
            )

            return len(rows)

        except Exception:
            conn.rollback()
            logger.exception(
                "Error storing insider roster holders for %s",
                self.ticker,
            )
            raise

        finally:
            conn.close()