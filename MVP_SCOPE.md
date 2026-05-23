# MVP Scope

Working: Phase 2 | Step 1 | Version v0.2.0 (planning)

Purpose: define all components included in MVP and their phase linkage.

## MVP Component Coverage

1. Ingestion and normalization pipeline.
2. Live telemetry onboarding from Azure sources.
3. Detection and correlation baseline (query packs + evidence shaping).
4. Rule-based RCA engine with explainable outputs.
5. Basic dashboard and notification path.
6. Validation and handoff package.

## Component to Phase Mapping

1. Ingestion baseline:
   - Phase 1 (completed)
2. Live telemetry collection:
   - Phase 2 (in progress)
3. Detection and correlation:
   - Phase 3
4. RCA scoring and incident contract:
   - Phase 4
5. Dashboard and alerts:
   - Phase 5
6. Drill validation and handoff:
   - Phase 6

## Architecture Linkage

1. High-level architecture:
   - `HIGH_LEVEL_ARCHITECTURE.md`
2. Low-level architecture:
   - `architecture/low-level/LLA_INGESTION_AND_OBSERVABILITY.md`
   - `architecture/low-level/LLA_DETECTION_AND_CORRELATION.md`
   - `architecture/low-level/LLA_RCA_ENGINE_AND_INCIDENT_MODEL.md`
   - `architecture/low-level/LLA_DASHBOARD_AND_ALERTING.md`
   - `architecture/low-level/LLA_PLATFORM_SECURITY_AND_OPERATIONS.md`

## Tracker Linkage

1. Phase/step/sub-step tracker:
   - `MASTER_PHASE_STEP_TRACKER.md`
2. MVP action plan:
   - `MVP_PHASE_ACTION_PLAN.md`
