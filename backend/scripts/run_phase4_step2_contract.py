"""Run Phase 4 Step 2.1 contract validation for incident output fields."""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import sys
from typing import Any

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.processors import analyze_telemetry, reset_repeat_incident_tracker
from backend.telemetry_samples import SAMPLE_EVENTS


REPORT_PATH = Path("artifacts/phase4_step2_contract_latest.json")


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _validate_incident_fields(sample_name: str, incident: Any) -> list[str]:
    failures: list[str] = []
    if incident is None:
        return [f"{sample_name}: incident not created"]

    if not (0.0 <= float(incident.probability_score) <= 1.0):
        failures.append(f"{sample_name}: probability_score out of range")
    if incident.confidence_label not in {"low", "medium", "high"}:
        failures.append(f"{sample_name}: invalid confidence_label")
    if not str(incident.incident_signature):
        failures.append(f"{sample_name}: incident_signature missing")
    if not str(incident.scoring_model_version):
        failures.append(f"{sample_name}: scoring_model_version missing")
    if int(incident.evidence_count) != len(incident.supporting_evidence):
        failures.append(f"{sample_name}: evidence_count mismatch")
    if len(incident.supporting_evidence) == 0:
        failures.append(f"{sample_name}: supporting_evidence empty")
    else:
        if incident.primary_evidence != incident.supporting_evidence[0]:
            failures.append(f"{sample_name}: primary_evidence mismatch")

    scoring = incident.supporting_data.get("rca_scoring", {})
    if incident.probability_score != scoring.get("composite_score_final"):
        failures.append(f"{sample_name}: probability_score not aligned to composite_score_final")
    if incident.incident_signature != scoring.get("incident_signature"):
        failures.append(f"{sample_name}: incident_signature not aligned to scoring payload")
    if incident.scoring_model_version != scoring.get("model_version"):
        failures.append(f"{sample_name}: scoring_model_version not aligned to scoring payload")

    return failures


def run_contract_validation() -> dict[str, Any]:
    report: dict[str, Any] = {
        "run_started_at": _utc_now_iso(),
        "phase": "Phase 4",
        "step": "Step 2",
        "sub_step": "2.1",
        "version": "v0.4.0",
        "result": "fail",
        "reason": "",
        "cases": [],
        "failures": [],
    }

    reset_repeat_incident_tracker()
    sample_names = ["network_spike", "app_error", "db_latency"]

    for sample_name in sample_names:
        event = SAMPLE_EVENTS[sample_name]
        incident = analyze_telemetry(event)
        case_failures = _validate_incident_fields(sample_name, incident)
        report["cases"].append(
            {
                "sample": sample_name,
                "incident_created": incident is not None,
                "incident_type": incident.incident_type.value if incident else None,
                "probability_score": float(incident.probability_score) if incident else None,
                "confidence_label": incident.confidence_label if incident else None,
                "evidence_count": int(incident.evidence_count) if incident else None,
                "failure_count": len(case_failures),
            }
        )
        report["failures"].extend(case_failures)

    report["summary"] = {
        "cases_total": len(report["cases"]),
        "failure_count": len(report["failures"]),
    }
    report["run_finished_at"] = _utc_now_iso()

    if report["failures"]:
        report["result"] = "fail"
        report["reason"] = "One or more Phase 4 Step 2.1 contract checks failed."
    else:
        report["result"] = "pass"
        report["reason"] = "Phase 4 Step 2.1 incident output contract checks passed."
    return report


def main() -> int:
    report = run_contract_validation()
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(f"Phase 4 Step 2.1 contract result: {report.get('result')}")
    print(f"Reason: {report.get('reason')}")
    print(f"Report: {REPORT_PATH}")
    return 0 if report.get("result") == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
