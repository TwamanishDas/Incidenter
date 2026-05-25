# Phase 2 Step 3 Source Coverage Expansion

Working: Phase 2 | Step 3 | Version v0.2.0 (planning)

Purpose: operational runbook to expand and validate live telemetry source coverage after ingestion tuning.

## Step 3.1 - Validate per-source live event freshness

Goal: prove all active collectors are healthy and fresh in live mode over repeated cycles.

Action:
1. Started backend in live mode.
2. Sampled:
   - `GET /scheduler/status`
   - `GET /ingestion/checklist`
3. Collected 3 samples across scheduler cycles (~70 seconds with `COLLECTION_INTERVAL=30`).

Verify:
1. Sample 1:
   - `collection_count=1`
   - `overall_status=pass`
   - `healthy_collectors=5`, `error_collectors=0`, `stale_collectors=0`
2. Sample 2:
   - `collection_count=2`
   - `overall_status=pass`
   - `healthy_collectors=5`, `error_collectors=0`, `stale_collectors=0`
3. Sample 3:
   - `collection_count=3`
   - `overall_status=pass`
   - `healthy_collectors=5`, `error_collectors=0`, `stale_collectors=0`
4. All collectors reported `status=healthy` with non-null `last_collection_time`.
5. Re-validation run on `2026-05-24` (local):
   - Sample 1: `collection_count=8`, `overall_status=pass`, `healthy_collectors=5`, `error_collectors=0`, `stale_collectors=0`
   - Sample 2: `collection_count=9`, `overall_status=pass`, `healthy_collectors=5`, `error_collectors=0`, `stale_collectors=0`
   - Sample 3: `collection_count=10`, `overall_status=pass`, `healthy_collectors=5`, `error_collectors=0`, `stale_collectors=0`
   - All collectors remained healthy with non-null `last_collection_time`.

Next: expand monitored resource IDs for additional live sources (Step 3.2).

## Step 3.2 - Expand monitored resource IDs

Goal: add additional target resources to increase live source coverage.

Action:
1. Expanded `.env` monitor configuration to include 3 SQL-scope resources:
   - `MONITOR_RESOURCE_IDS`
   - SQL Server: `.../providers/Microsoft.Sql/servers/sqlincidenter46744`
   - SQL DB: `.../providers/Microsoft.Sql/servers/sqlincidenter46744/databases/incidenterdb`
   - SQL DB (master): `.../providers/Microsoft.Sql/servers/sqlincidenter46744/databases/master`
2. Expanded `RESOURCE_REGION_OVERRIDES_JSON` with matching `centralindia` entries for all 3 IDs.
3. Restarted backend in live mode so updated `.env` values were reloaded.
4. Re-ran scheduler/checklist validation across multiple samples.

Verify:
1. Runtime config load confirms expanded scope:
   - `monitor_resource_count=3`
   - `region_override_count=3`
2. Validation samples:
   - Sample 1: `collection_count=1`, `overall_status=pass`, `healthy_collectors=5`, `error_collectors=0`, `stale_collectors=0`, `monitor_events_collected=2`
   - Sample 2: `collection_count=2`, `overall_status=pass`, `healthy_collectors=5`, `error_collectors=0`, `stale_collectors=0`, `monitor_events_collected=2`
   - Sample 3: `collection_count=2`, `overall_status=warn` (transient mid-cycle), `healthy_collectors=5`, `error_collectors=0`, `stale_collectors=0`, `monitor_events_collected=4`
3. Post-cycle recheck returned stable pass:
   - `/ingestion/checklist` `overall_status=pass`
   - `event_flow=pass`, `dedup_behavior=pass`

Next: update Layer 1 contract/source matrix with added sources (Step 3.3).

## Step 3.3 - Update Layer 1 contract and source matrix

Goal: align documentation contract with actual live-enabled sources.

Action:
1. Update:
   - `LAYER_1_DATA_CONTRACT.md`
   - `TELEMETRY_CATALOG.md` (if source schema coverage changed)
2. Record changes in tracker.

Verify:
1. Contract tables match current source coverage.
2. Tracker status and runbook references are in sync.

Next: proceed to Phase 2 Step 4 acceptance gate preparation.
