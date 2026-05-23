# Low Level Architecture: Platform, Security, and Operations

Working: Phase 2 | Step 1 | Version v0.2.0 (planning)

## Purpose

Define non-functional architecture for identity, access, reliability, compliance, deployment safety, and handoff operations.

## Architecture Parts

1. Identity and authentication:
   - Managed Identity first
   - Service principal fallback for development
2. Access control:
   - Monitoring Reader + Log Analytics Reader RBAC minimum
3. Secrets and config:
   - `.env` local development
   - Key Vault target for production
4. Operational safety:
   - acceptance gates
   - release tags and rollback strategy
5. Reliability controls:
   - scheduler interval tuning
   - dedup and watermark behavior

## Inputs and Outputs

1. Inputs:
   - Azure policy/security standards
   - operational SLA targets
2. Processing:
   - environment hardening
   - runbook and control validation
3. Outputs:
   - secure deployment pattern
   - repeatable release/rollback workflow

## Implementation Scope Linkage

1. Phase 2:
   - secure live telemetry onboarding and environment validation.
2. Phase 6:
   - validation, handoff package, and operational runbook closure.
3. Tracker source:
   - `MASTER_PHASE_STEP_TRACKER.md` -> Phase 2 and Phase 6

## Plan of Action

1. Standardize environment and secret handling path.
2. Validate RBAC scopes for all telemetry sources.
3. Define acceptance gates per phase before tagging.
4. Document rollback + recovery playbooks.
5. Finalize production handoff checklist in Phase 6.

## Traceability

1. High-level parent:
   - `HIGH_LEVEL_ARCHITECTURE.md`
2. Cross-scope link:
   - `MVP_PHASE_ACTION_PLAN.md`
   - `PRODUCTION_READY_SCOPE.md`
3. Project tracker:
   - `MASTER_PHASE_STEP_TRACKER.md`
