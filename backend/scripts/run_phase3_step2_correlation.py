"""Run Phase 3 Step 2 correlation enricher against Phase 3 Step 1 signal output."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import sys
from typing import Any

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.azure_config import AzureConfig
from backend.correlation_enricher import CorrelationEnricher
from backend.models import TelemetryEvent, TelemetryOrigin, TelemetrySource
from backend.signal_contract_mapper import map_signal_row_to_telemetry_event


INPUT_SIGNAL_ARTIFACT = Path("artifacts/phase3_step1_signal_pack_latest.json")
OUTPUT_CORRELATION_ARTIFACT = Path("artifacts/phase3_step2_correlation_latest.json")


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _build_synthetic_probe() -> tuple[list[TelemetryEvent], list[dict[str, Any]]]:
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    base_resource = "/subscriptions/demo-sub/resourceGroups/demo-rg/providers/Microsoft.Web/sites/demo-app"
    app_event = TelemetryEvent(
        timestamp=now,
        source=TelemetrySource.APPLICATION,
        origin=TelemetryOrigin.LOG_ANALYTICS,
        operation_name="synthetic::app_failure_rate",
        resource_id=base_resource,
        subscription_id="demo-sub",
        region="eastus",
        payload={
            "application_name": "demo-app",
            "request_rate_per_min": 120,
            "error_rate_pct": 9.5,
            "avg_response_ms": 1500.0,
            "p95_response_ms": 2200.0,
            "status_5xx_count": 20,
        },
    )
    db_event = TelemetryEvent(
        timestamp=now + timedelta(minutes=1),
        source=TelemetrySource.DATABASE,
        origin=TelemetryOrigin.AZURE_MONITOR_DIAGNOSTICS,
        operation_name="synthetic::db_timeout",
        resource_id=base_resource,
        subscription_id="demo-sub",
        region="eastus",
        payload={
            "database_name": "demo-db",
            "connection_errors": 6,
            "timeout_count": 4,
            "deadlock_count": 1,
            "avg_query_duration_ms": 2100.0,
        },
    )
    rows = [
        {
            "id": "synthetic::app_failure_rate",
            "status": "pass",
            "row_count": 1,
        },
        {
            "id": "synthetic::db_timeout",
            "status": "pass",
            "row_count": 1,
        },
    ]
    return [app_event, db_event], rows


def run_correlation() -> dict[str, Any]:
    report: dict[str, Any] = {
        "run_started_at": _utc_now_iso(),
        "phase": "Phase 3",
        "step": "Step 2",
        "version": "v0.3.0",
        "input_signal_artifact": str(INPUT_SIGNAL_ARTIFACT),
        "result": "fail",
        "reason": "",
    }

    if not INPUT_SIGNAL_ARTIFACT.exists():
        report["reason"] = f"Missing input artifact: {INPUT_SIGNAL_ARTIFACT}"
        report["run_finished_at"] = _utc_now_iso()
        return report

    input_payload = json.loads(INPUT_SIGNAL_ARTIFACT.read_text(encoding="utf-8"))
    signal_queries = input_payload.get("queries", []) or []

    enricher = CorrelationEnricher(window_minutes=15, max_events=10000)
    mapped_events: list[TelemetryEvent] = []
    mapping_errors: list[str] = []
    correlations = []

    for query in signal_queries:
        query_id = str(query.get("id") or "")
        rows = query.get("sample_rows", []) or []
        for index, row in enumerate(rows):
            if not isinstance(row, dict):
                continue
            try:
                mapped = map_signal_row_to_telemetry_event(
                    query_id=query_id,
                    row=row,
                    default_subscription_id=AzureConfig.SUBSCRIPTION_ID,
                    default_region=None,
                )
                mapped_events.append(mapped)
                correlation = enricher.ingest(mapped)
                if correlation:
                    correlations.append(correlation.model_dump(mode="json"))
            except Exception as exc:
                mapping_errors.append(f"{query_id}[{index}]: {exc}")

    synthetic_events, synthetic_rows = _build_synthetic_probe()
    synthetic_correlations = []
    synthetic_enricher = CorrelationEnricher(window_minutes=15, max_events=1000)
    for event in synthetic_events:
        correlation = synthetic_enricher.ingest(event)
        if correlation:
            synthetic_correlations.append(correlation.model_dump(mode="json"))

    report["summary"] = {
        "signal_queries_total": len(signal_queries),
        "mapped_events_count": len(mapped_events),
        "mapping_error_count": len(mapping_errors),
        "correlations_count": len(correlations),
        "synthetic_probe_events": len(synthetic_events),
        "synthetic_probe_correlations": len(synthetic_correlations),
    }
    report["mapping_errors"] = mapping_errors
    report["correlations"] = correlations
    report["signal_query_status"] = [
        {"id": query.get("id"), "status": query.get("status"), "row_count": query.get("row_count")}
        for query in signal_queries
    ]
    report["synthetic_probe"] = {
        "signals": synthetic_rows,
        "correlations": synthetic_correlations,
    }

    if mapping_errors:
        report["result"] = "fail"
        report["reason"] = "Signal-to-contract mapping errors occurred."
    elif len(synthetic_correlations) == 0:
        report["result"] = "fail"
        report["reason"] = "Synthetic probe did not produce correlated evidence."
    else:
        report["result"] = "pass"
        if len(mapped_events) == 0:
            report["reason"] = (
                "Correlation pipeline executed successfully. No live signal rows were available, "
                "synthetic probe correlation passed."
            )
        elif len(correlations) == 0:
            report["reason"] = (
                "Correlation pipeline executed successfully. Live signals mapped but did not meet "
                "cross-source join criteria in this window; synthetic probe correlation passed."
            )
        else:
            report["reason"] = (
                f"Correlation pipeline executed successfully with {len(correlations)} live correlated bundle(s)."
            )

    report["run_finished_at"] = _utc_now_iso()
    return report


def main() -> int:
    report = run_correlation()
    OUTPUT_CORRELATION_ARTIFACT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_CORRELATION_ARTIFACT.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(f"Phase 3 Step 2 correlation result: {report.get('result')}")
    print(f"Reason: {report.get('reason')}")
    print(f"Report: {OUTPUT_CORRELATION_ARTIFACT}")
    return 0 if report.get("result") == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())

