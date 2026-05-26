"""Run Phase 4 Step 1 scoring validation against deterministic sample telemetry."""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import sys
from typing import Any

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.models import TelemetryEvent, TelemetryOrigin, TelemetrySource
from backend.processors import analyze_telemetry, reset_repeat_incident_tracker
from backend.telemetry_samples import SAMPLE_EVENTS


REPORT_PATH = Path("artifacts/phase4_step1_scoring_latest.json")


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def run_scoring_validation() -> dict[str, Any]:
    report: dict[str, Any] = {
        "run_started_at": _utc_now_iso(),
        "phase": "Phase 4",
        "step": "Step 1",
        "sub_step": "1.3",
        "version": "v0.4.0",
        "result": "fail",
        "reason": "",
        "cases": [],
    }

    required_samples = ["network_spike", "app_error", "db_latency"]
    failures: list[str] = []
    reset_repeat_incident_tracker()

    for sample_name in required_samples:
        sample_event = SAMPLE_EVENTS[sample_name]
        _ = analyze_telemetry(sample_event)
        incident = analyze_telemetry(sample_event)
        case_result: dict[str, Any] = {
            "sample": sample_name,
            "incident_created": incident is not None,
        }
        if incident is None:
            failures.append(f"{sample_name}: incident not created")
            report["cases"].append(case_result)
            continue

        scoring = incident.supporting_data.get("rca_scoring", {})
        score = float(scoring.get("layer_signature_score") or 0.0)
        dependency_score = float(scoring.get("dependency_relationship_score") or 0.0)
        matched_signal_count = int(scoring.get("matched_signal_count") or 0)
        model_version = str(scoring.get("model_version") or "")
        dependency_edges = scoring.get("dependency_edges") or []
        repeat_count = int(scoring.get("repeat_incident_count_prior_window") or 0)
        repeat_bonus = float(scoring.get("repeat_weight_bonus") or 0.0)
        composite_pre_repeat = float(scoring.get("composite_score_pre_repeat") or 0.0)
        composite_final = float(scoring.get("composite_score_final") or 0.0)

        case_result["severity"] = incident.severity.value
        case_result["layer"] = scoring.get("layer")
        case_result["layer_signature_score"] = score
        case_result["dependency_relationship_score"] = dependency_score
        case_result["matched_signal_count"] = matched_signal_count
        case_result["top_signal"] = scoring.get("top_signal")
        case_result["dependency_edge_count"] = len(dependency_edges)
        case_result["repeat_incident_count_prior_window"] = repeat_count
        case_result["repeat_weight_bonus"] = repeat_bonus
        case_result["composite_score_pre_repeat"] = composite_pre_repeat
        case_result["composite_score_final"] = composite_final
        case_result["model_version"] = model_version

        if not (0.0 <= score <= 1.0):
            failures.append(f"{sample_name}: score out of range")
        if not (0.0 <= dependency_score <= 1.0):
            failures.append(f"{sample_name}: dependency score out of range")
        if matched_signal_count < 1:
            failures.append(f"{sample_name}: matched_signal_count < 1")
        if len(dependency_edges) < 1:
            failures.append(f"{sample_name}: dependency_edge_count < 1")
        if repeat_count < 1:
            failures.append(f"{sample_name}: repeat_incident_count_prior_window < 1")
        if repeat_bonus <= 0.0:
            failures.append(f"{sample_name}: repeat_weight_bonus <= 0")
        if composite_final < composite_pre_repeat:
            failures.append(f"{sample_name}: composite_score_final < composite_score_pre_repeat")
        if model_version != "phase4-step1.3-repeat-v1":
            failures.append(f"{sample_name}: unexpected model_version")

        report["cases"].append(case_result)

    benign_event = TelemetryEvent(
        source=TelemetrySource.APPLICATION,
        origin=TelemetryOrigin.SIMULATOR,
        payload={
            "request_rate_per_min": 100,
            "error_rate_pct": 0.2,
            "avg_response_ms": 180.0,
            "p95_response_ms": 260.0,
            "status_5xx_count": 0,
            "application_name": "healthy-app",
        },
    )
    benign_incident = analyze_telemetry(benign_event)
    benign_case = {
        "sample": "benign_application",
        "incident_created": benign_incident is not None,
        "expected": "no_incident",
    }
    report["cases"].append(benign_case)
    if benign_incident is not None:
        failures.append("benign_application: incident should not be created")

    report["summary"] = {
        "required_samples": len(required_samples),
        "cases_total": len(report["cases"]),
        "failure_count": len(failures),
    }
    report["failures"] = failures
    report["run_finished_at"] = _utc_now_iso()

    if failures:
        report["result"] = "fail"
        report["reason"] = "One or more Phase 4 Step 1.3 scoring checks failed."
    else:
        report["result"] = "pass"
        report["reason"] = "Phase 4 Step 1.3 repeated-incident weighting checks passed."
    return report


def main() -> int:
    report = run_scoring_validation()
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(f"Phase 4 Step 1.3 scoring result: {report.get('result')}")
    print(f"Reason: {report.get('reason')}")
    print(f"Report: {REPORT_PATH}")
    return 0 if report.get("result") == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
