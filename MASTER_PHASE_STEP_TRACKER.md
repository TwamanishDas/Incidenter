# Master Phase-Step Tracker

Working: Phase 4 | Step 1 | Version v0.4.0 (next)

Purpose: single source of truth for phase, step, and sub-step execution status.

## Documentation Linkage

1. Documentation structure and governance:
   - `DOCUMENTATION_STRUCTURE.md`
2. Top architecture entry:
   - `HIGH_LEVEL_ARCHITECTURE.md`
3. Telemetry source catalog:
   - `TELEMETRY_CATALOG.md`
4. Low-level architecture folder:
   - `architecture/low-level/`
5. MVP coverage and action mapping:
   - `MVP_SCOPE.md`
   - `MVP_PHASE_ACTION_PLAN.md`
6. Operational runbooks:
   - `PHASE1_EXECUTION_RUNBOOK.md`
   - `PHASE2_STEP1_TELEMETRY_COLLECTION_KICKOFF.md`
   - `PHASE2_STEP2_INGESTION_TUNING.md`
   - `PHASE2_STEP3_SOURCE_COVERAGE_EXPANSION.md`
   - `PHASE2_STEP4_ACCEPTANCE_GATE.md`
   - `PHASE3_STEP1_KQL_SIGNAL_PACKS.md`
   - `PHASE3_STEP2_CORRELATION_ENRICHER.md`
7. Production-ready extension:
   - `PRODUCTION_READY_SCOPE.md`

## Version Map

1. `v0.1.0` - Phase 1 completion baseline (tagged and published).
2. `v0.2.0` - Phase 2 execution track (completed and tagged).
3. `v0.3.0` - Phase 3 detection and correlation track (in progress).
4. `v0.4.0` - Phase 4 RCA engine target.
5. `v0.5.0` - Phase 5 dashboard and notifications target.
6. `v0.6.0` - Phase 6 validation and handoff target.

## Phase 1 - Data Ingestion Baseline (`v0.1.0`) [Completed]

### Step 1 - Sample data staged [Completed]
1. Sub-step 1.1: Sample ingestion payloads prepared.
2. Sub-step 1.2: Blob container/prefix aligned for replay.
3. Runbook reference:
   - `PHASE1_EXECUTION_RUNBOOK.md`

### Step 2 - Ingestion mode switch [Completed]
1. Sub-step 2.1: `INGESTION_MODE` support added.
2. Sub-step 2.2: `sample_blob` and `live` collector wiring validated.

### Step 3 - End-to-end replay validation [Completed]
1. Sub-step 3.1: Scheduler replay cycles verified.
2. Sub-step 3.2: Event posting path verified.

### Step 4 - Hardening [Completed]
1. Sub-step 4.1: Replay diagnostics added in sample collector status.
2. Sub-step 4.2: Scheduler switch behavior tests added.

### Step 5 - Ingestion checklist [Completed]
1. Sub-step 5.1: `GET /ingestion/checklist` endpoint added.
2. Sub-step 5.2: pass/warn/fail checks and tests validated.

### Step 6 - Acceptance and freeze [Completed]
1. Sub-step 6.1: Acceptance evaluator + runner script added.
2. Sub-step 6.2: Baseline artifact captured in `artifacts/step6_acceptance_latest.json`.
3. Sub-step 6.3: Baseline document frozen in `STEP6_MVP_INGESTION_BASELINE.md`.

### Step 7 - Release and tags [Completed]
1. Sub-step 7.1: Release notes drafted in `releases/v0.1.0.md`.
2. Sub-step 7.2: Checkpoint tag created: `cp/p1-s7`.
3. Sub-step 7.3: Release tag created: `v0.1.0`.
4. Sub-step 7.4: Pushed to GitHub (`origin/main` and tags).

## Phase 2 - Telemetry Collection Execution (`v0.2.0`) [Completed]

### Step 1 - Azure telemetry setup kickoff [Completed]
1. Sub-step 1.1: Create operational runbook:
   - `PHASE2_STEP1_TELEMETRY_COLLECTION_KICKOFF.md` [Completed]
2. Sub-step 1.2: Local prerequisites:
   - Azure CLI installed in project `.venv`; `az --version` verified [Completed]
3. Sub-step 1.3: Azure login and subscription selection (`1f5ee0d1-cee1-4424-9768-4eac65a0ad83`) [Completed]
4. Sub-step 1.4: Log Analytics workspace provisioning (`law-incidenter-pilot`) [Completed]
5. Sub-step 1.5: Workspace-based Application Insights setup (`appi-incidenter-pilot`) [Completed]
6. Sub-step 1.6: SQL diagnostics enablement (`sql-to-law` on `incidenterdb`) [Completed]
7. Sub-step 1.7: Network flow telemetry enablement:
   - NSG flow logs retired by Azure policy; switched to VNet flow logs (`incidenter-vnet-flowlog`) [Completed]
