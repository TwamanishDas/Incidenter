# Documentation Structure and Governance

Working: Phase 3 | Step 1 | Version v0.3.0 (next)

Purpose: define how documentation is organized, named, and maintained so phase/step execution is consistent.

## 1. Single Source of Truth

1. Execution status:
   - `MASTER_PHASE_STEP_TRACKER.md`
2. Execution plans:
   - `MVP_PHASE_ACTION_PLAN.md`
   - `PILOT_RCA_MVP_PLAN.md`
3. Per-step operational runbooks:
   - `PHASE1_EXECUTION_RUNBOOK.md`
   - `PHASE2_STEP1_TELEMETRY_COLLECTION_KICKOFF.md`
   - `PHASE2_STEP2_INGESTION_TUNING.md`
   - `PHASE2_STEP3_SOURCE_COVERAGE_EXPANSION.md`
   - `PHASE2_STEP4_ACCEPTANCE_GATE.md`

## 2. Naming Convention

1. Runbook naming:
   - `PHASE{N}_STEP{M}_{SHORT_NAME}.md`
2. Phase-wide runbook naming:
   - `PHASE{N}_EXECUTION_RUNBOOK.md`
3. Architecture docs:
   - `HIGH_LEVEL_ARCHITECTURE.md`
   - `architecture/low-level/LLA_*.md`
4. Scope docs:
   - `MVP_SCOPE.md`
   - `PRODUCTION_READY_SCOPE.md`
5. Release docs:
   - `releases/v{X.Y.Z}.md`

## 3. Required Documents Per Phase

1. Before phase start:
   - step runbook(s) for planned execution
   - tracker entries for all steps/sub-steps
2. During execution:
   - update tracker with completion evidence
   - update runbook with real executed values where useful
3. Phase close:
   - acceptance/baseline artifact reference
   - release notes + tags

## 4. Authoring Rules

1. Every runbook must use:
   - Goal
   - Action
   - Verify
   - Next
2. Every runbook must include:
   - `Working: Phase <X> | Step <Y> | Version <Z>`
3. Do not store secrets in markdown.
4. If resource IDs are documented, keep them operationally relevant and update when changed.

## 5. Current Runbook Coverage

1. Phase 1:
   - `PHASE1_EXECUTION_RUNBOOK.md` (present)
2. Phase 2:
   - Step 1: `PHASE2_STEP1_TELEMETRY_COLLECTION_KICKOFF.md` (present)
   - Step 2: `PHASE2_STEP2_INGESTION_TUNING.md` (present)
   - Step 3: `PHASE2_STEP3_SOURCE_COVERAGE_EXPANSION.md` (present)
   - Step 4: `PHASE2_STEP4_ACCEPTANCE_GATE.md` (present)
3. Upcoming required:
   - Phase 3 Step 1 runbook
