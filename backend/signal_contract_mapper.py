"""Map Phase 3 KQL signal rows into normalized TelemetryEvent contract."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from .collectors.kql_utils import parse_utc_timestamp
from .models import (
    TelemetryEvent,
    TelemetryOrigin,
    TelemetryRecordType,
    TelemetrySchemaType,
    TelemetrySource,
)


def _now_utc_naive() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _as_int(value: Any) -> int:
    try:
        if value is None:
            return 0
        return int(float(value))
    except (TypeError, ValueError):
        return 0


def _as_float(value: Any) -> float:
    try:
        if value is None:
            return 0.0
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def map_signal_row_to_telemetry_event(
    query_id: str,
    row: dict[str, Any],
    default_subscription_id: str | None = None,
    default_region: str | None = None,
) -> TelemetryEvent:
    """
    Convert one KQL signal row into normalized TelemetryEvent.
    """
    now_utc = _now_utc_naive()
    timestamp = parse_utc_timestamp(row.get("TimeGenerated"), now_utc)
    resource_id = str(row.get("ResourceId") or "") or None
    operation_name = f"phase3_signal::{query_id}"

    if query_id == "failed_request_rate":
        payload = {
            "application_name": str(row.get("AppName") or "unknown-application"),
            "request_rate_per_min": _as_int(row.get("TotalRequests")),
            "error_rate_pct": _as_float(row.get("FailureRatePct")),
            "avg_response_ms": 0.0,
            "p95_response_ms": None,
            "status_5xx_count": _as_int(row.get("Status5xx")),
            "failed_requests": _as_int(row.get("FailedRequests")),
        }
        return TelemetryEvent(
            timestamp=timestamp,
            source=TelemetrySource.APPLICATION,
            origin=TelemetryOrigin.LOG_ANALYTICS,
            record_type=TelemetryRecordType.METRIC,
            schema_type=TelemetrySchemaType.STANDARD,
            collection_channel="Log Analytics Query API",
            source_system="Application Insights / AppRequests",
            source_category="failed_request_rate_signal",
            payload=payload,
            fields=sorted(row.keys()),
            raw=dict(row),
            resource_id=resource_id,
            subscription_id=default_subscription_id,
            region=default_region,
            operation_name=operation_name,
            correlation_id=str(row.get("CorrelationId") or "") or None,
            raw_message="Phase 3 signal: failed request rate",
        )

    if query_id == "latency_spike":
        payload = {
            "application_name": str(row.get("AppName") or "unknown-application"),
            "request_rate_per_min": _as_int(row.get("Requests")),
            "error_rate_pct": 0.0,
            "avg_response_ms": _as_float(row.get("AvgLatencyMs")),
            "p95_response_ms": _as_float(row.get("P95LatencyMs")),
            "status_5xx_count": 0,
            "p99_response_ms": _as_float(row.get("P99LatencyMs")),
            "max_latency_ms": _as_float(row.get("MaxLatencyMs")),
        }
        return TelemetryEvent(
            timestamp=timestamp,
            source=TelemetrySource.APPLICATION,
            origin=TelemetryOrigin.LOG_ANALYTICS,
            record_type=TelemetryRecordType.METRIC,
            schema_type=TelemetrySchemaType.STANDARD,
            collection_channel="Log Analytics Query API",
            source_system="Application Insights / AppRequests",
            source_category="latency_spike_signal",
            payload=payload,
            fields=sorted(row.keys()),
            raw=dict(row),
            resource_id=resource_id,
            subscription_id=default_subscription_id,
            region=default_region,
            operation_name=operation_name,
            correlation_id=str(row.get("CorrelationId") or "") or None,
            raw_message="Phase 3 signal: latency spike",
        )

    if query_id == "sql_connectivity_errors":
        payload = {
            "database_name": str(row.get("DatabaseName") or "unknown-database"),
            "connection_errors": _as_int(row.get("ConnectivityErrors")),
            "timeout_count": _as_int(row.get("TimeoutCount")),
            "deadlock_count": _as_int(row.get("DeadlockCount")),
            "avg_query_duration_ms": 0.0,
            "cpu_percent": None,
            "worker_count": None,
            "connectivity_error_rate_pct": _as_float(row.get("ConnectivityErrorRatePct")),
            "total_events": _as_int(row.get("TotalEvents")),
        }
        return TelemetryEvent(
            timestamp=timestamp,
            source=TelemetrySource.DATABASE,
            origin=TelemetryOrigin.AZURE_MONITOR_DIAGNOSTICS,
            record_type=TelemetryRecordType.EVENT,
            schema_type=TelemetrySchemaType.STANDARD,
            collection_channel="Log Analytics Query API",
            source_system="Azure SQL Diagnostics",
            source_category="sql_connectivity_signal",
            payload=payload,
            fields=sorted(row.keys()),
            raw=dict(row),
            resource_id=resource_id,
            subscription_id=default_subscription_id,
            region=default_region,
            operation_name=operation_name,
            correlation_id=str(row.get("CorrelationId") or "") or None,
            raw_message="Phase 3 signal: SQL connectivity/deadlock/timeout",
        )

    if query_id == "nsg_deny_packet_drop":
        payload = {
            "packet_loss": 0.0,
            "avg_latency_ms": 0.0,
            "nsg_denied_connections": _as_int(row.get("DeniedEvents")),
            "tcp_retry_count": _as_int(row.get("DropLikeEvents")),
            "source_ip": str(row.get("SrcIP") or "") or None,
            "destination_ip": str(row.get("DestIP") or "") or None,
            "destination_port": _as_int(row.get("DestPort")) or None,
            "deny_rate_pct": _as_float(row.get("DenyRatePct")),
            "total_events": _as_int(row.get("TotalEvents")),
        }
        return TelemetryEvent(
            timestamp=timestamp,
            source=TelemetrySource.NETWORK,
            origin=TelemetryOrigin.AZURE_MONITOR_DIAGNOSTICS,
            record_type=TelemetryRecordType.EVENT,
            schema_type=TelemetrySchemaType.STANDARD,
            collection_channel="Log Analytics Query API",
            source_system="Azure Network Diagnostics",
            source_category="nsg_deny_drop_signal",
            payload=payload,
            fields=sorted(row.keys()),
            raw=dict(row),
            resource_id=resource_id,
            subscription_id=default_subscription_id,
            region=default_region,
            operation_name=operation_name,
            correlation_id=str(row.get("CorrelationId") or "") or None,
            raw_message="Phase 3 signal: NSG deny/drop-like pattern",
        )

    raise ValueError(f"Unsupported signal query id: {query_id}")

