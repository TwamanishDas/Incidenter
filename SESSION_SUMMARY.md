# AzureRCAPlanner Session Summary

## Purpose

This document captures the full state of the `AzureRCAPlanner` project and the conversation history needed to continue work in a new session.

The project is a pilot MVP for Azure incident flagging, forecasting, and root cause analysis (RCA) across:
- Network layer
- Application layer
- Database layer

It was created separately from the existing `AzureLens` project.

---

## Current Project Scope

- FastAPI backend that ingests telemetry events
- Rule-based RCA engine for network/application/database incidents
- In-memory incident store for MVP testing and validation
- Scenario simulation endpoints
- Phase 3 Azure integration plan and live collector framework implementations

---

## Key Files and Structure

### Root files
- `README.md` — MVP overview, running instructions, next steps
- `PILOT_RCA_MVP_PLAN.md` — pilot selection, architecture diagram, MVP deliverables, and phased implementation plan
- `PHASE_3_AZURE_INTEGRATION_PLAN.md` — Azure Layer 1 integration plan, collector architecture, auth strategy, expected telemetry formats, and success criteria
- `SESSION_SUMMARY.md` — this document
- `.env.example` — environment variables template for Azure integration

### Backend files
- `backend/app.py` — FastAPI app with endpoints:
  - `GET /health`
  - `POST /telemetry`
  - `GET /incidents`
  - `GET /incidents/{incident_id}`
  - `GET /forecast`
  - `POST /simulate`
- `backend/models.py` — Pydantic schema models for telemetry events, payloads, incidents, and simulation requests
- `backend/processors.py` — basic rule-based RCA engine that evaluates network, application, and database telemetry
- `backend/data_store.py` — in-memory storage for telemetry and incidents
- `backend/telemetry_samples.py` — prebuilt sample telemetry payloads for simulation
- `backend/requirements.txt` — dependencies for FastAPI and Azure SDK support
- `backend/azure_config.py` — Azure credential helper and configuration

### Azure integration components
- `backend/collectors/collector_base.py` — collector interface, watermark support, and status helpers
- `backend/collectors/log_analytics_collector.py` — Log Analytics + diagnostics + ingress/WAF collector
- `backend/collectors/appinsights_collector.py` — Application Insights collector (`query_resource` + strict ARM resource id)
- `backend/collectors/network_watcher_collector.py` — Network Watcher and network performance collector
- `backend/collectors/monitor_metrics_collector.py` — Azure Monitor metrics collector (SQL/VM + correlation enrichment)
- `backend/collectors/activity_health_collector.py` — Activity Log, Resource Health, and Service Health collector
- `backend/collectors/kql_utils.py` — shared KQL row/timestamp conversion utilities
- `backend/collectors/__init__.py` — package exports
- `backend/azure_scheduler/telemetry_scheduler.py` — scheduler with dedup, status tracking, and graceful stop behavior
- `backend/azure_scheduler/__init__.py` — package initializer

---

## What is working now

- The backend compiles successfully.
- The REST API endpoints are functional.
- Scenario simulation works for the following cases:
  - `network_spike`
  - `app_error`
  - `db_latency`
- A Pydantic validation issue was fixed by adding defaults to optional fields in `TelemetryEvent`.
- You verified the API behavior manually.
- Scheduler startup/shutdown lifecycle and dedup behavior were validated in local smoke tests.

---

## Current implementation details

### Latest update (May 22, 2026) - Step 4 hardening

- Added replay diagnostics to `backend/replay/blob_sample_collector.py` and exposed them via `GET /scheduler/status` for sample mode.
- New sample collector status fields now include:
  - `source_folder`, `source_prefix`
  - `last_blob_name`, `last_blob_candidate_count`, `last_blob_discovery_time`
  - `last_blob_list_status_code`, `last_blob_download_status_code`
  - `last_blob_records_parsed`, `last_replay_outcome`, `last_replay_error`
- Blob list/download failures now surface as collector errors (instead of silent empty results).
- Added unit tests under `backend/tests/`:
  - `test_blob_sample_collector.py`
  - `test_scheduler_switch_behavior.py`
- Validated scheduler switch behavior: changing `INGESTION_MODE` does **not** hot-swap collectors on an existing scheduler instance; reset/restart is required.
- Test command used:
  - `.\.venv\Scripts\python.exe -m unittest discover -s backend/tests -p "test_*.py" -v`

### Latest update (May 22, 2026) - Step 5 ingestion checklist

