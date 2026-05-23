"""Step 6 ingestion acceptance criteria evaluation."""

from typing import Any


def evaluate_ingestion_acceptance(
    scheduler_status: dict[str, Any] | None,
    checklist: dict[str, Any] | None,
    incidents_count: int,
) -> dict[str, Any]:
    scheduler_status = scheduler_status or {}
    checklist = checklist or {}

    collectors = scheduler_status.get("collectors", []) or []
    collector_statuses = [str(item.get("status", "unknown")).lower() for item in collectors]
    healthy_collectors = sum(1 for status in collector_statuses if status == "healthy")

    criteria = [
        {
            "id": "scheduler_running",
            "description": "Scheduler is running",
            "passed": bool(scheduler_status.get("is_running")),
            "observed": scheduler_status.get("is_running"),
            "expected": True,
        },
        {
            "id": "collectors_initialized",
            "description": "At least 5 collectors are initialized",
            "passed": len(collectors) >= 5,
            "observed": len(collectors),
            "expected": ">=5",
        },
        {
            "id": "collections_progressing",
            "description": "At least 2 collection cycles completed",
            "passed": int(scheduler_status.get("collection_count") or 0) >= 2,
            "observed": int(scheduler_status.get("collection_count") or 0),
            "expected": ">=2",
        },
        {
            "id": "collectors_healthy",
            "description": "All initialized collectors are healthy",
            "passed": len(collectors) > 0 and healthy_collectors == len(collectors),
            "observed": {
                "healthy": healthy_collectors,
                "total": len(collectors),
            },
            "expected": "healthy == total",
        },
        {
            "id": "ingestion_checklist_not_fail",
            "description": "Ingestion checklist overall status is not fail",
            "passed": checklist.get("overall_status") in {"pass", "warn"},
            "observed": checklist.get("overall_status"),
            "expected": "pass|warn",
        },
        {
            "id": "incidents_generated",
            "description": "At least one incident is generated from replayed data",
            "passed": incidents_count >= 1,
            "observed": incidents_count,
            "expected": ">=1",
        },
    ]

    passed_count = sum(1 for item in criteria if item["passed"])
    failed_count = len(criteria) - passed_count
    overall_passed = failed_count == 0

    return {
        "overall_passed": overall_passed,
        "summary": {
            "criteria_total": len(criteria),
            "criteria_passed": passed_count,
            "criteria_failed": failed_count,
        },
        "criteria": criteria,
    }

