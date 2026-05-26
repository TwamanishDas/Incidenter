# Phase 4 Step 2 RCA Output Contract

Working: Phase 4 | Step 2 | Version v0.4.0 (execution)

Purpose: finalize incident output fields and standardize RCA response contract for downstream consumers.

## Step 2.1 - Finalize incident output fields

Goal:
1. Define a stable output contract for all incident responses.
2. Ensure incident contract fields are derived from RCA scoring deterministically.

Action:
1. Extended incident model in:
   - `backend/models.py`
2. Finalized output fields added to `Incident`:
   - `probability_score`
   - `confidence_label`
   - `incident_signature`
   - `scoring_model_version`
   - `evidence_count`
   - `primary_evidence`
   - `supporting_evidence`
3. Added contract-mapping helper in:
   - `backend/processors.py`
   - Maps `supporting_data.rca_scoring` into output-level contract fields
4. Added/updated tests:
   - `backend/tests/test_incident_output_contract.py`
   - `backend/tests/test_rca_layer_scoring.py`
5. Added contract validation runner:
   - `backend/scripts/run_phase4_step2_contract.py`
6. Captured evidence artifact:
   - `artifacts/phase4_step2_contract_latest.json`

Verify:
1. Unit tests:
   - `.\.venv\Scripts\python.exe -m unittest discover -s backend\tests -v`
   - Result: `pass` (all tests green)
2. Step 2.1 contract runner:
   - `.\.venv\Scripts\python.exe backend\scripts\run_phase4_step2_contract.py`
   - Result: `pass`
   - Reason: `Phase 4 Step 2.1 incident output contract checks passed.`

Next:
1. Step 2.2: persist supporting evidence links.
2. Prepare persistence strategy for incident/evidence records beyond in-memory runtime.

## Step 2.2 - Persist supporting evidence links

Goal:
1. Persist evidence records and generate stable evidence links per incident.
2. Expose evidence retrieval APIs for incident-level and direct evidence lookup.

Action:
1. Added evidence record model:
   - `EvidenceRecord` in `backend/models.py`
2. Extended in-memory store:
   - `persist_incident_evidence`
   - `get_evidence_records`
   - `get_evidence_record`
   - `get_incident_evidence`
   - File: `backend/data_store.py`
3. Integrated persistence into ingestion flow:
   - `POST /telemetry` persists evidence for each detected incident
   - `POST /simulate` persists evidence for each detected incident
   - File: `backend/app.py`
4. Added evidence APIs:
   - `GET /incidents/{incident_id}/evidence`
   - `GET /evidence`
   - `GET /evidence/{evidence_id}`
5. Added tests:
   - `backend/tests/test_evidence_link_persistence.py`
6. Added runner:
   - `backend/scripts/run_phase4_step2_evidence_links.py`
7. Captured artifact:
   - `artifacts/phase4_step2_evidence_links_latest.json`

Verify:
1. Unit tests:
   - `.\.venv\Scripts\python.exe -m unittest discover -s backend\tests -v`
2. Step 2.2 runner:
   - `.\.venv\Scripts\python.exe backend\scripts\run_phase4_step2_evidence_links.py`
   - Result: `pass`

Next:
1. Phase 5 Step 1: incident dashboard implementation.
