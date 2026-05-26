# Low Level Architecture: Dashboard and Alerting

Working: Phase 5 | Step 1.1 | Version v0.5.0 (execution)

## Purpose

Define the user-facing investigation view and notification paths for active incidents and RCA outcomes.

## Architecture Parts

1. Dashboard view model:
   - active incidents
   - root-cause summary
   - impact and trend view
2. Drill-down model:
   - links to App Insights queries
   - links to Log Analytics/KQL investigation context
3. Alerting channels:
   - Azure Monitor alerts
   - Teams/email notifications

## Inputs and Outputs

1. Inputs:
   - incident records from RCA engine
2. Processing:
   - transform incident output for UI and notifications
3. Outputs:
   - dashboard cards/tables/charts
   - notification payloads with evidence summary

## Implementation Scope Linkage

1. Phase 5 (`v0.5.0`) primary scope:
   - dashboard implementation
   - notification integration
2. Dependency:
   - requires stable incident contract from Phase 4
3. Current step status:
   - Step 1.1 active incident list API completed
   - Step 1.2 RCA summary panel pending
   - Step 1.3 trend/forecast chart payload pending
4. Tracker source:
   - `MASTER_PHASE_STEP_TRACKER.md` -> Phase 5

## Plan of Action

1. Freeze incident response schema required by UI.
2. Build a minimal active-incident dashboard first.
3. Add RCA detail panel with supporting evidence.
4. Configure alert rules for highest severity incident categories.
5. Add channel-specific templates (Teams/email).

## Traceability

1. High-level parent:
   - `HIGH_LEVEL_ARCHITECTURE.md`
2. Upstream dependency:
   - `architecture/low-level/LLA_RCA_ENGINE_AND_INCIDENT_MODEL.md`
3. Delivery scope:
   - `MVP_SCOPE.md`
   - `PRODUCTION_READY_SCOPE.md`