8. Sub-step 1.8: Local `.env` live mode configuration and scheduler validation:
   - `/scheduler/status` = 200
   - `/ingestion/checklist` = pass [Completed]
9. Sub-step 1.9: Architecture documentation hierarchy (high-level -> low-level -> scope -> tracker) [Completed]
10. Sub-step 1.10: Telemetry metrics catalog integration (docs + schema-aware ingestion model + metric collector expansion) [Completed]

### Step 2 - Ingestion tuning [Completed]
1. Sub-step 2.1: tune `COLLECTION_INTERVAL`.
   - Updated local live setting to `COLLECTION_INTERVAL=30` (from 10) and revalidated:
   - `/scheduler/status` = 200 (`interval_seconds: 30`)
   - `/ingestion/checklist` = pass [Completed]
2. Sub-step 2.2: tune lookback/overlap/delay windows.
   - Updated local live settings:
   - `LOOKBACK_MINUTES=7`
   - `LOOKBACK_OVERLAP_SECONDS=45`
   - `INGESTION_DELAY_SECONDS=90`
   - Revalidated `/scheduler/status` = 200 and `/ingestion/checklist` = pass [Completed]
3. Sub-step 2.3: tune dedup window and verify false-positive suppression.
   - Retained `DEDUP_WINDOW_MINUTES=10` after live validation across 2 cycles:
   - `collection_count=2`, `total_events_collected=2`, `total_events_posted=2`, `total_events_deduped=0`
   - No false-positive suppression observed; checklist `dedup_behavior` = pass [Completed]
4. Runbook reference:
   - `PHASE2_STEP2_INGESTION_TUNING.md`

### Step 3 - Source coverage expansion [Completed]
1. Sub-step 3.1: validate per-source live event freshness.
   - Live validation executed across 3 samples (~70 seconds total, interval=30s):
   - Sample 1: `collection_count=1`, checklist=`pass`, `healthy_collectors=5`, `error_collectors=0`, `stale_collectors=0`
   - Sample 2: `collection_count=2`, checklist=`pass`, `healthy_collectors=5`, `error_collectors=0`, `stale_collectors=0`
   - Sample 3: `collection_count=3`, checklist=`pass`, `healthy_collectors=5`, `error_collectors=0`, `stale_collectors=0`
   - All configured collectors reported `status=healthy` with non-null `last_collection_time` [Completed]
   - Re-validated on `2026-05-24`: Sample counts `8 -> 9 -> 10`, checklist=`pass`, `healthy_collectors=5`, `error_collectors=0`, `stale_collectors=0`, all collectors had non-null `last_collection_time` [Completed]
2. Sub-step 3.2: expand monitored resource IDs.
   - Expanded `MONITOR_RESOURCE_IDS` from 1 to 3 SQL-scope resource IDs:
   - SQL server, `incidenterdb`, and `master` database resource IDs
   - Expanded `RESOURCE_REGION_OVERRIDES_JSON` to 3 `centralindia` mappings
   - Restarted live backend and validated:
   - Runtime config load: `monitor_resource_count=3`, `region_override_count=3`
   - Checklist stable pass after restart: `healthy_collectors=5`, `error_collectors=0`, `stale_collectors=0`, `event_flow=pass`, `dedup_behavior=pass` [Completed]
3. Sub-step 3.3: update Layer 1 contract and source matrix.
   - `LAYER_1_DATA_CONTRACT.md` updated with:
   - SP-first auth contract
   - Step 3.3 live source matrix snapshot
   - explicit distinction between collector capability and current pilot config
   - `TELEMETRY_CATALOG.md` updated with Step 3.3 live source matrix snapshot
   - Live scope captured as 5 enabled collectors with `MONITOR_RESOURCE_IDS` set to 3 SQL-scope IDs
   - Validation alignment check:
   - `/ingestion/checklist` `overall_status=pass`
   - `healthy_collectors=5`, `error_collectors=0`, `stale_collectors=0` [Completed]
4. Runbook reference:
   - `PHASE2_STEP3_SOURCE_COVERAGE_EXPANSION.md`

### Step 4 - Phase 2 acceptance gate [Completed]
1. Sub-step 4.1: define live-mode acceptance checklist.
   - Implemented executable checker:
   - `backend/scripts/run_phase2_step4_acceptance.py`
   - 12 acceptance criteria codified for live mode [Completed]
