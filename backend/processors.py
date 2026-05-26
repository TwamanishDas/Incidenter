from datetime import datetime
import uuid
from typing import Any

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


_SCORING_MODEL_VERSION = "phase4-step1.1-layer-signature-v1"


def _add_weighted_signal(
    evidence: list[RCALink],
    matched_signals: list[dict[str, Any]],
    *,
    signal_id: str,
    weight: float,
    severity: Severity,
    evidence_text: str,
    observed_value: Any,
    threshold: str,
) -> None:
    evidence.append(RCALink(evidence=evidence_text, severity=severity))
    matched_signals.append(
        {
            "signal_id": signal_id,
            "weight": weight,
            "severity": severity.value,
            "observed_value": observed_value,
            "threshold": threshold,
            "evidence": evidence_text,
        }
    )


def _build_layer_signature_scoring(
    source: TelemetrySource,
    matched_signals: list[dict[str, Any]],
) -> dict[str, Any]:
    ranked_signals = sorted(matched_signals, key=lambda item: float(item["weight"]), reverse=True)
    raw_score = sum(float(item["weight"]) for item in ranked_signals)
    normalized_score = round(min(1.0, raw_score), 2)
    return {
        "model_version": _SCORING_MODEL_VERSION,
        "layer": source.value,
        "layer_signature_score": normalized_score,
        "max_score": 1.0,
        "weight_sum_raw": round(raw_score, 3),
        "matched_signal_count": len(ranked_signals),
        "matched_signals": ranked_signals,
        "top_signal": ranked_signals[0]["signal_id"] if ranked_signals else None,
    }


def _build_supporting_data(
    source: TelemetrySource,
    payload: Any,
    matched_signals: list[dict[str, Any]],
) -> dict[str, Any]:
    supporting_data = payload.model_dump()
    supporting_data["rca_scoring"] = _build_layer_signature_scoring(source, matched_signals)
    return supporting_data


def evaluate_network_event(event: TelemetryEvent) -> Incident | None:
    payload = NetworkPayload(**event.payload)
    evidence: list[RCALink] = []
    matched_signals: list[dict[str, Any]] = []

    if payload.nsg_denied_connections > 10:
        _add_weighted_signal(
            evidence,
            matched_signals,
            signal_id="nsg_denied_connections",
            weight=0.40,
            severity=Severity.CRITICAL,
            evidence_text="High NSG denied connection count",
            observed_value=payload.nsg_denied_connections,
            threshold=">10",
        )
    if payload.packet_loss >= 5.0:
        _add_weighted_signal(
            evidence,
            matched_signals,
            signal_id="packet_loss",
            weight=0.35,
            severity=Severity.CRITICAL,
            evidence_text="Packet loss above 5%",
            observed_value=payload.packet_loss,
            threshold=">=5.0",
        )
    if payload.avg_latency_ms >= 200.0:
        _add_weighted_signal(
            evidence,
            matched_signals,
            signal_id="avg_latency_ms",
            weight=0.20,
            severity=Severity.WARNING,
            evidence_text="High average network latency",
            observed_value=payload.avg_latency_ms,
            threshold=">=200.0",
        )
    if payload.tcp_retry_count >= 5:
        _add_weighted_signal(
            evidence,
            matched_signals,
            signal_id="tcp_retry_count",
            weight=0.15,
            severity=Severity.WARNING,
            evidence_text="TCP retries indicate connectivity issues",
            observed_value=payload.tcp_retry_count,
            threshold=">=5",
        )

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
        supporting_data=_build_supporting_data(TelemetrySource.NETWORK, payload, matched_signals),
    )


def evaluate_application_event(event: TelemetryEvent) -> Incident | None:
    payload = ApplicationPayload(**event.payload)
    evidence: list[RCALink] = []
    matched_signals: list[dict[str, Any]] = []

    if payload.error_rate_pct >= 5.0 or payload.status_5xx_count >= 10:
        _add_weighted_signal(
            evidence,
            matched_signals,
            signal_id="error_rate_or_5xx",
            weight=0.55,
            severity=Severity.CRITICAL,
            evidence_text="Application error rate exceeds threshold",
            observed_value={
                "error_rate_pct": payload.error_rate_pct,
                "status_5xx_count": payload.status_5xx_count,
            },
            threshold="error_rate_pct>=5.0 or status_5xx_count>=10",
        )
    if payload.avg_response_ms >= 1000.0:
        _add_weighted_signal(
            evidence,
            matched_signals,
            signal_id="avg_response_ms",
            weight=0.30,
            severity=Severity.WARNING,
            evidence_text="Average response latency exceeds 1000 ms",
            observed_value=payload.avg_response_ms,
            threshold=">=1000.0",
        )
    if payload.p95_response_ms and payload.p95_response_ms >= 2000.0:
        _add_weighted_signal(
            evidence,
            matched_signals,
            signal_id="p95_response_ms",
            weight=0.25,
            severity=Severity.WARNING,
            evidence_text="P95 latency spike detected",
            observed_value=payload.p95_response_ms,
            threshold=">=2000.0",
        )

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
        supporting_data=_build_supporting_data(TelemetrySource.APPLICATION, payload, matched_signals),
    )


def evaluate_database_event(event: TelemetryEvent) -> Incident | None:
    payload = DatabasePayload(**event.payload)
    evidence: list[RCALink] = []
    matched_signals: list[dict[str, Any]] = []

    if payload.connection_errors >= 5:
        _add_weighted_signal(
            evidence,
            matched_signals,
            signal_id="connection_errors",
            weight=0.50,
            severity=Severity.CRITICAL,
            evidence_text="Database connection error spike.",
            observed_value=payload.connection_errors,
            threshold=">=5",
        )
    if payload.timeout_count >= 3:
        _add_weighted_signal(
            evidence,
            matched_signals,
            signal_id="timeout_count",
            weight=0.25,
            severity=Severity.WARNING,
            evidence_text="Database query timeouts observed.",
            observed_value=payload.timeout_count,
            threshold=">=3",
        )
    if payload.deadlock_count >= 1:
        _add_weighted_signal(
            evidence,
            matched_signals,
            signal_id="deadlock_count",
            weight=0.20,
            severity=Severity.WARNING,
            evidence_text="Deadlocks found in database workload.",
            observed_value=payload.deadlock_count,
            threshold=">=1",
        )
    if payload.avg_query_duration_ms >= 2000.0:
        _add_weighted_signal(
            evidence,
            matched_signals,
            signal_id="avg_query_duration_ms",
            weight=0.20,
            severity=Severity.WARNING,
            evidence_text="Average query duration is very high.",
            observed_value=payload.avg_query_duration_ms,
            threshold=">=2000.0",
        )

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
        supporting_data=_build_supporting_data(TelemetrySource.DATABASE, payload, matched_signals),
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
