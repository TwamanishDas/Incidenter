"""Run Phase 2 Step 4 live-mode acceptance checks against a local backend instance."""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import time
from typing import Any

import requests

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.azure_config import AzureConfig


BASE_URL = "http://127.0.0.1:8000"
ATTEMPTS = 3
POLL_SECONDS = 35
REPORT_PATH = Path("artifacts/phase2_step4_acceptance_latest.json")


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _get_json(path: str) -> tuple[int, dict[str, Any] | list[Any] | None]:
    response = requests.get(f"{BASE_URL}{path}", timeout=10)
    try:
        payload = response.json()
    except Exception:
        payload = None
    return response.status_code, payload


def _collect_snapshot() -> dict[str, Any]:
    health_status_code, health_payload = _get_json("/health")
    scheduler_status_code, scheduler_payload = _get_json("/scheduler/status")
    checklist_status_code, checklist_payload = _get_json("/ingestion/checklist")
    incidents_status_code, incidents_payload = _get_json("/incidents")

    incidents_count = len(incidents_payload) if isinstance(incidents_payload, list) else 0
    return {
        "captured_at": _utc_now_iso(),
        "health_status_code": health_status_code,
        "health": health_payload,
        "scheduler_status_code": scheduler_status_code,
        "scheduler_status": scheduler_payload,
        "checklist_status_code": checklist_status_code,
        "ingestion_checklist": checklist_payload,
        "incidents_status_code": incidents_status_code,
        "incidents_count": incidents_count,
    }


def _monitor_collector_events(scheduler_status: dict[str, Any]) -> int:
    collectors = scheduler_status.get("collectors", []) or []
    for collector in collectors:
        if collector.get("name") == "MonitorMetricsCollector":
            try:
                return int(collector.get("events_collected") or 0)
            except Exception:
                return 0
    return 0


