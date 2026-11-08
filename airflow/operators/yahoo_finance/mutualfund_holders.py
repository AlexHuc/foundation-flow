"""Fetch Yahoo Finance mutual fund holders and store them in PostgreSQL."""

import logging

import pandas as pd
import yfinance as yf

from airflow.exceptions import AirflowException
from psycopg2 import sql
from psycopg2.extras import execute_values

from .base import YahooFinanceBaseOperator


logger = logging.getLogger(__name__)


class FetchYahooFinanceMutualFundHolders(YahooFinanceBaseOperator):
    """Fetch and upsert mutual fund ownership records."""

    def execute(self, context):
        """Fetch mutual fund holders from Yahoo Finance."""
        logger.info(
            "Fetching mutual fund holders for %s",
            self.ticker,
        )

        try:
            mutualfund_holders = (
                yf.Ticker(self.ticker).mutualfund_holders
            )

            if mutualfund_holders is None or mutualfund_holders.empty:
                logger.warning(
                    "No mutual fund holders for %s",
                    self.ticker,
                )
                return {
                    "status": "no_data",
                    "ticker": self.ticker,
                }

            records_stored = (
                self._store_mutualfund_holders_in_postgres(
                    mutualfund_holders
                )
            )

            return {
                "status": "success",
                "ticker": self.ticker,
                "records_retrieved": len(mutualfund_holders),
                "records_processed": records_stored,
            }

        except Exception as exc:
            logger.exception(
                "Failed to fetch mutual fund holders for %s",
                self.ticker,
            )
            raise AirflowException(
                f"Mutual fund holders ingestion failed for "
                f"{self.ticker}: {exc}"
            ) from exc

    def _prepare_rows(self, mutualfund_holders, db_columns):
        """Normalize metrics and prepare rows for PostgreSQL."""

        # Each row represents a mutual fund or ETF holder.
        # No transpose is necessary.
        holders = mutualfund_holders.copy()

        # Automatically normalize Yahoo Finance column names.
        holders.columns = [
            self.normalize_metric(column)
            for column in holders.columns
        ]

        if holders.columns.has_duplicates:
            raise ValueError(
                "Duplicate mutual fund holders columns "
                "after normalization"
            )

        # These columns are part of the primary key.
        key_columns = {
            "date_reported",
            "holder",
        }

        missing = key_columns - set(holders.columns)

        if missing:
            raise ValueError(
                f"Missing mutual fund holders columns: "
                f"{sorted(missing)}"
            )

        # Verify required PostgreSQL primary key columns.
        required_db_columns = {
            "ticker",
            "date",
            *key_columns,
        }

        if not required_db_columns.issubset(db_columns):
            raise ValueError(
                "Missing required mutual fund holders "
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
            for metric in mutualfund_holders.columns
            if self.normalize_metric(metric) not in metric_columns
            and self.normalize_metric(metric) not in key_columns
        ]

        if skipped:
            logger.warning(
                "Skipping mutual fund holders metrics "
                "for %s: %s",
                self.ticker,
                ", ".join(skipped),
            )

        if not metric_columns:
            raise AirflowException(
                f"No matching mutual fund holders columns "
                f"for {self.ticker}"
            )

        # One UTC snapshot date for all holder records.
        snapshot_date = self.snapshot_date()

        rows = []
        seen_holders = set()

        for _, values in holders.iterrows():

            # Validate the reporting date.
            date_reported = values["date_reported"]

            if pd.isna(date_reported):
                raise ValueError(
                    "Invalid mutual fund holdings reporting date"
                )

            date_reported = pd.Timestamp(
                date_reported
            ).date()

            # Validate the mutual fund holder name.
            holder = values["holder"]

            if pd.isna(holder):
                raise ValueError(
                    "Missing mutual fund holder name"
                )

            holder = str(holder).strip()

            if not holder:
                raise ValueError(
                    "Mutual fund holder name cannot be empty"
                )

            # Prevent duplicate primary keys in the same batch.
            holder_key = (date_reported, holder)

            if holder_key in seen_holders:
                raise ValueError(
                    f"Duplicate mutual fund holder: "
                    f"{holder} on {date_reported}"
                )

            seen_holders.add(holder_key)

            row_values = []

            for column in metric_columns:
                value = values[column]

                if pd.isna(value):
                    row_values.append(None)

                elif column in ("shares", "value"):
                    # Preserve large integer values.
                    number = self.clean_scalar(value)

                    if number is None:
                        row_values.append(None)

                    elif (
                        isinstance(number, bool)
                        or number != int(number)
                        or number < 0
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

    def _store_mutualfund_holders_in_postgres(
        self,
        mutualfund_holders,
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
                    ("landing", "yahoo_mutualfund_holders"),
                )

                db_columns = {
                    row[0] for row in cursor.fetchall()
                }

                if not db_columns:
                    raise ValueError(
                        "Table landing.yahoo_mutualfund_holders "
                        "does not exist or has no columns"
                    )

                metric_columns, rows = self._prepare_rows(
                    mutualfund_holders,
                    db_columns,
                )

                if not rows:
                    raise ValueError(
                        "No mutual fund holders records to insert"
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
                    sql.Identifier("yahoo_mutualfund_holders"),
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
                "Stored %d mutual fund holders records for %s",
                len(rows),
                self.ticker,
            )

            return len(rows)

        except Exception:
            conn.rollback()
            logger.exception(
                "Error storing mutual fund holders for %s",
                self.ticker,
            )
            raise

        finally:
            conn.close()