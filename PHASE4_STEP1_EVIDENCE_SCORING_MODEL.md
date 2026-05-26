# Phase 4 Step 1 Evidence Scoring Model

Working: Phase 4 | Step 1 | Version v0.4.0 (execution)

Purpose: implement a formal RCA evidence scoring baseline for deterministic, explainable incident confidence.

## Step 1.1 - Layer signature weighting

Goal:
1. Add deterministic layer-level scoring to incident detection.
2. Keep current incident API contract stable while exposing scoring details in `supporting_data`.

Action:
1. Added weighted signal scoring helpers in:
   - `backend/processors.py`
2. Implemented per-layer signal weights:
   - Network: `nsg_denied_connections`, `packet_loss`, `avg_latency_ms`, `tcp_retry_count`
   - Application: `error_rate_or_5xx`, `avg_response_ms`, `p95_response_ms`
   - Database: `connection_errors`, `timeout_count`, `deadlock_count`, `avg_query_duration_ms`
3. Added normalized scoring output under:
   - `Incident.supporting_data["rca_scoring"]`
4. Added unit tests:
   - `backend/tests/test_rca_layer_scoring.py`
5. Added execution runner:
   - `backend/scripts/run_phase4_step1_scoring.py`
6. Captured artifact:
   - `artifacts/phase4_step1_scoring_latest.json`

Verify:
1. Unit tests:
   - `.\.venv\Scripts\python.exe -m unittest discover -s backend\tests -v`
   - Result: `Ran 22 tests ... OK`
2. Step 1.1 scoring runner:
   - `.\.venv\Scripts\python.exe backend\scripts\run_phase4_step1_scoring.py`
   - Result: `pass`
   - Reason: `Phase 4 Step 1.1 layer-signature scoring checks passed.`

Next:
1. Step 1.2: implement dependency relationship scoring.
2. Step 1.3: implement repeated-incident weighting.
3. Phase 4 Step 2: formalize RCA output contract fields and evidence linkage.
