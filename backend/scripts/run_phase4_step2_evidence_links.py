"""Run Phase 4 Step 2.2 evidence-link persistence validation."""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import sys
from typing import Any

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.data_store import store
from backend.processors import analyze_telemetry, reset_repeat_incident_tracker
from backend.telemetry_samples import SAMPLE_EVENTS


REPORT_PATH = Path("artifacts/phase4_step2_evidence_links_latest.json")


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _reset_runtime_state() -> None:
    reset_repeat_incident_tracker()
    store.telemetry.clear()
    store.incidents.clear()
    store.correlations.clear()
    store.evidence_records.clear()


def run_evidence_link_validation() -> dict[str, Any]:
    report: dict[str, Any] = {
        "run_started_at": _utc_now_iso(),
        "phase": "Phase 4",
        "step": "Step 2",
        "sub_step": "2.2",
        "version": "v0.4.0",
        "result": "fail",
        "reason": "",
        "cases": [],
        "failures": [],
    }

    _reset_runtime_state()
    sample_names = ["network_spike", "app_error", "db_latency"]

    for sample_name in sample_names:
        event = SAMPLE_EVENTS[sample_name].model_copy(deep=True)
        incident = analyze_telemetry(event)
        if incident is None:
            report["failures"].append(f"{sample_name}: incident not created")
            report["cases"].append({"sample": sample_name, "incident_created": False})
            continue

        store.add_incident(incident)
        records = store.persist_incident_evidence(incident)

        case_failures: list[str] = []
        if len(records) != incident.evidence_count:
            case_failures.append(f"{sample_name}: persisted records != evidence_count")
        if len(incident.supporting_evidence_links) != incident.evidence_count:
            case_failures.append(f"{sample_name}: supporting_evidence_links != evidence_count")
        if len(store.get_incident_evidence(incident.id)) != incident.evidence_count:
            case_failures.append(f"{sample_name}: incident evidence lookup count mismatch")

        resolved_links = 0
        for link in incident.supporting_evidence_links:
            evidence_id = link.split("/")[-1]
            if store.get_evidence_record(evidence_id):
                resolved_links += 1
        if resolved_links != len(incident.supporting_evidence_links):
            case_failures.append(f"{sample_name}: one or more evidence links do not resolve")

        report["cases"].append(
            {
                "sample": sample_name,
                "incident_created": True,
                "incident_id": incident.id,
                "evidence_count": incident.evidence_count,
                "persisted_records": len(records),
                "supporting_evidence_links": len(incident.supporting_evidence_links),
                "resolved_links": resolved_links,
                "failure_count": len(case_failures),
            }
        )
        report["failures"].extend(case_failures)

    report["summary"] = {
        "cases_total": len(report["cases"]),
        "persisted_evidence_total": len(store.get_evidence_records()),
        "failure_count": len(report["failures"]),
    }
    report["run_finished_at"] = _utc_now_iso()

    if report["failures"]:
        report["result"] = "fail"
        report["reason"] = "One or more Phase 4 Step 2.2 evidence-link checks failed."
    else:
        report["result"] = "pass"
        report["reason"] = "Phase 4 Step 2.2 evidence-link persistence checks passed."
    return report


def main() -> int:
    report = run_evidence_link_validation()
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(f"Phase 4 Step 2.2 evidence-link result: {report.get('result')}")
    print(f"Reason: {report.get('reason')}")
    print(f"Report: {REPORT_PATH}")
    return 0 if report.get("result") == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
