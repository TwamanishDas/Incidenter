# Pilot RCA MVP Plan

## 0. Execution Tracking (Phase / Step / Sub-step)

Use `MASTER_PHASE_STEP_TRACKER.md` as the execution source of truth for:
- phase sequencing,
- step-level progress,
- sub-step completion status,
- version labels (`v0.1.0` to `v0.6.0`).

Current active execution line:
- `Working: Phase 2 | Step 1 | Version v0.2.0 (planning)`

Documentation hierarchy for architecture and scope:
1. High-level architecture:
   - `HIGH_LEVEL_ARCHITECTURE.md`
2. Telemetry catalog:
   - `TELEMETRY_CATALOG.md`
3. Low-level architecture set:
   - `architecture/low-level/`
4. MVP scope and action flow:
   - `MVP_SCOPE.md`
   - `MVP_PHASE_ACTION_PLAN.md`
5. Production-ready scope:
   - `PRODUCTION_READY_SCOPE.md`

## 1. Selected pilot scope

Start with a focused pilot that delivers incident flagging, forecasting, and root cause analysis for:
- **Network-level incidents** affecting connectivity and packet flow
- **Application-level incidents** affecting frontend/API request success and latency
- **Database-level incidents** for Azure SQL connectivity and performance

This scope is intentionally narrow to build a working Azure-native MVP quickly.

## 2. Why this pilot scope

- Network and application failures are the most common operational pain points in Azure deployments.
- Azure provides strong telemetry for these layers through Network Watcher, Application Insights, and Log Analytics.
- A first MVP can demonstrate the end-to-end pipeline and RCA logic before expanding to OS, middleware, or architecture-level analysis.

## 3. Architecture diagram (logical)

```
  Users / Clients
        |
        v
  Azure Front Door / Application Gateway WAF
        |
        v
  Azure App Service / AKS API Layer  <->  Azure SQL Database
        |                               |
        |                               v
        |                        Diagnostics
        |                               |
        +-------------------------------+
                        |
                        v
                 Azure Monitor
             /      |       \ 
            /       |        \
   App Insights   Log Analytics   Network Watcher
            \       |        /
             \      |       /
              v     v      v
            Observation Lake / ADX
                     |
            Processing & Correlation
         (Azure Functions / Stream Analytics)
                     |
                     v
                 RCA Engine
           (dependency map + rule-based)
                     |
          +----------+-----------+
          |                      |
          v                      v
   Dashboard / Investigator   Alerts + Notifications
   (React / Power BI)         (Teams / Email / PagerDuty)
```

## 4. Core components

1. **Telemetry / ingestion**
   - Azure Monitor metrics and logs
   - Application Insights request/exceptions/traces
   - Network Watcher NSG flow logs and connectivity checks
   - Azure SQL diagnostic logs and query performance
   - Azure Activity Log for configuration/changes

2. **Central storage**
   - Log Analytics workspace
   - Azure Data Explorer (optional for fast query)
   - Azure Storage Gen2 for archived telemetry

3. **Processing & analysis**
   - Azure Functions for enrichment and scoring
   - Kusto queries for detection, anomaly detection, and RCA evidence
   - Dependency model stored in JSON/graph store

4. **RCA engine**
   - Start rule-based:
     - `High 5xx rate + SQL connection timeouts -> likely DB/app dependency`
     - `NSG deny count + failed TCP handshake -> likely network access`
     - `WAF blocked requests + backend 502 -> likely ingress layer`
   - Use evidence scoring across layers
   - Output: incident classification, probable root cause, top impacted component

5. **Presentation / ops console**
   - Simple dashboard, incident timeline, RCA summary
   - Drill-down links to App Insights, Log Analytics queries, and network flow details

6. **Alerting / automation**
   - Azure Monitor alerts for the first detected incident types
   - Teams or email notifications with RCA summary
   - Optionally store incidents in Cosmos DB for history and forecasting

## 5. Data flow for the MVP

1. User traffic arrives through Front Door/App Gateway.
2. Frontend/API telemetry is collected by Application Insights.
3. Network diagnostics are collected by Network Watcher and NSG flow logs.
4. Azure SQL diagnostics are forwarded to Log Analytics.
5. Ingested telemetry is normalized into a shared incident schema.
6. Processing engine detects anomalies and correlates events.
7. RCA engine matches patterns to a dependency graph and computes likely cause.
8. Dashboard displays incident, impact, root cause, and recommended next step.
9. Alerts are sent to operations channels.

## 6. Detailed MVP deliverables

### Phase 1: Pilot definition and architecture
- Document the minimal Azure topology for pilot.
- Define supported failure types for MVP:
  - Network connectivity (NSG/route/DNS)
  - Application request failures and latency
  - Database connection failure/performance
- Build a dependency model for the pilot components.

### Phase 2: Telemetry collection
- Provision a Log Analytics workspace.
- Connect Application Insights to the App Service/API.
- Enable Network Watcher and NSG flow logs.
- Enable Azure SQL diagnostics to Log Analytics.
- Verify telemetry flows into the workspace.

### Phase 3: Detection and correlation
- Create Kusto queries for:
  - failed request rate
  - request latency spikes
  - SQL connectivity errors
  - NSG deny/packet drop patterns
- Build an Azure Function or Logic App that ingests query results and adds correlation metadata.

### Phase 4: RCA engine
- Implement rule set for pilot scope.
- Build the first engine with evidence scoring:
  - layer signature matching
  - service dependency evaluation
  - historical pattern support for repeated incidents
- Create incident output fields:
  - `incident_type`, `likely_root_cause`, `probability_score`, `affected_component`, `supporting_evidence`

### Phase 5: Dashboard and notifications
- Build a simple React page or Power BI report with:
  - active incidents
  - root cause summary
  - impact view
  - forecast / trend chart
- Configure Azure Monitor alerts and Teams/email notifications.

### Phase 6: Validation and MVP handoff
- Simulate failure scenarios:
  - block SQL port with NSG / degrade SQL performance
  - add high latency or error injection in app
  - introduce network route/DNS issue
- Validate that the pipeline flags incidents and returns the correct RCA classification.

## 7. Recommended Azure services for MVP

- Azure Monitor
- Azure Log Analytics Workspace
- Azure Application Insights
- Azure Network Watcher
- Azure SQL Database
- Azure Front Door or Application Gateway WAF
- Azure Functions
- Azure Container Apps or App Service (pilot compute)
- Azure AD / Managed Identity
- Azure Key Vault

## 8. Security and governance for the pilot

- Use Managed Identity for all Azure Function and ingestion services.
- Restrict access to Log Analytics and App Insights using RBAC.
- Keep all data in transit encrypted.
- Use Private Link for Azure SQL and storage where possible.
- Apply NSGs for the pilot VNet and subnet isolation.
- Configure Azure Policy to enforce logging/diagnostic settings.

## 9. MVP success criteria

- Incident detection is available for the pilot scope.
- The system can classify a failure into network/app/database.
- RCA output is explainable and linked to evidence.
- Alerts are generated and delivered to operations.
- Dashboard gives a clear view of active incidents and impact.

## 10. Next steps

1. Validate the proposed pilot topology with your target Azure architecture.
2. Choose the actual compute stack for the first pilot: App Service + Azure SQL is the fastest.
3. Build the telemetry ingestion and Log Analytics pipeline.
4. Implement the first rule-based RCA engine.
5. Add the incident dashboard and notification workflow.

> This pilot is designed to be a strong foundation: once the network/application/database path works, you can extend the MVP to OS, middleware, and architecture-level RCA in later phases.
