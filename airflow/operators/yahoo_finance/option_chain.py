"""Fetch Yahoo Finance option chains and store them in PostgreSQL."""

import logging

import pandas as pd
import yfinance as yf

from airflow.exceptions import AirflowException
from psycopg2 import sql
from psycopg2.extras import execute_values

from .base import YahooFinanceBaseOperator


logger = logging.getLogger(__name__)


class FetchYahooFinanceOptionChain(YahooFinanceBaseOperator):
    """Fetch and upsert call and put option chains."""

    def execute(self, context):
        """Fetch option chains for all available expiration dates."""
        logger.info(
            "Fetching option chains for %s",
            self.ticker,
        )

        try:
            stock = yf.Ticker(self.ticker)

            # Retrieve every currently available expiration date.
            expirations = stock.options

            if not expirations:
                logger.warning(
                    "No option expiration dates for %s",
                    self.ticker,
                )
                return {
                    "status": "no_data",
                    "ticker": self.ticker,
                }

            frames = []

            for expiration in expirations:
                logger.info(
                    "Fetching option chain for %s, expiration %s",
                    self.ticker,
                    expiration,
                )

                chain = stock.option_chain(expiration)

                # Retrieve both call and put options.
                for option_type, contracts in (
                    ("CALL", chain.calls),
                    ("PUT", chain.puts),
                ):
                    if contracts is None or contracts.empty:
                        logger.info(
                            "No %s contracts for %s, expiration %s",
                            option_type,
                            self.ticker,
                            expiration,
                        )
                        continue

                    contracts = contracts.copy()

                    # These fields come from the retrieval context.
                    contracts["expiration"] = pd.Timestamp(
                        expiration
                    ).date()

                    contracts["option_type"] = option_type

                    frames.append(contracts)

            if not frames:
                logger.warning(
                    "No option contracts returned for %s",
                    self.ticker,
                )
                return {
                    "status": "no_data",
                    "ticker": self.ticker,
                    "expirations_retrieved": len(expirations),
                }

            # Calls and puts share the same financial metric schema.
            option_chain = pd.concat(
                frames,
                ignore_index=True,
                sort=False,
            )

            records_stored = self._store_option_chain_in_postgres(
                option_chain
            )

            return {
                "status": "success",
                "ticker": self.ticker,
                "expirations_retrieved": len(expirations),
                "records_retrieved": len(option_chain),
                "records_processed": records_stored,
            }

        except Exception as exc:
            logger.exception(
                "Failed to fetch option chains for %s",
                self.ticker,
            )
            raise AirflowException(
                f"Option chain ingestion failed for "
                f"{self.ticker}: {exc}"
            ) from exc

    def _prepare_rows(self, option_chain, db_columns):
        """Normalize option metrics and prepare PostgreSQL rows."""

        # Each row represents an individual option contract.
        # No transpose is necessary.
        contracts = option_chain.copy()

        # Automatically normalize Yahoo Finance column names.
        contracts.columns = [
            self.normalize_metric(column)
            for column in contracts.columns
        ]

        if contracts.columns.has_duplicates:
            raise ValueError(
                "Duplicate option chain columns after normalization"
            )

        # Columns identifying an option contract.
        key_columns = {
            "contract_symbol",
            "expiration",
            "option_type",
        }

        # Validate required columns.
        missing = key_columns - set(contracts.columns)

        if missing:
            raise ValueError(
                f"Missing option chain columns: {sorted(missing)}"
            )

        # Validate PostgreSQL primary key and identifier columns.
        required_db_columns = {
            "ticker",
            "date",
            *key_columns,
        }

        if not required_db_columns.issubset(db_columns):
            raise ValueError(
                "Missing required PostgreSQL option chain columns"
            )

        # Automatically select metrics matching PostgreSQL.
        metric_columns = [
            column
            for column in contracts.columns
            if column in db_columns
            and column not in self.METADATA_COLUMNS
            and column not in key_columns
        ]

        # Identify metrics missing from PostgreSQL.
        skipped = [
            str(column)
            for column in option_chain.columns
            if self.normalize_metric(column) not in metric_columns
            and self.normalize_metric(column) not in key_columns
        ]

        if skipped:
            logger.warning(
                "Skipping option chain metrics for %s: %s",
                self.ticker,
                ", ".join(skipped),
            )

        if not metric_columns:
            raise AirflowException(
                f"No matching option chain metrics for {self.ticker}"
            )

        snapshot_date = self.snapshot_date()

        rows = []
        seen_contracts = set()

        for _, values in contracts.iterrows():

            # Validate the contract symbol.
            contract_symbol = values["contract_symbol"]

            if pd.isna(contract_symbol):
                raise ValueError(
                    "Missing option contract symbol"
                )

            contract_symbol = str(contract_symbol).strip()

            if not contract_symbol:
                raise ValueError(
                    "Option contract symbol cannot be empty"
                )

            # Validate expiration date.
            expiration = values["expiration"]

            if pd.isna(expiration):
                raise ValueError(
                    f"Missing expiration for {contract_symbol}"
                )

            expiration_date = pd.Timestamp(expiration).date()

            # Validate option type.
            option_type = str(values["option_type"]).strip()

            if option_type not in ("CALL", "PUT"):
                raise ValueError(
                    f"Invalid option type: {option_type}"
                )

            # Prevent duplicate primary keys in the same batch.
            if contract_symbol in seen_contracts:
                raise ValueError(
                    f"Duplicate option contract: {contract_symbol}"
                )

            seen_contracts.add(contract_symbol)

            row_values = []

            for column in metric_columns:
                value = values[column]

                if pd.isna(value):
                    row_values.append(None)

                elif column == "last_trade_date":
                    # Preserve timezone-aware trade timestamps.
                    timestamp = pd.Timestamp(value)

                    if timestamp.tzinfo is None:
                        raise ValueError(
                            "Timezone-naive last trade date "
                            f"for contract {contract_symbol}"
                        )

                    row_values.append(
                        timestamp.to_pydatetime()
                    )

                elif column in ("volume", "open_interest"):
                    # Contract counts must be whole numbers.
                    number = self.numeric_or_none(value)

                    if number is None:
                        row_values.append(None)

                    elif number < 0 or not number.is_integer():
                        raise ValueError(
                            f"Invalid {column} for "
                            f"{contract_symbol}: {number}"
                        )

                    else:
                        row_values.append(int(number))

                elif column == "in_the_money":
                    # Preserve the Boolean value.
                    boolean_value = self.clean_scalar(value)

                    if not isinstance(boolean_value, bool):
                        raise ValueError(
                            f"Invalid in_the_money value "
                            f"for {contract_symbol}: {value}"
                        )

                    row_values.append(boolean_value)

                elif column in ("contract_size", "currency"):
                    # Text fields.
                    row_values.append(
                        str(value).strip() or None
                    )

                else:
                    # Prices, strike, change, and volatility.
                    row_values.append(
                        self.numeric_or_none(value)
                    )

            rows.append((
                self.ticker,
                snapshot_date,
                contract_symbol,
                expiration_date,
                option_type,
                *row_values,
            ))

        return metric_columns, rows

    def _store_option_chain_in_postgres(self, option_chain):
        """Upsert option contracts using database column matching."""

        conn = self.get_db_connection()

        try:
            with conn.cursor() as cursor:

                # Discover PostgreSQL columns.
                cursor.execute(
                    """
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_schema = %s
                      AND table_name = %s
                    """,
                    ("landing", "yahoo_option_chain"),
                )

                db_columns = {
                    row[0] for row in cursor.fetchall()
                }

                if not db_columns:
                    raise ValueError(
                        "Table landing.yahoo_option_chain "
                        "does not exist or has no columns"
                    )

                metric_columns, rows = self._prepare_rows(
                    option_chain,
                    db_columns,
                )

                if not rows:
                    raise ValueError(
                        "No option chain contracts to insert"
                    )

                # Primary key, contract identifiers, and metrics.
                columns = [
                    "ticker",
                    "date",
                    "contract_symbol",
                    "expiration",
                    "option_type",
                    *metric_columns,
                ]

                # Update contract identifiers and matching metrics.
                update_columns = [
                    "expiration",
                    "option_type",
                    *metric_columns,
                ]

                updates = sql.SQL(", ").join(
                    sql.SQL("{} = EXCLUDED.{}").format(
                        sql.Identifier(column),
                        sql.Identifier(column),
                    )
                    for column in update_columns
                )

                query = sql.SQL("""
                    INSERT INTO {}.{} ({})
                    VALUES %s

                    ON CONFLICT (ticker, date, contract_symbol)
                    DO UPDATE SET
                        {},
                        ingested_at = CURRENT_TIMESTAMP,
                        updated_at = CURRENT_TIMESTAMP
                """).format(
                    sql.Identifier("landing"),
                    sql.Identifier("yahoo_option_chain"),
                    sql.SQL(", ").join(
                        map(sql.Identifier, columns)
                    ),
                    updates,
                )

                # Insert or update contracts in batches.
                execute_values(
                    cursor,
                    query.as_string(conn),
                    rows,
                    page_size=1000,
                )

            conn.commit()

            logger.info(
                "Stored %d option contracts for %s",
                len(rows),
                self.ticker,
            )

            return len(rows)

        except Exception:
            conn.rollback()
            logger.exception(
                "Error storing option chains for %s",
                self.ticker,
            )
            raise

        finally:
            conn.close()