"""Convert asyncpg records into JSON-safe dictionaries."""

from datetime import date, datetime
from decimal import Decimal
from typing import Any

import asyncpg


def _value(value: Any) -> Any:
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, list):
        return [_value(v) for v in value]
    return value


def row_to_dict(record: asyncpg.Record) -> dict[str, Any]:
    return {key: _value(record[key]) for key in record.keys()}


def rows_to_dicts(records: list[asyncpg.Record]) -> list[dict[str, Any]]:
    return [row_to_dict(r) for r in records]
