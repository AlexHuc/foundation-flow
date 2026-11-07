"""Base operator for Yahoo Finance ingestion."""

import math
import re

from datetime import datetime, timezone

from airflow.models import BaseOperator
from airflow.providers.postgres.hooks.postgres import PostgresHook


class YahooFinanceBaseOperator(BaseOperator):
    """Common functionality for Yahoo Finance operators."""

    METADATA_COLUMNS = frozenset({
        "ticker",
        "date",
        "ingested_at",
        "created_at",
        "updated_at",
    })

    def __init__(
        self,
        ticker: str,
        postgres_conn_id: str = "postgres_landing",
        **kwargs,
    ):
        super().__init__(**kwargs)

        if not ticker or not ticker.strip():
            raise ValueError("ticker must not be empty")

        self.ticker = ticker.strip().upper()
        self.postgres_conn_id = postgres_conn_id

    def get_db_connection(self):
        """Return a PostgreSQL connection from Airflow."""
        hook = PostgresHook(
            postgres_conn_id=self.postgres_conn_id
        )
        return hook.get_conn()

    @staticmethod
    def snapshot_date():
        """Return the current UTC date."""
        return datetime.now(timezone.utc).date()

    @staticmethod
    def clean_scalar(value):
        """Convert missing and NumPy scalar values for PostgreSQL."""
        if value is None:
            return None

        if hasattr(value, "item"):
            try:
                value = value.item()
            except (TypeError, ValueError, AttributeError):
                pass

        if isinstance(value, float) and not math.isfinite(value):
            return None

        return value

    @staticmethod
    def normalize_metric(name):
        """Convert Yahoo Finance metric names to snake_case."""
        normalized = re.sub(
            r"[^a-zA-Z0-9]+",
            "_",
            str(name).strip().lower(),
        )
        return re.sub(r"_+", "_", normalized).strip("_")