- Added ingestion checklist module: `backend/ingestion_health.py`.
- Added endpoint: `GET /ingestion/checklist`.
- Checklist includes pass/warn/fail checks for:
  - scheduler running state
  - collector configuration count
  - collector errors
  - collector freshness SLA
  - event flow (`collected`, `posted`, `deduped`)
  - dedup behavior consistency
- Endpoint behavior:
  - returns HTTP `503` when overall checklist status is `fail`
  - returns HTTP `200` for `pass` and `warn`
- Added tests in `backend/tests/test_ingestion_health.py`.

### Latest update (May 22, 2026) - Step 6 acceptance + baseline freeze

- Added Step 6 acceptance evaluator: `backend/acceptance.py`.
- Added acceptance runner script: `backend/scripts/run_step6_acceptance.py`.
- Acceptance runner behavior:
  - checks scheduler status, ingestion checklist status, and incidents endpoint
  - evaluates 6 explicit pass/fail criteria
  - writes report to `artifacts/step6_acceptance_latest.json`
  - returns exit code `0` on pass, `1` on fail
- Added tests in `backend/tests/test_acceptance.py`.
- Created baseline freeze document:
  - `STEP6_MVP_INGESTION_BASELINE.md`
  - contains validated run summary and rerun command.

### Data flow in MVP

1. Telemetry is posted to `POST /telemetry`.
2. `backend/models.py` validates the payload.
3. Data is stored in-memory via `backend/data_store.py`.
4. `backend/processors.py` evaluates the event and generates an `Incident` if thresholds are exceeded.
5. Incidents are available through `GET /incidents` and `GET /incidents/{id}`.
6. `GET /forecast` returns a placeholder forecast message.
7. `POST /simulate` injects sample telemetry and generates incidents.

### RCA logic

- Network events are evaluated for NSG deny counts, packet loss, latency, and TCP retries.
- Application events are evaluated for error rate, 5xx counts, average latency, and P95 latency.
- Database events are evaluated for connection errors, timeouts, deadlocks, and average query duration.

---

## How to run the MVP

From `AzureRCAPlanner`:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r backend/requirements.txt
uvicorn backend.app:app --reload --port 8000
```

Test endpoints:
- `GET http://127.0.0.1:8000/health`
- `POST http://127.0.0.1:8000/simulate` with `{"scenario":"network_spike"}`
- `GET http://127.0.0.1:8000/incidents`
- `GET http://127.0.0.1:8000/forecast`

---

## Phase 3: Azure Layer 1 Integration

This project has a dedicated Phase 3 plan in `PHASE_3_AZURE_INTEGRATION_PLAN.md`.

### Implementation goals
- Connect to Azure Log Analytics, Application Insights, Network Watcher, Azure Monitor, and Activity/Health feeds
- Implement collectors that translate Azure telemetry into the existing `TelemetryEvent` model
- Use Azure credentials via `backend/azure_config.py`
- Add a scheduler to poll Azure sources periodically
- Post collected telemetry to the existing ingestion pipeline

---

## Notes for the next session

- `AzureRCAPlanner` is the working pilot project.
- `AzureLens` is a separate workspace/project and should not be mixed with `AzureRCAPlanner` unless you explicitly decide to merge later.
- Continue Phase 3 by validating live Azure ingestion and tuning thresholds for your environment.
- After Phase 3, move to Phase 4 by replacing in-memory storage with Azure persistence (Cosmos DB or Azure SQL).
- Later phases will include forecasting, dashboarding, OS/middleware RCA, and real Azure incident visualization.

---

## Recommended next steps

1. Confirm Azure subscription / Log Analytics workspace IDs and Application Insights resource ID (ARM path).
2. Populate `.env.example` with local development values and rename to `.env`.
3. Validate all configured collectors against live Azure telemetry in your subscriptions.
4. Tune collection interval/lookback/dedup settings for your ingestion latency profile.
5. Validate incident quality and root-cause confidence with controlled failure drills.
6. Add persistent storage and dashboard support.

---

## Current known state

- MVP backend and simulation are validated.
- Phase 3 architecture and Azure collectors are implemented with scheduler orchestration.
- No frontend dashboard has been implemented yet.
- The system currently uses in-memory storage only.

If you open a new session later, start by reading this file and then inspect:
- `backend/app.py`
- `backend/processors.py`
- `backend/collectors/`
- `PHASE_3_AZURE_INTEGRATION_PLAN.md`
- `PILOT_RCA_MVP_PLAN.md`
