"""Ingestion health checklist generation for scheduler telemetry."""

from datetime import datetime, timezone
from typing import Any


def _utc_now_naive() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _parse_iso_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is not None:
        return parsed.astimezone(timezone.utc).replace(tzinfo=None)
    return parsed


def _infer_ingestion_mode(collectors: list[dict[str, Any]]) -> str:
    if any(str(item.get("name", "")).startswith("BlobSample") for item in collectors):
        return "sample_blob"
    return "live"


def build_ingestion_checklist(scheduler_status: dict[str, Any] | None, now_utc: datetime | None = None) -> dict[str, Any]:
    now = now_utc or _utc_now_naive()
    checks: list[dict[str, Any]] = []

    def add_check(
        check_id: str,
        status: str,
        message: str,
        observed: Any = None,
        expected: Any = None,
    ):
        checks.append(
            {
                "id": check_id,
                "status": status,
                "message": message,
                "observed": observed,
                "expected": expected,
            }
        )

    if not scheduler_status:
        add_check(
            "scheduler_initialized",
            "fail",
            "Scheduler is not initialized.",
            observed=False,
            expected=True,
        )
        return {
            "overall_status": "fail",
            "evaluated_at": now.isoformat(),
            "ingestion_mode": "unknown",
            "freshness_sla_seconds": None,
            "summary": {
                "checks_total": 1,
                "checks_passed": 0,
                "checks_warned": 0,
                "checks_failed": 1,
            },
            "checks": checks,
            "collector_overview": {
                "total_collectors": 0,
                "healthy_collectors": 0,
                "error_collectors": 0,
                "stale_collectors": [],
            },
            "collectors": [],
            "counters": {},
        }

    collectors = scheduler_status.get("collectors", []) or []
    ingestion_mode = _infer_ingestion_mode(collectors)
    interval_seconds = int(scheduler_status.get("interval_seconds") or 0)
    collection_count = int(scheduler_status.get("collection_count") or 0)
    total_collected = int(scheduler_status.get("total_events_collected") or 0)
    total_posted = int(scheduler_status.get("total_events_posted") or 0)
    total_deduped = int(scheduler_status.get("total_events_deduped") or 0)
    dedup_cache_size = int(scheduler_status.get("dedup_cache_size") or 0)
    freshness_sla_seconds = max(90, interval_seconds * 3) if interval_seconds > 0 else 180

    is_running = bool(scheduler_status.get("is_running"))
    add_check(
        "scheduler_running",
        "pass" if is_running else "fail",
        "Scheduler run loop is active." if is_running else "Scheduler run loop is not active.",
        observed=is_running,
        expected=True,
    )

    collector_count = len(collectors)
    if collector_count == 0:
        add_check(
            "collectors_configured",
            "fail",
            "No collectors are configured.",
            observed=collector_count,
            expected=">=1",
        )
    elif collector_count < 3:
        add_check(
            "collectors_configured",
            "warn",
            "Collector count is lower than expected for Layer 1 coverage.",
            observed=collector_count,
            expected=">=3",
        )
    else:
        add_check(
            "collectors_configured",
            "pass",
            "Collectors are configured.",
            observed=collector_count,
            expected=">=3",
        )

    collector_snapshots = []
    stale_collectors: list[str] = []
    error_collectors: list[str] = []
    for collector in collectors:
        name = str(collector.get("name", "unknown"))
        last_error = collector.get("last_error")
        last_collection_time = _parse_iso_datetime(collector.get("last_collection_time"))
        age_seconds = None
        is_fresh = None
        if last_collection_time is not None:
            age_seconds = max(0, int((now - last_collection_time).total_seconds()))
            is_fresh = age_seconds <= freshness_sla_seconds
            if not is_fresh:
                stale_collectors.append(name)
        elif collection_count > 0:
            stale_collectors.append(name)

        if collector.get("status") == "error" or bool(last_error):
            error_collectors.append(name)

        collector_snapshots.append(
            {
                "name": name,
                "status": collector.get("status", "unknown"),
                "last_error": last_error,
                "last_collection_time": collector.get("last_collection_time"),
                "age_seconds": age_seconds,
                "is_fresh": is_fresh,
                "events_collected": collector.get("events_collected", 0),
                "last_replay_outcome": collector.get("last_replay_outcome"),
                "last_blob_name": collector.get("last_blob_name"),
            }
        )

    if error_collectors:
        add_check(
            "collector_errors",
            "fail",
            "One or more collectors are in error state.",
            observed=error_collectors,
            expected=[],
        )
    else:
        add_check(
            "collector_errors",
            "pass",
            "No collector errors detected.",
            observed=[],
            expected=[],
        )

    if collection_count == 0:
        add_check(
            "collector_freshness",
            "warn",
            "No collection cycle has completed yet.",
            observed=stale_collectors,
            expected=[],
        )
    elif stale_collectors:
        add_check(
            "collector_freshness",
            "warn",
            "Some collectors are stale or have not reported a recent collection timestamp.",
            observed=stale_collectors,
            expected=[],
        )
    else:
        add_check(
            "collector_freshness",
            "pass",
            "Collector freshness is within SLA.",
            observed=[],
            expected=[],
        )

    processed_events = total_posted + total_deduped
    if total_collected == 0:
        add_check(
            "event_flow",
            "warn",
            "No telemetry events collected yet.",
            observed=total_collected,
            expected=">0 after initial cycles",
        )
    elif processed_events == 0:
        add_check(
            "event_flow",
            "fail",
            "Collected events are not being posted or deduplicated.",
            observed={
                "collected": total_collected,
                "posted": total_posted,
                "deduped": total_deduped,
            },
            expected="posted + deduped > 0",
        )
    elif processed_events < total_collected:
        add_check(
            "event_flow",
            "warn",
            "Some collected events were neither posted nor deduplicated.",
            observed={
                "collected": total_collected,
                "posted": total_posted,
                "deduped": total_deduped,
            },
            expected="posted + deduped ~= collected",
        )
    else:
        add_check(
            "event_flow",
            "pass",
            "Event flow is healthy.",
            observed={
                "collected": total_collected,
                "posted": total_posted,
                "deduped": total_deduped,
            },
            expected="posted + deduped >= collected",
        )

    if total_deduped > total_collected:
        add_check(
            "dedup_behavior",
            "fail",
            "Dedup counter exceeds collected events, which indicates inconsistent counters.",
            observed={
                "collected": total_collected,
                "deduped": total_deduped,
                "cache_size": dedup_cache_size,
            },
            expected="deduped <= collected",
        )
    elif ingestion_mode == "sample_blob" and collection_count >= 2 and total_collected > 0 and total_deduped == 0:
        add_check(
            "dedup_behavior",
            "warn",
            "No deduplicated events observed yet in sample replay mode.",
            observed={
                "collection_count": collection_count,
                "deduped": total_deduped,
                "cache_size": dedup_cache_size,
            },
            expected="deduped > 0 after repeated replay",
        )
    else:
        add_check(
            "dedup_behavior",
            "pass",
            "Dedup behavior is within expected range.",
            observed={
                "collection_count": collection_count,
                "deduped": total_deduped,
                "cache_size": dedup_cache_size,
            },
            expected="deduped <= collected",
        )

    checks_failed = sum(1 for item in checks if item["status"] == "fail")
    checks_warned = sum(1 for item in checks if item["status"] == "warn")
    checks_passed = sum(1 for item in checks if item["status"] == "pass")
    overall_status = "fail" if checks_failed else ("warn" if checks_warned else "pass")

    return {
        "overall_status": overall_status,
        "evaluated_at": now.isoformat(),
        "ingestion_mode": ingestion_mode,
        "freshness_sla_seconds": freshness_sla_seconds,
        "summary": {
            "checks_total": len(checks),
            "checks_passed": checks_passed,
            "checks_warned": checks_warned,
            "checks_failed": checks_failed,
        },
        "checks": checks,
        "collector_overview": {
            "total_collectors": collector_count,
            "healthy_collectors": collector_count - len(error_collectors),
            "error_collectors": len(error_collectors),
            "stale_collectors": stale_collectors,
        },
        "collectors": collector_snapshots,
        "counters": {
            "interval_seconds": interval_seconds,
            "collection_count": collection_count,
            "total_events_collected": total_collected,
            "total_events_posted": total_posted,
            "total_events_deduped": total_deduped,
            "dedup_cache_size": dedup_cache_size,
            "last_collection_time": scheduler_status.get("last_collection_time"),
        },
    }

