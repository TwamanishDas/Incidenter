# Step 6 MVP Ingestion Baseline

## Purpose

Freeze the validated Layer 1 MVP ingestion state (sample-blob mode) before moving to release/versioning work.

## Baseline Run

- Date: May 22, 2026
- Command:
  - `.\.venv\Scripts\python.exe backend\scripts\run_step6_acceptance.py`
- Report artifact:
  - `artifacts/step6_acceptance_latest.json`

## Configuration Snapshot

- `INGESTION_MODE=sample_blob`
- `SAMPLE_BLOB_CONTAINER=rca-sample-ingestion`
- `SAMPLE_BLOB_PREFIX=v1`
- `SAMPLE_REPLAY_REBASE_TIMESTAMPS=true`

## Acceptance Outcome

- Result: **PASS**
- Criteria passed: `6/6`
- Scheduler collections: `2`
- Events collected: `10`
- Events posted: `5`
- Events deduped: `0`
- Incidents generated: `2`
- Collectors healthy:
  - `BlobSampleLogAnalyticsCollector`
  - `BlobSampleAppInsightsCollector`
  - `BlobSampleNetworkWatcherCollector`
  - `BlobSampleMonitorMetricsCollector`
  - `BlobSampleActivityHealthCollector`

## Checklist Interpretation

- `/ingestion/checklist` returned overall status `warn` during this baseline run.
- This is acceptable for Step 6 because all acceptance criteria passed.
- Current warning cause is expected in sample replay mode with `SAMPLE_REPLAY_REBASE_TIMESTAMPS=true`, where repeated cycles may not produce dedup hits.

## Freeze Decision

This baseline is approved as the Step 6 MVP ingestion reference.

Any later ingestion changes should be validated by re-running:
- `.\.venv\Scripts\python.exe backend\scripts\run_step6_acceptance.py`

and comparing outcomes against:
- `artifacts/step6_acceptance_latest.json`
- this baseline document.

