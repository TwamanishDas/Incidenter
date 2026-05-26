"""Run Phase 5 Step 1.1 validation for the active incident dashboard endpoint."""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import sys
from typing import Any

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.app import list_active_incident_cards, simulate
from backend.data_store import store
from backend.models import SimulationRequest
from backend.processors import reset_repeat_incident_tracker


REPORT_PATH = Path("artifacts/phase5_step1_active_incidents_latest.json")


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _reset_runtime_state() -> None:
    reset_repeat_incident_tracker()
    store.telemetry.clear()
    store.incidents.clear()
    store.correlations.clear()
    store.evidence_records.clear()


def run_dashboard_validation() -> dict[str, Any]:
    report: dict[str, Any] = {
        "run_started_at": _utc_now_iso(),
        "phase": "Phase 5",
        "step": "Step 1",
        "sub_step": "1.1",
        "version": "v0.5.0",
        "result": "fail",
        "reason": "",
        "checks": [],
        "failures": [],
    }

    _reset_runtime_state()
    for scenario in ["network_spike", "app_error", "db_latency"]:
        try:
            simulate(SimulationRequest(scenario=scenario))
        except Exception as exc:  # pragma: no cover - defensive path
            report["failures"].append(f"simulate failed for scenario {scenario}: {exc}")

    try:
        cards = [item.model_dump(mode="json") for item in list_active_incident_cards()]
    except Exception as exc:  # pragma: no cover - defensive path
        report["failures"].append(f"dashboard active incident card generation failed: {exc}")
        cards = []

    report["checks"].append(
        {
            "check": "active_incidents_response",
            "function_status": "ok" if not report["failures"] else "error",
            "card_count": len(cards),
        }
    )

    if len(cards) != 3:
        report["failures"].append("active incident card count mismatch")

    required_fields = {
        "incident_id",
        "detected_at",
        "incident_type",
        "title",
        "severity",
        "affected_component",
        "likely_root_cause",
        "probability_score",
        "confidence_label",
        "evidence_count",
        "primary_evidence",
        "evidence_links",
        "status",
    }
    if cards:
        missing = sorted(required_fields - set(cards[0].keys()))
        if missing:
            report["failures"].append(f"missing required card fields: {', '.join(missing)}")

    report["summary"] = {
        "incidents_in_store": len(store.get_incidents()),
        "cards_returned": len(cards),
        "failure_count": len(report["failures"]),
    }
    report["run_finished_at"] = _utc_now_iso()

    if report["failures"]:
        report["result"] = "fail"
        report["reason"] = "One or more Phase 5 Step 1.1 dashboard checks failed."
    else:
        report["result"] = "pass"
        report["reason"] = "Phase 5 Step 1.1 active incident dashboard checks passed."
    return report


def main() -> int:
    report = run_dashboard_validation()
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(f"Phase 5 Step 1.1 dashboard result: {report.get('result')}")
    print(f"Reason: {report.get('reason')}")
    print(f"Report: {REPORT_PATH}")
    return 0 if report.get("result") == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
