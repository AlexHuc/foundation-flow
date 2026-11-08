"""Base operator for Yahoo Finance ingestion."""

import pandas as pd
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
        "period",
        "quarter",
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

        name = str(name).strip()

        # Handle camelCase and PascalCase.
        name = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1_\2", name)
        name = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", name)

        # Replace spaces and special characters with underscores.
        name = re.sub(r"[^a-zA-Z0-9]+", "_", name)

        # Remove duplicate and surrounding underscores.
        return re.sub(r"_+", "_", name).strip("_").lower()

    @classmethod
    def numeric_or_none(cls, value):
        """Convert missing numeric values to PostgreSQL NULL."""

        if pd.isna(value):
            return None

        value = cls.clean_scalar(value)

        return None if value is None else float(value)