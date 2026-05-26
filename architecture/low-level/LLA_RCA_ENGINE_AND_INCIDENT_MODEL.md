# Low Level Architecture: RCA Engine and Incident Model

Working: Phase 4 | Step 2.1 | Version v0.4.0 (execution)

## Purpose

Define the RCA decision logic, evidence scoring model, and final incident output schema.

## Architecture Parts

1. Rule execution engine:
   - network signature rules
   - application signature rules
   - database signature rules
2. Evidence scorer:
   - confidence/probability scoring
   - cross-layer weight adjustments
3. Incident model:
   - `incident_type`
   - `likely_root_cause`
   - `probability_score`
   - `affected_component`
   - `supporting_evidence`

## Inputs and Outputs

1. Inputs:
   - correlated evidence bundles
   - dependency hints
2. Processing:
   - rule matching + weighted scoring
3. Outputs:
   - incident records exposed via API endpoints

## Implementation Scope Linkage

1. Current baseline:
   - rule-based logic exists in `backend/processors.py`.
2. Phase 4 (`v0.4.0`) target:
   - formal evidence scoring model
   - expanded incident output contract
3. Current Step status:
   - Step 1.1 layer signature weighting completed
   - Step 1.2 dependency relationship scoring completed
   - Step 1.3 repeated-incident weighting completed
   - Step 2.1 RCA output contract finalization next
4. Tracker source:
   - `MASTER_PHASE_STEP_TRACKER.md` -> Phase 4

## Plan of Action

1. Externalize rule definitions for maintainability.
2. Introduce explicit scoring weights per signal category.
3. Add incident explanation payload for transparent RCA.
4. Add repeat-incident pattern contribution to confidence scoring.
5. Validate with controlled failure scenarios in Phase 6.

## Traceability

1. High-level parent:
   - `HIGH_LEVEL_ARCHITECTURE.md`
2. Upstream dependency:
   - `architecture/low-level/LLA_DETECTION_AND_CORRELATION.md`
3. MVP and production scope:
   - `MVP_SCOPE.md`
   - `PRODUCTION_READY_SCOPE.md`
