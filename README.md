# AzureRCAPlanner MVP

## Overview

This project is a pilot MVP for Azure incident flagging, forecasting, and root cause analysis.
The current implementation focuses on:
- Network-level incident detection
- Application-level incident detection
- Database-level incident detection
- Rule-based RCA and evidence scoring

## Current MVP scope

- A Python FastAPI backend that ingests telemetry events
- A lightweight RCA engine with initial classification rules
- In-memory incident store for proof-of-concept
- Sample telemetry payloads for development and simulation

## Architecture and Tracking Documents

1. Execution tracker:
   - `MASTER_PHASE_STEP_TRACKER.md`
2. High-level architecture:
   - `HIGH_LEVEL_ARCHITECTURE.md`
3. Low-level architecture:
   - `architecture/low-level/`
4. MVP scope and action plan:
   - `MVP_SCOPE.md`
   - `MVP_PHASE_ACTION_PLAN.md`
5. Production-ready scope:
   - `PRODUCTION_READY_SCOPE.md`

## Folder structure

- `backend/`
  - `app.py` - FastAPI app with ingestion and incident endpoints
  - `models.py` - telemetry and incident schemas
  - `processors.py` - rule-based RCA engine
  - `data_store.py` - in-memory storage and persistence helpers
  - `telemetry_samples.py` - sample event payloads
  - `requirements.txt` - Python dependencies
  - `azure_config.py` - Azure authentication and configuration
  - `collectors/` - Azure telemetry collectors (Phase 3)
    - `collector_base.py` - base class for all collectors
    - `log_analytics_collector.py` - queries Log Analytics workspace
    - `appinsights_collector.py` - queries Application Insights
    - `network_watcher_collector.py` - queries NSG flow logs
    - `monitor_metrics_collector.py` - queries Azure Monitor metrics
  - `azure_scheduler/` - telemetry collection scheduler (Phase 3)
    - `telemetry_scheduler.py` - orchestrates periodic collection

## Getting started (MVP - Simulated Data)

1. Create and activate a Python virtual environment:
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```
2. Install dependencies:
   ```powershell
   pip install -r backend/requirements.txt
   ```
3. Start the backend:
   ```powershell
   uvicorn backend.app:app --reload --port 8000
   ```
4. Use the endpoints:
   - `GET http://127.0.0.1:8000/health`
   - `POST http://127.0.0.1:8000/telemetry` to submit telemetry
   - `GET http://127.0.0.1:8000/incidents` to fetch detected incidents
   - `POST http://127.0.0.1:8000/simulate` to generate sample incident scenarios

## Phase 3: Azure Integration (Real Telemetry)

To connect to real Azure telemetry sources instead of simulated data:

1. See [SETUP_PHASE_3.md](./SETUP_PHASE_3.md) for detailed configuration
2. See [LAYER_1_DATA_CONTRACT.md](./LAYER_1_DATA_CONTRACT.md) for normalized schema + ingestion matrix
3. Configure `.env` with your Azure resource IDs
4. Scheduler automatically collects from: Log Analytics, Application Insights, Network Watcher, Azure Monitor
5. New endpoint: `GET http://127.0.0.1:8000/scheduler/status` to monitor collection
6. New endpoint: `GET http://127.0.0.1:8000/ingestion/checklist` for pass/warn/fail ingestion readiness summary
7. Step 6 acceptance runner: `.\.venv\Scripts\python.exe backend\scripts\run_step6_acceptance.py`

## Implementation Roadmap

Roadmap status is maintained in:
- `MASTER_PHASE_STEP_TRACKER.md`

Current active line:
- `Working: Phase 2 | Step 1 | Version v0.2.0 (planning)`
