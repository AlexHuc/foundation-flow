"""Fetch Yahoo Finance company fundamentals."""

import json
import logging

import yfinance as yf

from airflow.exceptions import AirflowException
from psycopg2.extras import Json

from .base import YahooFinanceBaseOperator


logger = logging.getLogger(__name__)


class FetchYahooFinanceTickerInfo(YahooFinanceBaseOperator):
    """Fetch and upsert company fundamentals into PostgreSQL."""

    def execute(self, context):
        """Fetch company information and store a snapshot."""
        logger.info("Fetching fundamentals for %s", self.ticker)

        try:
            info = yf.Ticker(self.ticker).info

            if not isinstance(info, dict) or not info:
                logger.warning(
                    "No fundamentals returned for %s", self.ticker
                )
                return {"status": "no_data", "ticker": self.ticker}

            self._store_fundamentals_in_postgres(info)

            return {
                "status": "success",
                "ticker": self.ticker,
                "metrics_retrieved": len(info),
                "records_processed": 1,
            }

        except Exception as exc:
            logger.exception(
                "Failed to fetch fundamentals for %s", self.ticker
            )
            raise AirflowException(
                f"Fundamentals ingestion failed for "
                f"{self.ticker}: {exc}"
            ) from exc

    def _store_fundamentals_in_postgres(self, info):
        """Upsert one fundamentals snapshot."""
        query = """
            INSERT INTO landing.yahoo_info (
                ticker,
                date,
                market_cap,
                pe_ratio,
                dividend_yield,
                earnings_per_share,
                fifty_two_week_high,
                fifty_two_week_low,
                average_volume,
                beta,
                raw_response
            )
            VALUES (
                %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s
            )

            ON CONFLICT (ticker, date) DO UPDATE SET
                market_cap = EXCLUDED.market_cap,
                pe_ratio = EXCLUDED.pe_ratio,
                dividend_yield = EXCLUDED.dividend_yield,
                earnings_per_share = EXCLUDED.earnings_per_share,
                fifty_two_week_high = EXCLUDED.fifty_two_week_high,
                fifty_two_week_low = EXCLUDED.fifty_two_week_low,
                average_volume = EXCLUDED.average_volume,
                beta = EXCLUDED.beta,
                raw_response = EXCLUDED.raw_response,
                ingested_at = CURRENT_TIMESTAMP,
                updated_at = CURRENT_TIMESTAMP
        """

        values = (
            self.ticker,
            self.snapshot_date(),
            self.clean_scalar(info.get("marketCap")),
            self.clean_scalar(info.get("trailingPE")),
            self.clean_scalar(info.get("dividendYield")),
            self.clean_scalar(info.get("trailingEps")),
            self.clean_scalar(info.get("fiftyTwoWeekHigh")),
            self.clean_scalar(info.get("fiftyTwoWeekLow")),
            self.clean_scalar(info.get("averageVolume")),
            self.clean_scalar(info.get("beta")),
            Json(info, dumps=lambda obj: json.dumps(obj, default=str)),
        )

        conn = self.get_db_connection()

        try:
            with conn.cursor() as cursor:
                cursor.execute(query, values)

            conn.commit()

            logger.info(
                "Stored fundamentals for %s", self.ticker
            )

        except Exception:
            conn.rollback()
            logger.exception(
                "Error storing fundamentals for %s", self.ticker
            )
            raise

        finally:
            conn.close()