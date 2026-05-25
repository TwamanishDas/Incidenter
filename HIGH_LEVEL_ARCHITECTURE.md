# High Level Architecture

Working: Phase 3 | Step 2 | Version v0.3.0 (next)

Purpose: define the top-level system architecture and route readers to low-level architecture and implementation tracking.

## System Layers

1. Traffic and edge: Front Door / Application Gateway WAF.
2. Workload layer: App Service or AKS API layer.
3. Data layer: Azure SQL Database.
4. Observability layer: Azure Monitor, Application Insights, Log Analytics, Network Watcher.
5. Ingestion and normalization layer: collector + scheduler pipeline in `backend/collectors` and `backend/azure_scheduler`.
6. Detection and correlation layer: query/aggregation/correlation logic.
7. RCA and incident layer: rule engine and incident output model.
8. Experience and operations layer: dashboard, alerts, notifications, runbooks.

## High-Level Logical Flow

```text
Users -> Edge (Front Door/App Gateway) -> App/API -> Azure SQL
   -> Telemetry Sources (App Insights, LA, Network Watcher, Metrics, Activity)
   -> Ingestion + Normalization
   -> Detection + Correlation
   -> RCA Engine
   -> Incident Store + Dashboard + Alerts
```

## Low-Level Architecture Breakdown

1. Ingestion and observability internals:
   - `architecture/low-level/LLA_INGESTION_AND_OBSERVABILITY.md`
2. Detection and correlation internals:
   - `architecture/low-level/LLA_DETECTION_AND_CORRELATION.md`
3. RCA engine and incident model internals:
   - `architecture/low-level/LLA_RCA_ENGINE_AND_INCIDENT_MODEL.md`
4. Dashboard and alerting internals:
   - `architecture/low-level/LLA_DASHBOARD_AND_ALERTING.md`
5. Platform security and operations internals:
   - `architecture/low-level/LLA_PLATFORM_SECURITY_AND_OPERATIONS.md`

## Implementation Scope Linkage

1. Master execution tracker:
   - `MASTER_PHASE_STEP_TRACKER.md`
2. Telemetry source catalog:
   - `TELEMETRY_CATALOG.md`
3. MVP scope and phase tracking:
   - `MVP_SCOPE.md`
   - `MVP_PHASE_ACTION_PLAN.md`
4. Production-ready scope and phase tracking:
   - `PRODUCTION_READY_SCOPE.md`

## Relationship Rules

1. Any new architecture component must be added in this file first.
2. Every component in this file must map to one low-level architecture file.
3. Every low-level architecture file must include:
   - phase/step/sub-step mapping,
   - plan-of-action,
   - tracker references.
