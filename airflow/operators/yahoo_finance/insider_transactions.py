"""Fetch Yahoo Finance insider transactions and store them in PostgreSQL."""

import hashlib
import json
import logging
from collections import defaultdict

import pandas as pd
import yfinance as yf

from airflow.exceptions import AirflowException
from psycopg2 import sql
from psycopg2.extras import execute_values

from .base import YahooFinanceBaseOperator


logger = logging.getLogger(__name__)


class FetchYahooFinanceInsiderTransactions(YahooFinanceBaseOperator):
    """Fetch and upsert insider transaction records."""

    def execute(self, context):
        """Fetch insider transactions from Yahoo Finance."""
        logger.info(
            "Fetching insider transactions for %s",
            self.ticker,
        )

        try:
            insider_transactions = (
                yf.Ticker(self.ticker).insider_transactions
            )

            if (
                insider_transactions is None
                or insider_transactions.empty
            ):
                logger.warning(
                    "No insider transactions for %s",
                    self.ticker,
                )
                return {
                    "status": "no_data",
                    "ticker": self.ticker,
                }

            records_stored = (
                self._store_insider_transactions_in_postgres(
                    insider_transactions
                )
            )

            return {
                "status": "success",
                "ticker": self.ticker,
                "records_retrieved": len(insider_transactions),
                "records_processed": records_stored,
            }

        except Exception as exc:
            logger.exception(
                "Failed to fetch insider transactions for %s",
                self.ticker,
            )
            raise AirflowException(
                f"Insider transactions ingestion failed for "
                f"{self.ticker}: {exc}"
            ) from exc

    def _prepare_rows(self, insider_transactions, db_columns):
        """Normalize transaction metrics and prepare PostgreSQL rows."""

        # Each DataFrame row represents an insider transaction.
        # No transpose is necessary.
        transactions = insider_transactions.copy()

        # Automatically normalize Yahoo Finance column names.
        transactions.columns = [
            self.normalize_metric(column)
            for column in transactions.columns
        ]

        if transactions.columns.has_duplicates:
            raise ValueError(
                "Duplicate insider transaction columns "
                "after normalization"
            )

        # Required source fields.
        required_columns = {
            "insider",
            "start_date",
        }

        missing = required_columns - set(transactions.columns)

        if missing:
            raise ValueError(
                f"Missing insider transaction columns: "
                f"{sorted(missing)}"
            )

        # Verify the PostgreSQL primary key columns.
        required_db_columns = {
            "ticker",
            "date",
            "transaction_id",
        }

        if not required_db_columns.issubset(db_columns):
            raise ValueError(
                "Missing required insider transaction "
                "primary key columns"
            )

        # Exclude metadata and generated identifiers.
        excluded_columns = (
            set(self.METADATA_COLUMNS)
            | {"transaction_id"}
        )

        # Automatically select matching source columns.
        metric_columns = [
            column
            for column in transactions.columns
            if column in db_columns
            and column not in excluded_columns
        ]

        # Log Yahoo Finance fields missing from PostgreSQL.
        skipped = [
            str(column)
            for column in insider_transactions.columns
            if self.normalize_metric(column) not in metric_columns
        ]

        if skipped:
            logger.warning(
                "Skipping insider transaction metrics "
                "for %s: %s",
                self.ticker,
                ", ".join(skipped),
            )

        if not metric_columns:
            raise AirflowException(
                f"No matching insider transaction columns "
                f"for {self.ticker}"
            )

        if not required_columns.issubset(metric_columns):
            raise ValueError(
                "Missing insider or start_date column "
                "in the PostgreSQL schema"
            )

        # One UTC snapshot date for all transaction records.
        snapshot_date = self.snapshot_date()

        rows = []

        # Track repeated, otherwise identical source records.
        seen_hashes = defaultdict(int)

        for _, values in transactions[metric_columns].iterrows():

            row_values = []

            for column, value in values.items():

                if pd.isna(value):
                    row_values.append(None)

                elif column == "start_date":
                    # Convert Yahoo transaction dates to DATE.
                    row_values.append(
                        pd.Timestamp(value).date()
                    )

                elif column == "shares":
                    # Preserve large integer share counts.
                    number = self.clean_scalar(value)

                    if number is None:
                        row_values.append(None)

                    elif (
                        isinstance(number, bool)
                        or number != int(number)
                    ):
                        raise ValueError(
                            f"Invalid insider transaction "
                            f"share count: {number}"
                        )

                    else:
                        row_values.append(int(number))

                elif column == "value":
                    # Transaction values may contain decimals.
                    row_values.append(
                        self.numeric_or_none(value)
                    )

                else:
                    # URL, Text, Insider, Position,
                    # Transaction and Ownership are text.
                    row_values.append(
                        str(value).strip() or None
                    )

            # Build a normalized source record.
            record = dict(zip(metric_columns, row_values))

            # Reject transactions missing their main identifiers.
            if not record.get("insider"):
                raise ValueError(
                    "Missing insider name in transaction record"
                )

            if record.get("start_date") is None:
                raise ValueError(
                    "Missing start date in transaction record"
                )

            # Generate a stable fingerprint from the record values.
            # Sorting JSON keys makes the result independent of
            # the original DataFrame column order.
            payload = json.dumps(
                record,
                sort_keys=True,
                default=str,
                ensure_ascii=False,
                separators=(",", ":"),
            )

            record_hash = hashlib.sha256(
                payload.encode("utf-8")
            ).hexdigest()

            # Preserve identical duplicate source rows as
            # separate occurrences in the same snapshot.
            occurrence = seen_hashes[record_hash]
            seen_hashes[record_hash] += 1

            transaction_id = hashlib.sha256(
                f"{record_hash}:{occurrence}".encode("utf-8")
            ).hexdigest()

            rows.append((
                self.ticker,
                snapshot_date,
                transaction_id,
                *row_values,
            ))

        return metric_columns, rows

    def _store_insider_transactions_in_postgres(
        self,
        insider_transactions,
    ):
        """Upsert transactions using database column matching."""

        conn = self.get_db_connection()

        try:
            with conn.cursor() as cursor:

                # Discover existing PostgreSQL table columns.
                cursor.execute(
                    """
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_schema = %s
                      AND table_name = %s
                    """,
                    ("landing", "yahoo_insider_transactions"),
                )

                db_columns = {
                    row[0] for row in cursor.fetchall()
                }

                if not db_columns:
                    raise ValueError(
                        "Table landing.yahoo_insider_transactions "
                        "does not exist or has no columns"
                    )

                metric_columns, rows = self._prepare_rows(
                    insider_transactions,
                    db_columns,
                )

                if not rows:
                    raise ValueError(
                        "No insider transaction records to insert"
                    )

                # Primary key followed by matching source columns.
                columns = [
                    "ticker",
                    "date",
                    "transaction_id",
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

                # Dynamically construct the PostgreSQL upsert.
                query = sql.SQL("""
                    INSERT INTO {}.{} ({})
                    VALUES %s

                    ON CONFLICT (ticker, date, transaction_id)
                    DO UPDATE SET
                        {},
                        ingested_at = CURRENT_TIMESTAMP,
                        updated_at = CURRENT_TIMESTAMP
                """).format(
                    sql.Identifier("landing"),
                    sql.Identifier("yahoo_insider_transactions"),
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
                "Stored %d insider transactions for %s",
                len(rows),
                self.ticker,
            )

            return len(rows)

        except Exception:
            conn.rollback()
            logger.exception(
                "Error storing insider transactions for %s",
                self.ticker,
            )
            raise

        finally:
            conn.close()