2. Sub-step 4.2: capture evidence artifact.
   - Executed Phase 2 Step 4 acceptance runner:
   - `.\.venv\Scripts\python.exe backend\scripts\run_phase2_step4_acceptance.py`
   - Artifact saved: `artifacts/phase2_step4_acceptance_latest.json`
   - Result: `pass` (`criteria_passed=12`, `criteria_failed=0`) [Completed]
3. Sub-step 4.3: create `cp/p2-s4` checkpoint and `v0.2.0` release tag.
   - Release notes prepared: `releases/v0.2.0.md`
   - Checkpoint tag created: `cp/p2-s4`
   - Release tag created: `v0.2.0` [Completed]
4. Runbook reference:
   - `PHASE2_STEP4_ACCEPTANCE_GATE.md`

## Phase 3 - Detection and Correlation (`v0.3.0`) [Completed]

### Step 1 - KQL signal packs [Completed]
1. Sub-step 1.1: failed request rate query.
   - Implemented: `kql/phase3_step1/01_failed_request_rate.kql` [Completed]
2. Sub-step 1.2: latency spike query.
   - Implemented: `kql/phase3_step1/02_latency_spike.kql` [Completed]
3. Sub-step 1.3: SQL connectivity error query.
   - Implemented: `kql/phase3_step1/03_sql_connectivity_errors.kql` [Completed]
4. Sub-step 1.4: NSG deny and packet-drop query.
   - Implemented: `kql/phase3_step1/04_nsg_deny_packet_drop.kql` [Completed]
5. Validation:
   - Runner: `backend/scripts/run_phase3_step1_signal_pack.py`
   - Artifact: `artifacts/phase3_step1_signal_pack_latest.json`
   - Result: `pass` (`queries_passed=4`, `queries_failed=0`) [Completed]
6. Runbook reference:
   - `PHASE3_STEP1_KQL_SIGNAL_PACKS.md`

### Step 2 - Correlation enricher [Completed]
1. Sub-step 2.1: add metadata join strategy.
   - Implemented `backend/correlation_enricher.py` with join tokens across:
   - correlation ID, resource ID, subscription ID, operation name, and component keys
   - Added rolling 15-minute time-window matching + duplicate bundle suppression [Completed]
2. Sub-step 2.2: implement ingestion of query outputs to normalized contract.
   - Implemented `backend/signal_contract_mapper.py` to map Phase 3 Step 1 query rows into `TelemetryEvent` [Completed]
3. Sub-step 2.3: expose correlated evidence through API and store.
   - Added `CorrelatedEvidence` model in `backend/models.py`
   - Added correlation storage methods in `backend/data_store.py`
   - Added API endpoints:
   - `GET /correlations`
   - `GET /correlations/{correlation_id}` [Completed]
4. Sub-step 2.4: validate Step 2 execution.
   - Unit tests:
   - `backend/tests/test_correlation_enricher.py`
   - `backend/tests/test_signal_contract_mapper.py`
   - Runner:
   - `.\.venv\Scripts\python.exe backend\scripts\run_phase3_step2_correlation.py`
   - Artifact:
   - `artifacts/phase3_step2_correlation_latest.json`
   - Result: `pass` [Completed]
5. Runbook reference:
   - `PHASE3_STEP2_CORRELATION_ENRICHER.md`

## Phase 4 - RCA Engine (`v0.4.0`) [Pending]

### Step 1 - Evidence scoring model
1. Sub-step 1.1: layer signature weighting.
2. Sub-step 1.2: dependency relationship scoring.
3. Sub-step 1.3: repeated-incident weighting.

### Step 2 - RCA output contract
1. Sub-step 2.1: finalize incident output fields.
2. Sub-step 2.2: persist supporting evidence links.

## Phase 5 - Dashboard and Notifications (`v0.5.0`) [Pending]

### Step 1 - Incident dashboard
1. Sub-step 1.1: active incident list.
2. Sub-step 1.2: RCA summary panel.
3. Sub-step 1.3: trend/forecast chart.

### Step 2 - Alert delivery
1. Sub-step 2.1: monitor alert rules.
2. Sub-step 2.2: Teams/email integration.

## Phase 6 - Validation and Handoff (`v0.6.0`) [Pending]

### Step 1 - Controlled failure drills
1. Sub-step 1.1: SQL degradation scenario.
2. Sub-step 1.2: application error injection scenario.
3. Sub-step 1.3: network route/DNS issue scenario.

### Step 2 - Handoff package
1. Sub-step 2.1: final acceptance evidence.
2. Sub-step 2.2: operations runbook.
3. Sub-step 2.3: release notes and final tag.
