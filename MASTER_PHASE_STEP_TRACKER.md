# Master Phase-Step Tracker

Working: Phase 2 | Step 2 | Version v0.2.0 (planning)

Purpose: single source of truth for phase, step, and sub-step execution status.

## Documentation Linkage

1. Top architecture entry:
   - `HIGH_LEVEL_ARCHITECTURE.md`
2. Telemetry source catalog:
   - `TELEMETRY_CATALOG.md`
3. Low-level architecture folder:
   - `architecture/low-level/`
4. MVP coverage and action mapping:
   - `MVP_SCOPE.md`
   - `MVP_PHASE_ACTION_PLAN.md`
5. Production-ready extension:
   - `PRODUCTION_READY_SCOPE.md`

## Version Map

1. `v0.1.0` - Phase 1 completion baseline (tagged and published).
2. `v0.2.0` - Phase 2 execution track (in progress).
3. `v0.3.0` - Phase 3 detection and correlation target.
4. `v0.4.0` - Phase 4 RCA engine target.
5. `v0.5.0` - Phase 5 dashboard and notifications target.
6. `v0.6.0` - Phase 6 validation and handoff target.

## Phase 1 - Data Ingestion Baseline (`v0.1.0`) [Completed]

### Step 1 - Sample data staged [Completed]
1. Sub-step 1.1: Sample ingestion payloads prepared.
2. Sub-step 1.2: Blob container/prefix aligned for replay.

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

## Phase 2 - Telemetry Collection Execution (`v0.2.0`) [In Progress]

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

### Step 2 - Ingestion tuning [In Progress]
1. Sub-step 2.1: tune `COLLECTION_INTERVAL`.
   - Updated local live setting to `COLLECTION_INTERVAL=30` (from 10) and revalidated:
   - `/scheduler/status` = 200 (`interval_seconds: 30`)
   - `/ingestion/checklist` = pass [Completed]
2. Sub-step 2.2: tune lookback/overlap/delay windows.
3. Sub-step 2.3: tune dedup window and verify false-positive suppression.

### Step 3 - Source coverage expansion [Pending]
1. Sub-step 3.1: validate per-source live event freshness.
2. Sub-step 3.2: expand monitored resource IDs.
3. Sub-step 3.3: update Layer 1 contract and source matrix.

### Step 4 - Phase 2 acceptance gate [Pending]
1. Sub-step 4.1: define live-mode acceptance checklist.
2. Sub-step 4.2: capture evidence artifact.
3. Sub-step 4.3: create `cp/p2-s4` checkpoint and `v0.2.0` release tag.

## Phase 3 - Detection and Correlation (`v0.3.0`) [Pending]

### Step 1 - KQL signal packs
1. Sub-step 1.1: failed request rate query.
2. Sub-step 1.2: latency spike query.
3. Sub-step 1.3: SQL connectivity error query.
4. Sub-step 1.4: NSG deny and packet-drop query.

### Step 2 - Correlation enricher
1. Sub-step 2.1: add metadata join strategy.
2. Sub-step 2.2: implement ingestion of query outputs to normalized contract.

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
