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


_SCORING_MODEL_VERSION = "phase4-step1.2-dependency-v1"


_DEPENDENCY_RELATIONSHIPS = {
    TelemetrySource.NETWORK: {
        "upstream_layers": ["edge", "dns"],
        "downstream_layers": [TelemetrySource.APPLICATION.value, TelemetrySource.DATABASE.value],
        "base_score": 0.40,
    },
    TelemetrySource.APPLICATION: {
        "upstream_layers": [TelemetrySource.NETWORK.value, "identity"],
        "downstream_layers": [TelemetrySource.DATABASE.value],
        "base_score": 0.35,
    },
    TelemetrySource.DATABASE: {
        "upstream_layers": [TelemetrySource.APPLICATION.value, TelemetrySource.NETWORK.value],
        "downstream_layers": ["storage"],
        "base_score": 0.30,
    },
}


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


def _build_dependency_relationship_scoring(
    event: TelemetryEvent,
    source: TelemetrySource,
    payload: Any,
    layer_scoring: dict[str, Any],
) -> dict[str, Any]:
    config = _DEPENDENCY_RELATIONSHIPS[source]
    upstream_layers = list(config["upstream_layers"])
    downstream_layers = list(config["downstream_layers"])
    base_score = float(config["base_score"])

    hint_flags = {
        "has_correlation_id": bool(event.correlation_id),
        "has_resource_id": bool(event.resource_id),
        "has_operation_name": bool(event.operation_name),
        "has_application_name": bool(getattr(payload, "application_name", None)),
        "has_database_name": bool(getattr(payload, "database_name", None)),
        "has_source_ip": bool(getattr(payload, "source_ip", None)),
        "has_destination_ip": bool(getattr(payload, "destination_ip", None)),
        "has_destination_port": bool(getattr(payload, "destination_port", None)),
    }

    hint_count = sum(1 for value in hint_flags.values() if value)
    hint_bonus = min(0.25, hint_count * 0.03)
    identity_bonus = 0.0
    if hint_flags["has_correlation_id"]:
        identity_bonus += 0.10
    if hint_flags["has_resource_id"]:
        identity_bonus += 0.08
    if hint_flags["has_operation_name"]:
        identity_bonus += 0.05

    layer_signature_score = float(layer_scoring.get("layer_signature_score") or 0.0)
    if layer_signature_score >= 0.90:
        layer_bonus = 0.15
    elif layer_signature_score >= 0.70:
        layer_bonus = 0.10
    elif layer_signature_score >= 0.40:
        layer_bonus = 0.05
    else:
        layer_bonus = 0.0

    raw_score = base_score + hint_bonus + identity_bonus + layer_bonus
    dependency_score = round(min(1.0, raw_score), 2)

    if dependency_score >= 0.75:
        blast_radius = "high"
    elif dependency_score >= 0.50:
        blast_radius = "medium"
    else:
        blast_radius = "low"

    dependency_edges: list[dict[str, Any]] = []
    for index, layer_name in enumerate(downstream_layers):
        dependency_edges.append(
            {
                "from_layer": source.value,
                "to_layer": layer_name,
                "relationship": "supports",
                "confidence": round(max(0.1, dependency_score - (index * 0.08)), 2),
            }
        )

    return {
        "dependency_relationship_score": dependency_score,
        "dependency_weight_raw": round(raw_score, 3),
        "dependency_base_score": base_score,
        "dependency_upstream_layers": upstream_layers,
        "dependency_downstream_layers": downstream_layers,
        "dependency_hint_count": hint_count,
        "dependency_hints": hint_flags,
        "dependency_edges": dependency_edges,
        "estimated_blast_radius": blast_radius,
        "primary_dependency_edge": dependency_edges[0] if dependency_edges else None,
    }


def _build_supporting_data(
    event: TelemetryEvent,
    source: TelemetrySource,
    payload: Any,
    matched_signals: list[dict[str, Any]],
) -> dict[str, Any]:
    layer_scoring = _build_layer_signature_scoring(source, matched_signals)
    dependency_scoring = _build_dependency_relationship_scoring(event, source, payload, layer_scoring)
    layer_scoring.update(dependency_scoring)

    supporting_data = payload.model_dump()
    supporting_data["rca_scoring"] = layer_scoring
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
        supporting_data=_build_supporting_data(event, TelemetrySource.NETWORK, payload, matched_signals),
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
        supporting_data=_build_supporting_data(event, TelemetrySource.APPLICATION, payload, matched_signals),
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
        supporting_data=_build_supporting_data(event, TelemetrySource.DATABASE, payload, matched_signals),
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
