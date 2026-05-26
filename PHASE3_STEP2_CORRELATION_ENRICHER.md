# Phase 3 Step 2 Correlation Enricher

Working: Phase 3 | Step 2 | Version v0.3.0 (completed)

Purpose: implement metadata/time-window correlation logic and map KQL signal outputs into normalized `TelemetryEvent` contract for RCA-ready evidence.

## Step 2.1 - Add metadata join strategy

Goal: correlate related telemetry signals across layers instead of treating each signal independently.

Action:
1. Added real-time correlation enricher:
   - `backend/correlation_enricher.py`
2. Implemented join-token strategy across:
   - `correlation_id`
   - `resource_id`
   - `subscription_id`
   - `operation_name`
   - component-level payload keys (`application_name`, `database_name`, `source_ip`, `destination_ip`)
3. Implemented rolling time-window matching (default 15 minutes) and deduped bundle emission.
4. Added correlation evidence model:
   - `CorrelatedEvidence` in `backend/models.py`
5. Added in-memory correlation storage methods:
   - `add_correlation`, `get_correlations`, `get_correlation` in `backend/data_store.py`
6. Integrated enricher into live ingestion flow:
   - `POST /telemetry` now runs correlation after ingest.
   - `POST /simulate` now runs correlation after ingest.
7. Added API visibility for correlated output:
   - `GET /correlations`
   - `GET /correlations/{correlation_id}`

Verify:
1. Correlation unit tests pass:
   - `backend/tests/test_correlation_enricher.py`
2. Correlated bundles are emitted only when multi-source conditions are met.

Next: map signal-pack query output into normalized contract (Step 2.2).

## Step 2.2 - Implement ingestion of query outputs to normalized contract

Goal: convert KQL signal rows to `TelemetryEvent` so correlation and downstream RCA can use one canonical schema.

Action:
1. Added signal-to-contract mapper:
   - `backend/signal_contract_mapper.py`
2. Implemented mappings for all Phase 3 Step 1 query IDs:
   - `failed_request_rate` -> `TelemetrySource.APPLICATION`
   - `latency_spike` -> `TelemetrySource.APPLICATION`
   - `sql_connectivity_errors` -> `TelemetrySource.DATABASE`
   - `nsg_deny_packet_drop` -> `TelemetrySource.NETWORK`
3. Added Step 2 execution runner:
   - `backend/scripts/run_phase3_step2_correlation.py`
4. Runner behavior:
   - reads `artifacts/phase3_step1_signal_pack_latest.json`
   - maps rows to normalized events
   - runs correlation enricher on mapped events
   - executes synthetic probe to validate correlation path when live rows are empty
   - writes artifact `artifacts/phase3_step2_correlation_latest.json`

Verify:
1. Mapper unit tests pass:
   - `backend/tests/test_signal_contract_mapper.py`
2. Step 2 runner execution:
   - Command:
     - `.\.venv\Scripts\python.exe backend\scripts\run_phase3_step2_correlation.py`
   - Result: `pass`
   - Artifact:
     - `artifacts/phase3_step2_correlation_latest.json`
   - Summary:
     - correlation pipeline executed successfully
     - synthetic probe produced correlated evidence

Next: proceed to Phase 4 Step 1 (evidence scoring model), unless additional Phase 3 signal packs are requested.
