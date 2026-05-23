# Production Ready Scope

Working: Phase 2 | Step 1 | Version v0.2.0 (planning)

Purpose: define production-grade components beyond MVP and connect them to phase tracking.

## Production Component Set

1. Persistent incident and evidence store.
2. Hardened identity and secret management with Key Vault and Managed Identity.
3. HA and DR strategy for ingestion and RCA pipeline.
4. SLO/SLA observability and on-call runbooks.
5. Governance, policy, compliance, and audit controls.
6. CI/CD release gates and rollout/rollback automation.
7. Capacity and cost controls for telemetry and compute paths.

## Upgrade Path from MVP

1. Phase 2:
   - stabilize live telemetry collection and tuning.
2. Phase 3:
   - productionize query and correlation reliability.
3. Phase 4:
   - formalize RCA scoring and explainability guarantees.
4. Phase 5:
   - add production UX, access model, and notification reliability.
5. Phase 6:
   - execute resilience drills and finalize handoff controls.
6. Post-Phase 6:
   - transition to managed release train with security and compliance gates.

## Architecture Linkage

1. High-level architecture:
   - `HIGH_LEVEL_ARCHITECTURE.md`
2. Low-level architecture files:
   - `architecture/low-level/LLA_INGESTION_AND_OBSERVABILITY.md`
   - `architecture/low-level/LLA_DETECTION_AND_CORRELATION.md`
   - `architecture/low-level/LLA_RCA_ENGINE_AND_INCIDENT_MODEL.md`
   - `architecture/low-level/LLA_DASHBOARD_AND_ALERTING.md`
   - `architecture/low-level/LLA_PLATFORM_SECURITY_AND_OPERATIONS.md`

## Tracking Linkage

1. Master phase/step/sub-step tracker:
   - `MASTER_PHASE_STEP_TRACKER.md`
2. MVP execution plan:
   - `MVP_PHASE_ACTION_PLAN.md`
3. Session continuity:
   - `SESSION_SUMMARY.md`
