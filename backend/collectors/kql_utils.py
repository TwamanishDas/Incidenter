"""Helpers for transforming Azure Monitor query results."""

from datetime import datetime, timezone
from typing import Any


def rows_as_dicts(query_result: Any) -> list[dict[str, Any]]:
    """Convert first result table to list[dict] keyed by column name."""
    if not getattr(query_result, "tables", None):
        return []
    table = query_result.tables[0]
    column_names = [column.name for column in table.columns]
    return [dict(zip(column_names, row)) for row in table.rows]


def to_utc_naive(value: datetime) -> datetime:
    """
    Normalize datetime to naive UTC for consistent in-process comparisons/storage.
    """
    if value.tzinfo is None:
        return value
    return value.astimezone(timezone.utc).replace(tzinfo=None)


def parse_utc_timestamp(value: Any, fallback: datetime) -> datetime:
    """Parse datetime from query row value with safe fallback."""
    fallback_norm = to_utc_naive(fallback)
    if isinstance(value, datetime):
        return to_utc_naive(value)
    if isinstance(value, str):
        try:
            # Handles "YYYY-MM-DDTHH:MM:SS(.fff)Z" and offset strings.
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            return to_utc_naive(parsed)
        except ValueError:
            return fallback_norm
    return fallback_norm


def as_int(value: Any, default: int = 0) -> int:
    try:
        if value is None:
            return default
        return int(float(value))
    except (TypeError, ValueError):
        return default


def as_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default
