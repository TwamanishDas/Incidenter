# Phase 3 Step 1 KQL Signal Packs

Working: Phase 3 | Step 1 | Version v0.3.0 (execution)

Purpose: implement and validate reusable KQL signal packs for Phase 3 detection inputs.

## Step 1.1 - Failed request rate query

Goal: detect failed request spikes by app/operation in short windows.

Action:
1. Added query pack file:
   - `kql/phase3_step1/01_failed_request_rate.kql`
2. Query uses `AppRequests` with schema-safe `column_ifexists` mappings.
3. Signal condition:
   - `TotalRequests >= 20`
   - `FailureRatePct >= 2.0`

Verify:
1. Query executed via validation runner without syntax/semantic failure.
2. Included in artifact:
   - `artifacts/phase3_step1_signal_pack_latest.json`

Next: implement latency spike pack (Step 1.2).

## Step 1.2 - Latency spike query

Goal: detect p95/p99 latency regressions by app/operation.

Action:
1. Added query pack file:
   - `kql/phase3_step1/02_latency_spike.kql`
2. Query uses `AppRequests` and computes:
   - `AvgLatencyMs`, `P95LatencyMs`, `P99LatencyMs`, `MaxLatencyMs`
3. Signal condition:
   - `Requests >= 20`
   - `P95LatencyMs >= 1000` or `P99LatencyMs >= 2000`

Verify:
1. Query executed successfully in live workspace validation.
2. Included in artifact with `status=pass`.

Next: implement SQL connectivity pack (Step 1.3).

## Step 1.3 - SQL connectivity error query

Goal: detect SQL connectivity/timeouts/deadlocks from diagnostics.

Action:
1. Added query pack file:
   - `kql/phase3_step1/03_sql_connectivity_errors.kql`
2. Query sources:
   - `AzureDiagnostics` (`ResourceProvider=MICROSOFT.SQL`)
3. Signal metrics:
   - `ConnectivityErrors`
   - `TimeoutCount`
   - `DeadlockCount`
   - `ConnectivityErrorRatePct`

Verify:
1. Query executed successfully in live workspace validation.
2. Included in artifact with `status=pass`.

Next: implement network deny/drop pack (Step 1.4).

## Step 1.4 - NSG deny and packet-drop query

Goal: detect network policy deny/drop-like evidence from network diagnostics.

Action:
1. Added query pack file:
   - `kql/phase3_step1/04_nsg_deny_packet_drop.kql`
2. Query sources:
   - `AzureDiagnostics` (`ResourceProvider=MICROSOFT.NETWORK`)
3. Signal metrics:
   - `DeniedEvents`
   - `DropLikeEvents`
   - `DenyRatePct`

Verify:
1. Query executed successfully in live workspace validation.
2. Included in artifact with `status=pass`.

Next: run full query pack validation and capture evidence.

## Step 1 Validation Artifact

Goal: validate all 4 signal packs together in live mode.

Action:
1. Added validation runner:
   - `backend/scripts/run_phase3_step1_signal_pack.py`
2. Executed:
   - `.\.venv\Scripts\python.exe backend\scripts\run_phase3_step1_signal_pack.py`
3. Artifact generated:
   - `artifacts/phase3_step1_signal_pack_latest.json`

Verify:
1. Result: `pass`
2. Summary:
   - `queries_total=4`
   - `queries_passed=4`
   - `queries_warned=0`
   - `queries_failed=0`

Next: proceed to Phase 3 Step 2 (Correlation Enricher).
