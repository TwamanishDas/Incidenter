"""Run Step 6 MVP ingestion acceptance against a local backend instance."""

from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from typing import Any

import requests

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.acceptance import evaluate_ingestion_acceptance


BASE_URL = "http://127.0.0.1:8000"
STARTUP_TIMEOUT_SECONDS = 40
MAX_ACCEPTANCE_WAIT_SECONDS = 120
POLL_SECONDS = 5
REPORT_PATH = Path("artifacts/step6_acceptance_latest.json")


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _get_json(path: str) -> tuple[int, dict[str, Any] | list[Any] | None]:
    response = requests.get(f"{BASE_URL}{path}", timeout=10)
    try:
        payload = response.json()
    except Exception:
        payload = None
    return response.status_code, payload


def _wait_for_health() -> bool:
    deadline = time.time() + STARTUP_TIMEOUT_SECONDS
    while time.time() < deadline:
        try:
            status_code, payload = _get_json("/health")
            if status_code == 200 and isinstance(payload, dict) and payload.get("status") == "healthy":
                return True
        except Exception:
            pass
        time.sleep(1)
    return False


def _start_backend() -> subprocess.Popen:
    env = os.environ.copy()
    cmd = [sys.executable, "-m", "uvicorn", "backend.app:app", "--host", "127.0.0.1", "--port", "8000"]
    return subprocess.Popen(
        cmd,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        env=env,
    )


def _stop_backend(process: subprocess.Popen | None):
    if process is None:
        return
    if process.poll() is not None:
        return
    try:
        process.terminate()
        process.wait(timeout=8)
    except Exception:
        process.kill()


def _collect_snapshot() -> dict[str, Any]:
    scheduler_status_code, scheduler_payload = _get_json("/scheduler/status")
    checklist_status_code, checklist_payload = _get_json("/ingestion/checklist")
    incidents_status_code, incidents_payload = _get_json("/incidents")

    incidents_count = len(incidents_payload) if isinstance(incidents_payload, list) else 0
    evaluation = evaluate_ingestion_acceptance(
        scheduler_payload if isinstance(scheduler_payload, dict) else None,
        checklist_payload if isinstance(checklist_payload, dict) else None,
        incidents_count=incidents_count,
    )

    return {
        "captured_at": _utc_now_iso(),
        "scheduler_status_code": scheduler_status_code,
        "checklist_status_code": checklist_status_code,
        "incidents_status_code": incidents_status_code,
        "scheduler_status": scheduler_payload,
        "ingestion_checklist": checklist_payload,
        "incidents_count": incidents_count,
        "evaluation": evaluation,
    }


def run_acceptance() -> dict[str, Any]:
    report: dict[str, Any] = {
        "run_started_at": _utc_now_iso(),
        "base_url": BASE_URL,
        "mode_expected": "sample_blob",
        "result": "fail",
        "reason": "",
        "attempts": [],
    }

    existing_backend = False
    backend_process: subprocess.Popen | None = None

    try:
        try:
            status_code, payload = _get_json("/health")
            existing_backend = status_code == 200 and isinstance(payload, dict) and payload.get("status") == "healthy"
        except Exception:
            existing_backend = False

        if not existing_backend:
            backend_process = _start_backend()
            if not _wait_for_health():
                report["reason"] = "Backend failed to start within timeout."
                return report

        deadline = time.time() + MAX_ACCEPTANCE_WAIT_SECONDS
        while time.time() < deadline:
            snapshot = _collect_snapshot()
            report["attempts"].append(snapshot)

            evaluation = snapshot.get("evaluation", {})
            if evaluation.get("overall_passed"):
                report["result"] = "pass"
                report["reason"] = "All Step 6 acceptance criteria passed."
                break

            time.sleep(POLL_SECONDS)

        if report["result"] != "pass":
            report["reason"] = report["reason"] or "Acceptance criteria did not pass within timeout."

        report["final_snapshot"] = report["attempts"][-1] if report["attempts"] else None
        report["run_finished_at"] = _utc_now_iso()
        return report
    finally:
        if not existing_backend:
            _stop_backend(backend_process)


def main() -> int:
    report = run_acceptance()
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(f"Step 6 acceptance result: {report.get('result')}")
    print(f"Reason: {report.get('reason')}")
    print(f"Report: {REPORT_PATH}")

    return 0 if report.get("result") == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
