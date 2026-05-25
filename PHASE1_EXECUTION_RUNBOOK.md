# Phase 1 Execution Runbook

Working: Phase 1 | Step 1-7 | Version v0.1.0

Purpose: consolidated operational runbook for the completed Phase 1 ingestion baseline.

## Step 1 - Sample data staged

Goal: prepare replay-ready sample telemetry.

Action:
1. Prepared sample payload set for the supported pilot sources.
2. Staged blob container/prefix layout for replay.

Verify:
1. Sample payload files are available under the replay structure.
2. Scheduler can discover replay blobs in configured container/prefix.

Next: enable ingestion mode switching.

## Step 2 - Ingestion mode switch

Goal: support both sample replay and live collection with one scheduler.

Action:
1. Added `INGESTION_MODE` handling in configuration.
2. Wired scheduler collector initialization for:
   - `sample_blob`
   - `live`

Verify:
1. Collector set changes based on `INGESTION_MODE`.
2. Scheduler starts successfully in both modes.

Next: validate end-to-end replay behavior.

## Step 3 - End-to-end replay validation

Goal: confirm replay data flows through scheduler to API.

Action:
1. Executed replay cycles through scheduler.
2. Validated posting path to `/telemetry`.

Verify:
1. Collection counters increment.
2. Posted event counters increment.

Next: harden replay diagnostics and tests.

## Step 4 - Hardening

Goal: improve reliability and visibility of replay mode.

Action:
1. Added replay diagnostics fields in collector status.
2. Added scheduler switch behavior tests.

Verify:
1. Status output includes replay metadata.
2. Tests pass for scheduler mode switching.

Next: add ingestion checklist endpoint.

## Step 5 - Ingestion checklist

Goal: provide a pass/warn/fail health endpoint for ingestion readiness.

Action:
1. Added `GET /ingestion/checklist`.
2. Implemented health checks for:
   - scheduler running
   - collector configuration/errors/freshness
   - event flow
   - dedup behavior

Verify:
1. Endpoint returns structured checklist JSON.
2. Unit tests cover checklist logic.

Next: run acceptance gate and freeze baseline.

## Step 6 - Acceptance and freeze

Goal: capture objective acceptance evidence for Phase 1.

Action:
1. Added acceptance evaluator/runner script.
2. Captured baseline artifact:
   - `artifacts/step6_acceptance_latest.json`
3. Froze baseline summary document:
   - `STEP6_MVP_INGESTION_BASELINE.md`

Verify:
1. Acceptance artifact generated successfully.
2. Baseline doc reflects final accepted state.

Next: prepare release notes and tags.

## Step 7 - Release and tags

Goal: package and publish Phase 1 baseline release.

Action:
1. Drafted release notes:
   - `releases/v0.1.0.md`
2. Created tags:
   - `cp/p1-s7`
   - `v0.1.0`
3. Pushed `main` and tags to remote.

Verify:
1. Release notes and tags are available in repository.
2. Tracker marks Phase 1 complete.

Next: start Phase 2 live telemetry onboarding.
