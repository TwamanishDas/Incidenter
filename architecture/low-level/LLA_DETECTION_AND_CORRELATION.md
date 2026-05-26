# Low Level Architecture: Detection and Correlation

Working: Phase 3 | Step 2 | Version v0.3.0 (completed)

## Purpose

Define the detailed design for signal extraction, anomaly detection, and cross-layer correlation before RCA classification.

## Architecture Parts

1. Signal query pack:
   - failed request rate
   - latency spikes
   - SQL connectivity and timeout signals
   - NSG deny and packet-drop signals
2. Correlation enricher:
   - resource ID joins
   - time-window joins
   - correlation ID propagation
3. Enriched evidence output:
   - normalized evidence record for RCA engine input

## Inputs and Outputs

1. Inputs:
   - normalized ingestion events from scheduler pipeline
2. Processing:
   - query summarization + evidence scoring inputs
3. Outputs:
   - evidence bundles for incident classification

## Implementation Scope Linkage

1. Phase 3 (`v0.3.0`) primary scope:
   - Step 1 KQL signal packs
   - Step 2 correlation enricher
2. Early dependency in Phase 2:
   - requires stable live ingestion and freshness checks
3. Tracker source:
   - `MASTER_PHASE_STEP_TRACKER.md` -> Phase 3

## Plan of Action

1. Define canonical KQL templates per layer.
2. Define correlation policy by:
   - timestamp window,
   - resource relationship,
   - operation/correlation IDs.
3. Build evidence schema with deterministic fields.
4. Add validation tests for signal correctness and join behavior.

## Current Execution Status

1. Phase 3 Step 1 (KQL signal packs) completed:
   - `kql/phase3_step1/01_failed_request_rate.kql`
   - `kql/phase3_step1/02_latency_spike.kql`
   - `kql/phase3_step1/03_sql_connectivity_errors.kql`
   - `kql/phase3_step1/04_nsg_deny_packet_drop.kql`
   - validation artifact: `artifacts/phase3_step1_signal_pack_latest.json`
2. Phase 3 Step 2 (correlation enricher) completed:
   - metadata + time-window correlation implemented in `backend/correlation_enricher.py`
   - signal-row mapper implemented in `backend/signal_contract_mapper.py`
   - API exposure implemented:
   - `GET /correlations`
   - `GET /correlations/{correlation_id}`
   - validation runner:
   - `backend/scripts/run_phase3_step2_correlation.py`
   - validation artifact: `artifacts/phase3_step2_correlation_latest.json`

## Traceability

1. High-level parent:
   - `HIGH_LEVEL_ARCHITECTURE.md`
2. MVP scope:
   - `MVP_SCOPE.md`
   - `MVP_PHASE_ACTION_PLAN.md`
3. Downstream consumer:
   - `architecture/low-level/LLA_RCA_ENGINE_AND_INCIDENT_MODEL.md`
