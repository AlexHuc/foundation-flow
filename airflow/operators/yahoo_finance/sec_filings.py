"""Fetch Yahoo Finance SEC filings and store them in PostgreSQL."""

import logging
from datetime import date, datetime

import pandas as pd
import yfinance as yf

from airflow.exceptions import AirflowException
from psycopg2 import sql
from psycopg2.extras import Json, execute_values

from .base import YahooFinanceBaseOperator


logger = logging.getLogger(__name__)


class FetchYahooFinanceSECFilings(YahooFinanceBaseOperator):
    """Fetch and upsert SEC filing metadata from Yahoo Finance."""

    def execute(self, context):
        """Fetch SEC filings from Yahoo Finance."""
        logger.info(
            "Fetching SEC filings for %s",
            self.ticker,
        )

        try:
            sec_filings = yf.Ticker(self.ticker).sec_filings

            if sec_filings is None or len(sec_filings) == 0:
                logger.warning(
                    "No SEC filings returned for %s",
                    self.ticker,
                )
                return {
                    "status": "no_data",
                    "ticker": self.ticker,
                }

            records_stored = self._store_sec_filings_in_postgres(
                sec_filings
            )

            return {
                "status": "success",
                "ticker": self.ticker,
                "records_retrieved": len(sec_filings),
                "records_processed": records_stored,
            }

        except Exception as exc:
            logger.exception(
                "Failed to fetch SEC filings for %s",
                self.ticker,
            )
            raise AirflowException(
                f"SEC filings ingestion failed for "
                f"{self.ticker}: {exc}"
            ) from exc

    def _prepare_rows(self, sec_filings, db_columns):
        """Normalize filing dictionaries and prepare PostgreSQL rows."""

        # Validate required PostgreSQL primary key columns.
        required_db_columns = {
            "ticker",
            "date",
            "edgar_url",
            "filing_date",
        }

        if not required_db_columns.issubset(db_columns):
            raise ValueError(
                "Missing required SEC filings PostgreSQL columns"
            )

        if not isinstance(sec_filings, (list, tuple)):
            raise ValueError(
                "SEC filings must be a list or tuple of dictionaries"
            )

        # Convert each filing dictionary into normalized fields.
        normalized_filings = []

        for filing in sec_filings:

            if not isinstance(filing, dict):
                raise ValueError(
                    "Invalid SEC filing: expected a dictionary"
                )

            normalized = {}

            for key, value in filing.items():

                # Automatically normalize Yahoo Finance keys.
                column = self.normalize_metric(key)

                # Source 'date' is the SEC filing date.
                # PostgreSQL 'date' is our ingestion snapshot.
                if column == "date":
                    column = "filing_date"

                if column in normalized:
                    raise ValueError(
                        "Duplicate SEC filing field "
                        f"after normalization: {column}"
                    )

                normalized[column] = value

            normalized_filings.append(normalized)

        # Discover all available normalized source fields,
        # preserving their initial appearance order.
        source_columns = list(
            dict.fromkeys(
                column
                for filing in normalized_filings
                for column in filing
            )
        )

        # Fields already represented in the primary key.
        key_columns = {
            "edgar_url",
            "filing_date",
        }

        # Automatically match fields against PostgreSQL.
        metric_columns = [
            column
            for column in source_columns
            if column in db_columns
            and column not in self.METADATA_COLUMNS
            and column not in key_columns
        ]

        # Log source fields not available in PostgreSQL.
        skipped = [
            column
            for column in source_columns
            if column not in db_columns
        ]

        if skipped:
            logger.warning(
                "Skipping SEC filing fields for %s: %s",
                self.ticker,
                ", ".join(skipped),
            )

        if not metric_columns:
            raise AirflowException(
                f"No matching SEC filing metadata columns "
                f"for {self.ticker}"
            )

        # Every filing belongs to the same UTC ingestion snapshot.
        snapshot_date = self.snapshot_date()

        rows = []
        seen_filings = set()

        for filing in normalized_filings:

            # Validate the source filing URL.
            edgar_url = filing.get("edgar_url")

            if edgar_url is None or pd.isna(edgar_url):
                raise ValueError(
                    "SEC filing is missing edgar_url"
                )

            edgar_url = str(edgar_url).strip()

            if not edgar_url:
                raise ValueError(
                    "SEC filing edgar_url cannot be empty"
                )

            # Validate the original filing date.
            filing_date = filing.get("filing_date")

            if filing_date is None or pd.isna(filing_date):
                raise ValueError(
                    f"Missing filing date for {edgar_url}"
                )

            filing_date = pd.Timestamp(filing_date).date()

            # Prevent duplicate primary keys in one batch.
            if edgar_url in seen_filings:
                raise ValueError(
                    f"Duplicate SEC filing URL: {edgar_url}"
                )

            seen_filings.add(edgar_url)

            row_values = []

            for column in metric_columns:
                value = filing.get(column)

                if value is None:
                    row_values.append(None)
                    continue

                if column == "exhibits":
                    # Preserve the complete nested dictionary.
                    # Empty dictionaries are stored as {}, not NULL.
                    if not isinstance(value, dict):
                        raise ValueError(
                            f"Invalid exhibits for {edgar_url}: "
                            "expected a dictionary"
                        )

                    row_values.append(Json(value))

                elif column in ("epoch_date", "max_age"):
                    # Unix timestamps and response age
                    # are integer values.
                    if pd.isna(value):
                        row_values.append(None)
                        continue

                    number = self.clean_scalar(value)

                    if (
                        isinstance(number, bool)
                        or number != int(number)
                    ):
                        raise ValueError(
                            f"Invalid {column} for {edgar_url}: "
                            f"{number}"
                        )

                    row_values.append(int(number))

                elif column in ("type", "title"):
                    if pd.isna(value):
                        row_values.append(None)
                    else:
                        row_values.append(
                            str(value).strip() or None
                        )

                elif isinstance(value, (date, datetime)):
                    # For any additional date-like field
                    # automatically matched in PostgreSQL.
                    row_values.append(value)

                elif pd.isna(value):
                    row_values.append(None)

                else:
                    # Preserve other source scalar values.
                    row_values.append(
                        self.clean_scalar(value)
                    )

            rows.append((
                self.ticker,
                snapshot_date,
                edgar_url,
                filing_date,
                *row_values,
            ))

        return metric_columns, rows

    def _store_sec_filings_in_postgres(self, sec_filings):
        """Upsert SEC filings using dynamic PostgreSQL column matching."""

        conn = self.get_db_connection()

        try:
            with conn.cursor() as cursor:

                # Discover columns in the PostgreSQL table.
                cursor.execute(
                    """
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_schema = %s
                      AND table_name = %s
                    """,
                    ("landing", "yahoo_sec_filings"),
                )

                db_columns = {
                    row[0] for row in cursor.fetchall()
                }

                if not db_columns:
                    raise ValueError(
                        "Table landing.yahoo_sec_filings "
                        "does not exist or has no columns"
                    )

                metric_columns, rows = self._prepare_rows(
                    sec_filings,
                    db_columns,
                )

                if not rows:
                    raise ValueError(
                        "No SEC filing records to insert"
                    )

                # Primary key fields and matching source metrics.
                columns = [
                    "ticker",
                    "date",
                    "edgar_url",
                    "filing_date",
                    *metric_columns,
                ]

                # Update the original filing date and all metrics.
                update_columns = [
                    "filing_date",
                    *metric_columns,
                ]

                # Dynamically generate UPDATE assignments.
                updates = sql.SQL(", ").join(
                    sql.SQL("{} = EXCLUDED.{}").format(
                        sql.Identifier(column),
                        sql.Identifier(column),
                    )
                    for column in update_columns
                )

                # Dynamically generate the PostgreSQL upsert.
                query = sql.SQL("""
                    INSERT INTO {}.{} ({})
                    VALUES %s

                    ON CONFLICT (ticker, date, edgar_url)
                    DO UPDATE SET
                        {},
                        ingested_at = CURRENT_TIMESTAMP,
                        updated_at = CURRENT_TIMESTAMP
                """).format(
                    sql.Identifier("landing"),
                    sql.Identifier("yahoo_sec_filings"),
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
                "Stored %d SEC filings for %s",
                len(rows),
                self.ticker,
            )

            return len(rows)

        except Exception:
            conn.rollback()
            logger.exception(
                "Error storing SEC filings for %s",
                self.ticker,
            )
            raise

        finally:
            conn.close()