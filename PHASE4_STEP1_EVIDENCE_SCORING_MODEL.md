# Phase 4 Step 1 Evidence Scoring Model

Working: Phase 4 | Step 1 | Version v0.4.0 (in progress)

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

## Step 1.2 - Dependency relationship scoring

Goal:
1. Add dependency-aware RCA scoring so incidents include blast-radius and layer-edge context.
2. Keep incident API unchanged while expanding `supporting_data.rca_scoring`.

Action:
1. Extended scoring model in:
   - `backend/processors.py`
2. Added dependency relationship model:
   - per-layer upstream/downstream map
   - dependency hint extraction (`correlation_id`, `resource_id`, operation and payload identity hints)
   - computed `dependency_relationship_score` in range `0.0..1.0`
   - generated dependency edges and estimated blast radius
3. Updated test coverage:
   - `backend/tests/test_rca_layer_scoring.py`
4. Updated execution runner checks:
   - `backend/scripts/run_phase4_step1_scoring.py`
   - runner now validates Step 1.2 model version and dependency fields
5. Refreshed artifact:
   - `artifacts/phase4_step1_scoring_latest.json`

Verify:
1. Unit tests:
   - `.\.venv\Scripts\python.exe -m unittest discover -s backend\tests -v`
   - Result: `Ran 22 tests ... OK`
2. Step 1.2 scoring runner:
   - `.\.venv\Scripts\python.exe backend\scripts\run_phase4_step1_scoring.py`
   - Result: `pass`
   - Reason: `Phase 4 Step 1.2 dependency scoring checks passed.`

Next:
1. Step 1.3: implement repeated-incident weighting.
2. Phase 4 Step 2: formalize RCA output contract fields and evidence linkage.
