# New Session Handoff (Phase 1)

## Working Context

- Current focus: **Phase 1 (Data Ingestion)**
- Current step status: **Step 6 complete, Step 7 pending**
- Version label currently in use: **`v0.1.0` (pre-tag baseline)**
- Important user preference: always communicate updates as:
  - `Working: Phase <X> | Step <Y> | Version <Z>`

## What Is Completed (Phase 1)

1. Step 1: Sample ingestion data staged in blob container.
2. Step 2: Ingestion mode switch implemented:
   - `INGESTION_MODE=sample_blob`
   - `INGESTION_MODE=live`
3. Step 3: End-to-end sample replay validation completed.
4. Step 4: Hardening completed:
   - replay diagnostics in sample collector
   - scheduler switch-behavior tests
5. Step 5: Ingestion checklist endpoint completed:
   - `GET /ingestion/checklist`
6. Step 6: Acceptance + baseline freeze completed:
   - acceptance runner script
   - baseline document
   - acceptance report artifact

## What Is Pending

1. Step 7: Create release/version artifacts:
   - checkpoint tag (`cp/p1-s7`)
   - phase tag (`v0.1.0`)
   - release notes file

## Key Files (Most Important)

- Data contract:
  - `LAYER_1_DATA_CONTRACT.md`
- Setup/runbook:
  - `SETUP_PHASE_3.md`
- Main session state:
  - `SESSION_SUMMARY.md`
- Baseline freeze:
  - `STEP6_MVP_INGESTION_BASELINE.md`
- Collaboration preferences:
  - `COLLABORATION_AWARENESS.md`

## Backend Implementation Pointers

- App entry + endpoints:
  - `backend/app.py`
- Azure config + mode:
  - `backend/azure_config.py`
- Scheduler:
  - `backend/azure_scheduler/telemetry_scheduler.py`
- Sample replay collector:
  - `backend/replay/blob_sample_collector.py`
- Ingestion checklist logic:
  - `backend/ingestion_health.py`
- Step 6 acceptance logic:
  - `backend/acceptance.py`
- Step 6 acceptance runner:
  - `backend/scripts/run_step6_acceptance.py`

## Validation Artifacts

- Latest Step 6 acceptance JSON:
  - `artifacts/step6_acceptance_latest.json`
- Unit tests currently passing:
  - `backend/tests/test_blob_sample_collector.py`
  - `backend/tests/test_scheduler_switch_behavior.py`
  - `backend/tests/test_ingestion_health.py`
  - `backend/tests/test_acceptance.py`

## Useful Commands

```powershell
# Run backend
uvicorn backend.app:app --reload --port 8000

# Scheduler status
curl http://127.0.0.1:8000/scheduler/status

# Ingestion checklist
curl http://127.0.0.1:8000/ingestion/checklist

# Step 6 acceptance run
.\.venv\Scripts\python.exe backend\scripts\run_step6_acceptance.py

# Unit tests
.\.venv\Scripts\python.exe -m unittest discover -s backend/tests -p "test_*.py" -v
```

## Known Operational Issue

- Intermittent stream disconnections happened during long web lookups.
- Recommended behavior in next session:
  1. Do one query batch at a time.
  2. Return findings in short chunks.
  3. Avoid overlapping follow-up prompts while a fetch is active.

## Azure Metrics Research Status

- User requested Azure Monitor metric-type research from Microsoft docs.
- Work was interrupted by stream disconnections before final consolidated output.
- This is the **next functional research task** to continue in new session.

## Ready-to-Paste New Session Prompt

Use this at the start of a new session:

```text
Working: Phase 1 | Step Azure metrics discovery | Version v0.1.0 (pre-tag)

Read these files first:
1) NEW_SESSION_HANDOFF_PHASE1.md
2) SESSION_SUMMARY.md
3) LAYER_1_DATA_CONTRACT.md
4) STEP6_MVP_INGESTION_BASELINE.md

Then continue from pending work:
- Finish Azure Monitor metrics research from Microsoft docs.
- Provide ingestion-ready metric recommendations by source (SQL, VM, App Service, Front Door/App Gateway/WAF, etc.).
- Use short chunked updates to avoid stream disconnection.
```

