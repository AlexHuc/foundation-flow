"""Fetch Yahoo Finance calendar events and analyst estimates and store them in PostgreSQL."""

import logging

from datetime import date

import pandas as pd
import yfinance as yf

from airflow.exceptions import AirflowException

from .base import YahooFinanceBaseOperator


logger = logging.getLogger(__name__)


class FetchYahooFinanceCalendar(YahooFinanceBaseOperator):
    """Fetch and store Yahoo Finance calendar snapshots."""

    @staticmethod
    def _parse_date(value):
        """Convert Yahoo date values to Python date objects."""
        if value is None or pd.isna(value):
            return None

        return pd.Timestamp(value).date()

    @classmethod
    def _parse_earnings_dates(cls, value):
        """Convert one or multiple earnings dates to a date list."""
        if value is None:
            return None

        if not isinstance(value, (list, tuple)):
            value = [value]

        dates = [
            cls._parse_date(item)
            for item in value
        ]

        return [
            item for item in dates
            if item is not None
        ]

    def execute(self, context):
        """Fetch and store the current calendar snapshot."""
        logger.info(
            "Fetching Yahoo Finance calendar for %s",
            self.ticker,
        )

        try:
            calendar = yf.Ticker(self.ticker).calendar

            if not isinstance(calendar, dict) or not calendar:
                logger.warning(
                    "No calendar data returned for %s",
                    self.ticker,
                )
                return {
                    "status": "no_data",
                    "ticker": self.ticker,
                }

            self._store_calendar_in_postgres(calendar)

            return {
                "status": "success",
                "ticker": self.ticker,
                "metrics_retrieved": len(calendar),
                "records_processed": 1,
            }

        except Exception as exc:
            logger.exception(
                "Error fetching calendar data for %s",
                self.ticker,
            )
            raise AirflowException(
                f"Failed to fetch calendar data "
                f"for {self.ticker}: {exc}"
            ) from exc

    def _store_calendar_in_postgres(self, calendar):
        """Insert or update a daily calendar snapshot."""

        # Convert Yahoo Finance values into PostgreSQL-compatible
        # Python values.
        values = (
            self.ticker,
            self.snapshot_date(),

            # Dividend events.
            self._parse_date(
                calendar.get("Dividend Date")
            ),
            self._parse_date(
                calendar.get("Ex-Dividend Date")
            ),

            # Earnings dates can contain multiple dates.
            self._parse_earnings_dates(
                calendar.get("Earnings Date")
            ),

            # Earnings estimates.
            self.clean_scalar(
                calendar.get("Earnings High")
            ),
            self.clean_scalar(
                calendar.get("Earnings Low")
            ),
            self.clean_scalar(
                calendar.get("Earnings Average")
            ),

            # Revenue estimates.
            self.clean_scalar(
                calendar.get("Revenue High")
            ),
            self.clean_scalar(
                calendar.get("Revenue Low")
            ),
            self.clean_scalar(
                calendar.get("Revenue Average")
            ),
        )

        query = """
            INSERT INTO landing.yahoo_calendar (
                ticker,
                date,
                dividend_date,
                ex_dividend_date,
                earnings_dates,
                earnings_high,
                earnings_low,
                earnings_average,
                revenue_high,
                revenue_low,
                revenue_average
            )
            VALUES (
                %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s
            )

            ON CONFLICT (ticker, date) DO UPDATE SET
                dividend_date = EXCLUDED.dividend_date,
                ex_dividend_date = EXCLUDED.ex_dividend_date,
                earnings_dates = EXCLUDED.earnings_dates,
                earnings_high = EXCLUDED.earnings_high,
                earnings_low = EXCLUDED.earnings_low,
                earnings_average = EXCLUDED.earnings_average,
                revenue_high = EXCLUDED.revenue_high,
                revenue_low = EXCLUDED.revenue_low,
                revenue_average = EXCLUDED.revenue_average,
                ingested_at = CURRENT_TIMESTAMP,
                updated_at = CURRENT_TIMESTAMP
        """

        conn = self.get_db_connection()

        try:
            with conn.cursor() as cursor:
                cursor.execute(query, values)

            conn.commit()

            logger.info(
                "Stored calendar snapshot for %s",
                self.ticker,
            )

        except Exception:
            conn.rollback()
            logger.exception(
                "Error storing calendar data for %s",
                self.ticker,
            )
            raise

        finally:
            conn.close()