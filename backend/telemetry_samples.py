from datetime import datetime

from .models import TelemetryEvent, TelemetryOrigin, TelemetrySource

SAMPLE_EVENTS: dict[str, TelemetryEvent] = {
    "network_spike": TelemetryEvent(
        timestamp=datetime.utcnow(),
        source=TelemetrySource.NETWORK,
        origin=TelemetryOrigin.SIMULATOR,
        payload={
            "packet_loss": 12.5,
            "avg_latency_ms": 320.0,
            "nsg_denied_connections": 38,
            "tcp_retry_count": 9,
            "source_ip": "10.0.0.15",
            "destination_ip": "10.0.1.10",
            "destination_port": 443,
        },
        raw_message="Sample network spike event",
    ),
    "app_error": TelemetryEvent(
        timestamp=datetime.utcnow(),
        source=TelemetrySource.APPLICATION,
        origin=TelemetryOrigin.SIMULATOR,
        payload={
            "request_rate_per_min": 1800,
            "error_rate_pct": 12.3,
            "avg_response_ms": 1450.0,
            "p95_response_ms": 2210.0,
            "status_5xx_count": 24,
            "application_name": "customer-api",
        },
        raw_message="Sample application error spike",
    ),
    "db_latency": TelemetryEvent(
        timestamp=datetime.utcnow(),
        source=TelemetrySource.DATABASE,
        origin=TelemetryOrigin.SIMULATOR,
        payload={
            "connection_errors": 11,
            "timeout_count": 7,
            "deadlock_count": 2,
            "avg_query_duration_ms": 3100.0,
            "database_name": "orders-db",
            "cpu_percent": 83.5,
            "worker_count": 14,
        },
        raw_message="Sample database latency and connection failure event",
    ),
}
