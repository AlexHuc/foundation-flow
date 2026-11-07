"""Fetch Yahoo Finance fast_info market snapshots."""

import logging

import yfinance as yf

from airflow.exceptions import AirflowException

from .base import YahooFinanceBaseOperator


logger = logging.getLogger(__name__)


# (Yahoo Finance field, PostgreSQL column)
FAST_INFO_FIELDS = (
    ("currency", "currency"),
    ("dayHigh", "day_high"),
    ("dayLow", "day_low"),
    ("exchange", "exchange"),
    ("fiftyDayAverage", "fifty_day_average"),
    ("lastPrice", "last_price"),
    ("lastVolume", "last_volume"),
    ("marketCap", "market_cap"),
    ("open", "open"),
    ("previousClose", "previous_close"),
    ("quoteType", "quote_type"),
    ("regularMarketPreviousClose", "regular_market_previous_close"),
    ("shares", "shares"),
    ("tenDayAverageVolume", "ten_day_average_volume"),
    ("threeMonthAverageVolume", "three_month_average_volume"),
    ("timezone", "timezone"),
    ("twoHundredDayAverage", "two_hundred_day_average"),
    ("yearChange", "year_change"),
    ("yearHigh", "year_high"),
    ("yearLow", "year_low"),
)


class FetchYahooFinanceTickerFastInfo(YahooFinanceBaseOperator):
    """Fetch and upsert fast_info snapshots into PostgreSQL."""

    def execute(self, context):
        """Fetch, extract, and store fast_info metrics."""
        logger.info("Fetching fast_info for %s", self.ticker)

        try:
            fast_info = yf.Ticker(self.ticker).fast_info

            if fast_info is None:
                return {"status": "no_data", "ticker": self.ticker}

            values = self._extract_values(fast_info)

            metrics_retrieved = sum(
                value is not None for value in values
            )

            if metrics_retrieved == 0:
                logger.warning(
                    "No usable fast_info metrics for %s", self.ticker
                )
                return {"status": "no_data", "ticker": self.ticker}

            self._store_fast_info_in_postgres(values)

            return {
                "status": "success",
                "ticker": self.ticker,
                "metrics_retrieved": metrics_retrieved,
                "records_processed": 1,
            }

        except Exception as exc:
            logger.exception(
                "Failed to fetch fast_info for %s", self.ticker
            )
            raise AirflowException(
                f"Fast info ingestion failed for {self.ticker}: {exc}"
            ) from exc

    def _extract_values(self, fast_info):
        """Read individual fields from yfinance's lazy FastInfo."""
        values = []

        for yahoo_key, _ in FAST_INFO_FIELDS:
            try:
                value = fast_info.get(yahoo_key)
                values.append(self.clean_scalar(value))

            except Exception:
                logger.warning(
                    "Could not retrieve fast_info field %s for %s",
                    yahoo_key,
                    self.ticker,
                    exc_info=True,
                )
                values.append(None)

        return values

    def _store_fast_info_in_postgres(self, values):
        """Upsert one fast_info snapshot."""
        columns = [
            "ticker",
            "date",
            *(column for _, column in FAST_INFO_FIELDS),
        ]

        placeholders = ", ".join(["%s"] * len(columns))

        update_columns = [
            column for _, column in FAST_INFO_FIELDS
        ]

        assignments = ", ".join(
            f"{column} = EXCLUDED.{column}"
            for column in update_columns
        )

        # Column names above come exclusively from this module's
        # constant FAST_INFO_FIELDS, not from external API data.
        query = f"""
            INSERT INTO landing.yahoo_fast_info (
                {", ".join(columns)}
            )
            VALUES ({placeholders})

            ON CONFLICT (ticker, date) DO UPDATE SET
                {assignments},
                ingested_at = CURRENT_TIMESTAMP,
                updated_at = CURRENT_TIMESTAMP
        """

        params = (
            self.ticker,
            self.snapshot_date(),
            *values,
        )

        conn = self.get_db_connection()

        try:
            with conn.cursor() as cursor:
                cursor.execute(query, params)

            conn.commit()

            logger.info(
                "Stored fast_info snapshot for %s", self.ticker
            )

        except Exception:
            conn.rollback()
            logger.exception(
                "Error storing fast_info for %s", self.ticker
            )
            raise

        finally:
            conn.close()