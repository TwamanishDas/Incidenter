from datetime import datetime
import uuid

from .models import (
    ApplicationPayload,
    DatabasePayload,
    Incident,
    NetworkPayload,
    RCALink,
    Severity,
    TelemetryEvent,
    TelemetrySource,
)


def evaluate_network_event(event: TelemetryEvent) -> Incident | None:
    payload = NetworkPayload(**event.payload)
    evidence: list[RCALink] = []

    if payload.nsg_denied_connections > 10:
        evidence.append(RCALink(evidence="High NSG denied connection count", severity=Severity.CRITICAL))
    if payload.packet_loss >= 5.0:
        evidence.append(RCALink(evidence="Packet loss above 5%", severity=Severity.CRITICAL))
    if payload.avg_latency_ms >= 200.0:
        evidence.append(RCALink(evidence="High average network latency", severity=Severity.WARNING))
    if payload.tcp_retry_count >= 5:
        evidence.append(RCALink(evidence="TCP retries indicate connectivity issues", severity=Severity.WARNING))

    if not evidence:
        return None

    severity = Severity.CRITICAL if any(item.severity == Severity.CRITICAL for item in evidence) else Severity.WARNING
    return Incident(
        id=str(uuid.uuid4()),
        incident_type=TelemetrySource.NETWORK,
        title="Network incident detected",
        description="A network telemetry pattern indicates connectivity or packet flow degradation.",
        severity=severity,
        likely_root_cause="Network path or security rule issue",
        affected_component="Network layer",
        evidence=evidence,
        supporting_data=payload.model_dump(),
    )


def evaluate_application_event(event: TelemetryEvent) -> Incident | None:
    payload = ApplicationPayload(**event.payload)
    evidence: list[RCALink] = []

    if payload.error_rate_pct >= 5.0 or payload.status_5xx_count >= 10:
        evidence.append(RCALink(evidence="Application error rate exceeds threshold", severity=Severity.CRITICAL))
    if payload.avg_response_ms >= 1000.0:
        evidence.append(RCALink(evidence="Average response latency exceeds 1000 ms", severity=Severity.WARNING))
    if payload.p95_response_ms and payload.p95_response_ms >= 2000.0:
        evidence.append(RCALink(evidence="P95 latency spike detected", severity=Severity.WARNING))

    if not evidence:
        return None

    severity = Severity.CRITICAL if any(item.severity == Severity.CRITICAL for item in evidence) else Severity.WARNING
    return Incident(
        id=str(uuid.uuid4()),
        incident_type=TelemetrySource.APPLICATION,
        title="Application incident detected",
        description="Application telemetry shows increased errors or request latency.",
        severity=severity,
        likely_root_cause="Application code, dependency failure, or backend service degradation",
        affected_component=payload.application_name or "Application service",
        evidence=evidence,
        supporting_data=payload.model_dump(),
    )


def evaluate_database_event(event: TelemetryEvent) -> Incident | None:
    payload = DatabasePayload(**event.payload)
    evidence: list[RCALink] = []

    if payload.connection_errors >= 5:
        evidence.append(RCALink(evidence="Database connection error spike.", severity=Severity.CRITICAL))
    if payload.timeout_count >= 3:
        evidence.append(RCALink(evidence="Database query timeouts observed.", severity=Severity.WARNING))
    if payload.deadlock_count >= 1:
        evidence.append(RCALink(evidence="Deadlocks found in database workload.", severity=Severity.WARNING))
    if payload.avg_query_duration_ms >= 2000.0:
        evidence.append(RCALink(evidence="Average query duration is very high.", severity=Severity.WARNING))

    if not evidence:
        return None

    severity = Severity.CRITICAL if any(item.severity == Severity.CRITICAL for item in evidence) else Severity.WARNING
    return Incident(
        id=str(uuid.uuid4()),
        incident_type=TelemetrySource.DATABASE,
        title="Database incident detected",
        description="Database telemetry indicates connection or performance issues.",
        severity=severity,
        likely_root_cause="Database resource, connection limit, or query performance issue",
        affected_component=payload.database_name or "Database service",
        evidence=evidence,
        supporting_data=payload.model_dump(),
    )


def analyze_telemetry(event: TelemetryEvent) -> Incident | None:
    if event.source == TelemetrySource.NETWORK:
        return evaluate_network_event(event)
    if event.source == TelemetrySource.APPLICATION:
        return evaluate_application_event(event)
    if event.source == TelemetrySource.DATABASE:
        return evaluate_database_event(event)
    return None


def build_forecast_message() -> dict:
    return {
        "forecasted_incident_trend": "moderate",
        "commentary": "Use observed rising error rates and network latency as early indicators for forecasted service risk.",
        "prediction_date": datetime.utcnow().isoformat() + "Z",
    }
