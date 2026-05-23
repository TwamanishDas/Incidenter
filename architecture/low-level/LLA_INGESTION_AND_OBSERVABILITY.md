# Low Level Architecture: Ingestion and Observability

Working: Phase 2 | Step 1 | Version v0.2.0 (planning)

## Purpose

Define internals for telemetry ingestion, normalization, scheduler orchestration, and source collectors.

## Architecture Parts

1. Collector contract:
   - `backend/collectors/collector_base.py`
2. Source collectors:
   - Log Analytics collector
   - Application Insights collector
   - Network Watcher collector
   - Monitor Metrics collector
   - Activity/Health collector
3. Scheduler:
   - `backend/azure_scheduler/telemetry_scheduler.py`
4. Ingestion health and acceptance:
   - `backend/ingestion_health.py`
   - `backend/acceptance.py`

## Inputs and Outputs

1. Inputs:
   - Azure Monitor APIs
   - Log Analytics KQL results
   - App Insights query results
2. Internal normalized contract:
   - `LAYER_1_DATA_CONTRACT.md`
   - `TELEMETRY_CATALOG.md`
   - `TelemetryEvent` in `backend/models.py`
3. Output:
   - events posted to `POST /telemetry`

## Implementation Scope Linkage

1. Phase 1 (completed):
   - Steps 1-7 completed and tagged (`v0.1.0`).
2. Phase 2 (active):
   - Step 1.2 through Step 1.8 are the immediate scope for live ingestion.
3. Tracker source:
   - `MASTER_PHASE_STEP_TRACKER.md` -> Phase 2 -> Step 1.

## Plan of Action

1. Finish local prerequisites (`az` installation and login).
2. Provision and connect telemetry sources (LAW, App Insights, SQL diagnostics, NSG flow logs).
3. Bind `.env` live-mode settings.
4. Validate `/scheduler/status` and `/ingestion/checklist`.
5. Move to tuning window/dedup strategy in Phase 2 Step 2.
6. Onboard custom/vendor sources using schema-type rules:
   - custom -> persist full `raw`
   - vendor -> require `parser_version`

## Traceability

1. High-level parent:
   - `HIGH_LEVEL_ARCHITECTURE.md`
2. MVP scope:
   - `MVP_SCOPE.md`
   - `MVP_PHASE_ACTION_PLAN.md`
3. Production extension:
   - `PRODUCTION_READY_SCOPE.md`
