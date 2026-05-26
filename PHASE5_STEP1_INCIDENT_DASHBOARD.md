# Phase 5 Step 1 Incident Dashboard

Working: Phase 5 | Step 1.1 | Version v0.5.0 (execution)

Purpose: deliver the first user-facing dashboard view for active incidents using the stabilized Phase 4 RCA output contract.

## Step 1.1 - Active incident list

Goal:
1. Provide a dashboard endpoint that returns active incident cards.
2. Ensure cards include RCA and evidence summary fields needed by UI.

Action:
1. Added dashboard response model:
   - `ActiveIncidentCard` in `backend/models.py`
2. Added endpoint:
   - `GET /dashboard/incidents/active` in `backend/app.py`
3. Added tests:
   - `backend/tests/test_dashboard_active_incidents.py`
4. Added validation runner:
   - `backend/scripts/run_phase5_step1_active_dashboard.py`
5. Captured artifact:
   - `artifacts/phase5_step1_active_incidents_latest.json`

Verify:
1. Unit tests:
   - `.\.venv\Scripts\python.exe -m unittest discover -s backend\tests -v`
2. Step 1.1 runner:
   - `.\.venv\Scripts\python.exe backend\scripts\run_phase5_step1_active_dashboard.py`
   - Expected result: `pass`

Next:
1. Step 1.2: RCA summary panel payload (severity breakdown + top root causes).
2. Step 1.3: trend/forecast payload for chart layer.
