"""Run Phase 3 Step 1 KQL signal packs against the configured Log Analytics workspace."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import sys
from typing import Any

from azure.core.exceptions import HttpResponseError
from azure.monitor.query import LogsQueryClient, LogsQueryStatus

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.azure_config import AzureConfig, get_azure_credential
from backend.collectors.kql_utils import rows_as_dicts


REPORT_PATH = Path("artifacts/phase3_step1_signal_pack_latest.json")
QUERY_DIR = Path("kql/phase3_step1")
QUERY_PACKS: list[tuple[str, str]] = [
    ("failed_request_rate", "01_failed_request_rate.kql"),
    ("latency_spike", "02_latency_spike.kql"),
    ("sql_connectivity_errors", "03_sql_connectivity_errors.kql"),
    ("nsg_deny_packet_drop", "04_nsg_deny_packet_drop.kql"),
]


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _render_query(raw_query: str, lookback_minutes: int) -> str:
    return raw_query.replace("{{LOOKBACK_MINUTES}}", str(lookback_minutes))


def _result_payload_rows(response: Any) -> list[dict[str, Any]]:
    if getattr(response, "status", None) == LogsQueryStatus.PARTIAL:
        return rows_as_dicts(response.partial_data)
    return rows_as_dicts(response)


def run_signal_pack() -> dict[str, Any]:
    lookback_minutes = max(5, int(AzureConfig.LOOKBACK_MINUTES or 5))
    report: dict[str, Any] = {
        "run_started_at": _utc_now_iso(),
        "phase": "Phase 3",
        "step": "Step 1",
        "version": "v0.3.0",
        "workspace_id": AzureConfig.LOG_ANALYTICS_WORKSPACE_ID,
        "lookback_minutes": lookback_minutes,
        "query_dir": str(QUERY_DIR),
        "result": "fail",
        "reason": "",
        "queries": [],
    }

    workspace_id = (AzureConfig.LOG_ANALYTICS_WORKSPACE_ID or "").strip()
    if not workspace_id:
        report["reason"] = "LOG_ANALYTICS_WORKSPACE_ID is not configured."
        report["run_finished_at"] = _utc_now_iso()
        return report

    client = LogsQueryClient(get_azure_credential())
    total_failures = 0
    total_warnings = 0

    for query_id, query_file in QUERY_PACKS:
        file_path = QUERY_DIR / query_file
        query_record: dict[str, Any] = {
            "id": query_id,
            "file": str(file_path),
            "status": "fail",
            "row_count": 0,
            "sample_rows": [],
            "error": None,
            "warning": None,
        }
        try:
            raw_query = file_path.read_text(encoding="utf-8")
            rendered_query = _render_query(raw_query, lookback_minutes)
            response = client.query_workspace(
                workspace_id=workspace_id,
                query=rendered_query,
                timespan=timedelta(minutes=max(lookback_minutes * 2, 30)),
            )
            rows = _result_payload_rows(response)
            query_record["row_count"] = len(rows)
            query_record["sample_rows"] = rows[:3]

            if getattr(response, "status", None) == LogsQueryStatus.PARTIAL:
                query_record["status"] = "warn"
                query_record["warning"] = str(getattr(response, "partial_error", "Partial result returned"))
                total_warnings += 1
            else:
                query_record["status"] = "pass"
        except FileNotFoundError:
            total_failures += 1
            query_record["error"] = f"query_file_missing: {file_path}"
        except HttpResponseError as exc:
            total_failures += 1
            query_record["error"] = f"http_response_error: {exc}"
        except Exception as exc:  # pragma: no cover - defensive
            total_failures += 1
            query_record["error"] = f"unexpected_error: {exc}"

        report["queries"].append(query_record)

    if total_failures == 0 and total_warnings == 0:
        report["result"] = "pass"
        report["reason"] = "All Phase 3 Step 1 signal pack queries executed successfully."
    elif total_failures == 0:
        report["result"] = "warn"
        report["reason"] = "Signal pack queries completed with partial results."
    else:
        report["result"] = "fail"
        report["reason"] = "One or more signal pack queries failed to execute."

    report["summary"] = {
        "queries_total": len(QUERY_PACKS),
        "queries_passed": sum(1 for item in report["queries"] if item["status"] == "pass"),
        "queries_warned": sum(1 for item in report["queries"] if item["status"] == "warn"),
        "queries_failed": sum(1 for item in report["queries"] if item["status"] == "fail"),
    }
    report["run_finished_at"] = _utc_now_iso()
    return report


def main() -> int:
    report = run_signal_pack()
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(f"Phase 3 Step 1 signal pack result: {report.get('result')}")
    print(f"Reason: {report.get('reason')}")
    print(f"Report: {REPORT_PATH}")
    return 0 if report.get("result") in {"pass", "warn"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
