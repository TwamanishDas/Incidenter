# Phase 2 Step 2 Ingestion Tuning

Working: Phase 2 | Step 2 | Version v0.2.0 (planning)

Purpose: operational runbook for tuning live ingestion behavior after Step 1 telemetry onboarding.

## Step 2.1 - Tune collection interval

Goal: reduce API pressure while preserving near-real-time telemetry.

Action:
1. Set `COLLECTION_INTERVAL=30` in `.env` (from 10).
2. Restarted backend scheduler.
3. Ran:
   - `GET /scheduler/status`
   - `GET /ingestion/checklist`

Verify:
1. `/scheduler/status` reports `interval_seconds: 30`.
2. `/ingestion/checklist` returns overall `pass`.

Next: tune lookback/overlap/delay windows.

## Step 2.2 - Tune lookback, overlap, and ingestion delay

Goal: avoid missing late-indexed telemetry while limiting duplicate processing.

Action:
1. Updated `.env`:
   - `LOOKBACK_MINUTES=7`
   - `LOOKBACK_OVERLAP_SECONDS=45`
   - `INGESTION_DELAY_SECONDS=90`
2. Restarted backend scheduler.
3. Re-ran scheduler and checklist endpoints.

Verify:
1. Scheduler remains healthy.
2. Checklist remains `pass` with no collector freshness/error regressions.

Next: validate dedup behavior.

## Step 2.3 - Validate dedup window behavior

Goal: confirm dedup suppression is correct and does not create false positives.

Action:
1. Kept `DEDUP_WINDOW_MINUTES=10`.
2. Ran multiple scheduler cycles in live mode.
3. Reviewed counters from `/scheduler/status` and checklist.

Verify:
1. Observed:
   - `collection_count=2`
   - `total_events_collected=2`
   - `total_events_posted=2`
   - `total_events_deduped=0`
2. Checklist `dedup_behavior` is `pass`.
3. No false-positive suppression detected.

Next: move to Phase 2 Step 3 source coverage expansion.