def _evaluate(report: dict[str, Any]) -> dict[str, Any]:
    attempts = report.get("attempts", [])
    first = attempts[0] if attempts else {}
    final = attempts[-1] if attempts else {}

    first_scheduler = first.get("scheduler_status") if isinstance(first.get("scheduler_status"), dict) else {}
    final_scheduler = final.get("scheduler_status") if isinstance(final.get("scheduler_status"), dict) else {}
    final_checklist = final.get("ingestion_checklist") if isinstance(final.get("ingestion_checklist"), dict) else {}
    final_health = final.get("health") if isinstance(final.get("health"), dict) else {}

    final_collection_count = int(final_scheduler.get("collection_count") or 0)
    first_collection_count = int(first_scheduler.get("collection_count") or 0)
    final_collected = int(final_scheduler.get("total_events_collected") or 0)
    final_posted = int(final_scheduler.get("total_events_posted") or 0)
    final_deduped = int(final_scheduler.get("total_events_deduped") or 0)
    final_collectors = final_scheduler.get("collectors", []) or []
    final_collector_count = len(final_collectors)

    monitor_resource_count = len(AzureConfig.MONITOR_RESOURCE_IDS)
    monitor_events = _monitor_collector_events(final_scheduler)

    criteria = [
        {
            "id": "backend_healthy",
            "description": "Backend health endpoint returns healthy",
            "passed": final.get("health_status_code") == 200 and final_health.get("status") == "healthy",
            "observed": {"status_code": final.get("health_status_code"), "status": final_health.get("status")},
            "expected": {"status_code": 200, "status": "healthy"},
        },
        {
            "id": "scheduler_running",
            "description": "Scheduler is running in final snapshot",
            "passed": bool(final_scheduler.get("is_running")),
            "observed": final_scheduler.get("is_running"),
            "expected": True,
        },
        {
            "id": "collector_count",
            "description": "At least 5 collectors are configured",
            "passed": final_collector_count >= 5,
            "observed": final_collector_count,
            "expected": ">=5",
        },
        {
            "id": "collectors_no_error",
            "description": "Checklist reports zero collector errors",
            "passed": int(final_checklist.get("collector_overview", {}).get("error_collectors", 0)) == 0,
            "observed": final_checklist.get("collector_overview", {}).get("error_collectors"),
            "expected": 0,
        },
        {
            "id": "collectors_not_stale",
            "description": "Checklist reports zero stale collectors",
            "passed": len(final_checklist.get("collector_overview", {}).get("stale_collectors", []) or []) == 0,
            "observed": final_checklist.get("collector_overview", {}).get("stale_collectors"),
            "expected": [],
        },
        {
            "id": "live_mode",
            "description": "Ingestion checklist mode is live",
            "passed": str(final_checklist.get("ingestion_mode")) == "live",
            "observed": final_checklist.get("ingestion_mode"),
            "expected": "live",
        },
        {
            "id": "checklist_pass",
            "description": "Ingestion checklist overall status is pass",
            "passed": str(final_checklist.get("overall_status")) == "pass",
            "observed": final_checklist.get("overall_status"),
            "expected": "pass",
        },
        {
            "id": "event_flow_integrity",
            "description": "Collected events are processed correctly",
            "passed": final_collected > 0 and (final_posted + final_deduped) >= final_collected,
            "observed": {
                "collected": final_collected,
                "posted": final_posted,
                "deduped": final_deduped,
            },
            "expected": "collected > 0 and posted + deduped >= collected",
        },
        {
            "id": "dedup_sanity",
            "description": "Dedup count does not exceed collected count",
            "passed": final_deduped <= final_collected,
            "observed": {"collected": final_collected, "deduped": final_deduped},
            "expected": "deduped <= collected",
        },
        {
            "id": "monitor_scope_expanded",
            "description": "Monitor resource scope includes at least 3 resource IDs",
            "passed": monitor_resource_count >= 3,
            "observed": monitor_resource_count,
            "expected": ">=3",
        },
        {
            "id": "collections_progressing",
            "description": "Collection count progressed across snapshots",
            "passed": final_collection_count > first_collection_count,
            "observed": {"first": first_collection_count, "final": final_collection_count},
            "expected": "final > first",
        },
        {
            "id": "monitor_events_present",
            "description": "Monitor metrics collector has collected events",
            "passed": monitor_events > 0,
            "observed": monitor_events,
            "expected": ">0",
        },
    ]

    passed = sum(1 for item in criteria if item["passed"])
    failed = len(criteria) - passed
    overall_passed = failed == 0
    return {
        "overall_passed": overall_passed,
        "summary": {
            "criteria_total": len(criteria),
            "criteria_passed": passed,
            "criteria_failed": failed,
        },
        "criteria": criteria,
    }


def run_acceptance() -> dict[str, Any]:
    report: dict[str, Any] = {
        "run_started_at": _utc_now_iso(),
        "phase": "Phase 2",
        "step": "Step 4",
        "version": "v0.2.0",
        "mode_expected": "live",
        "base_url": BASE_URL,
        "attempts": [],
        "result": "fail",
        "reason": "",
    }

    for idx in range(ATTEMPTS):
        try:
            report["attempts"].append(_collect_snapshot())
        except Exception as exc:
            report["attempts"].append(
                {
                    "captured_at": _utc_now_iso(),
                    "error": f"snapshot_failed: {exc}",
                }
            )
        if idx < ATTEMPTS - 1:
            time.sleep(POLL_SECONDS)

    evaluation = _evaluate(report)
    report["evaluation"] = evaluation
    report["final_snapshot"] = report["attempts"][-1] if report["attempts"] else None
    report["run_finished_at"] = _utc_now_iso()

    if evaluation.get("overall_passed"):
        report["result"] = "pass"
        report["reason"] = "Phase 2 Step 4 live acceptance criteria passed."
    else:
        report["result"] = "fail"
        report["reason"] = "One or more Phase 2 Step 4 live acceptance criteria failed."

    return report


def main() -> int:
    report = run_acceptance()
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(f"Phase 2 Step 4 acceptance result: {report.get('result')}")
    print(f"Reason: {report.get('reason')}")
    print(f"Report: {REPORT_PATH}")

    return 0 if report.get("result") == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
