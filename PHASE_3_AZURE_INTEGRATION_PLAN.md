# Phase 3: Azure Integration Plan

## Objective
Connect AzureRCAPlanner to real Azure telemetry sources to replace simulated sample data with live infrastructure metrics.

## Data Sources to Integrate

### 1. **Azure Log Analytics**
- **Purpose**: VM logs, application logs, diagnostic logs
- **Telemetry Types**: 
  - Application logs (stdout/stderr, exceptions)
  - System logs (kernel, services)
  - Custom application events
- **Query Tool**: KQL (Kusto Query Language)
- **Mapping**: Application-layer telemetry

### 2. **Application Insights**
- **Purpose**: Application performance monitoring, user interactions, dependencies
- **Telemetry Types**:
  - Request rates and response times
  - Exception rates and stack traces
  - Dependency calls (SQL, HTTP, etc.)
  - Custom metrics
- **Query Tool**: Kusto Analytics queries
- **Mapping**: Application-layer telemetry

### 3. **Azure Network Watcher**
- **Purpose**: Network flow logs, NSG diagnostics, connectivity monitoring
- **Telemetry Types**:
  - NSG rule denials
  - Packet loss and latency
  - Connection timeouts
  - Traffic patterns
- **Query Tool**: REST API + KQL queries on stored logs
- **Mapping**: Network-layer telemetry

### 4. **Azure Monitor (Metrics)**
- **Purpose**: Resource-level metrics
- **Telemetry Types**:
  - CPU, memory, disk usage
  - Network in/out
  - Database connections
  - Query performance
- **Query Tool**: Metrics API
- **Mapping**: Database/Infrastructure-layer telemetry

### 5. **Azure Activity + Health**
- **Purpose**: Control-plane and platform health signals
- **Telemetry Types**:
  - Deployment/configuration changes
  - RBAC and policy-impacting operations
  - Resource Health and Service Health events
- **Query Tool**: KQL queries on `AzureActivity`
- **Mapping**: Layer inferred from provider/operation

### 6. **Custom Agents** (Future)
- **Purpose**: OS-level and middleware telemetry
- **Telemetry Types**: Application-specific metrics, business KPIs
- **Mapping**: Application-layer custom events

---

## Architecture: Data Flow for Phase 3

```
┌─────────────────────────────────────────┐
│  Azure Data Sources                     │
│  • Log Analytics                        │
│  • Application Insights                 │
│  • Network Watcher                      │
│  • Azure Monitor                        │
└─────────────┬───────────────────────────┘
              │
              ↓
┌─────────────────────────────────────────┐
│  collectors/ (NEW)                      │
│  • log_analytics_collector.py           │
│  • appinsights_collector.py             │
│  • network_watcher_collector.py         │
│  • monitor_metrics_collector.py         │
│  • activity_health_collector.py         │
│  • collector_base.py (interface)        │
└─────────────┬───────────────────────────┘
              │ Transforms Azure → TelemetryEvent
              ↓
┌─────────────────────────────────────────┐
│  azure_scheduler/ (NEW)                 │
│  • telemetry_scheduler.py               │
│  └─ Polls collectors every N seconds    │
└─────────────┬───────────────────────────┘
              │
              ↓
┌─────────────────────────────────────────┐
│  Existing Ingestion Pipeline            │
│  • POST /telemetry                      │
│  • models.py (validation)               │
│  • data_store.py (persistence)          │
│  • processors.py (RCA)                  │
└─────────────────────────────────────────┘
```

---

## Implementation Steps

### Step 1: Azure SDK Setup
- Install: `azure-monitor-query`, `azure-identity`, `azure-core`
- Implement authentication (Managed Identity or Service Principal)
- Create config for Azure resource IDs and workspace IDs

### Step 2: Collector Base Class
- Define interface: `collect() → List[TelemetryEvent]`
- Implement error handling and retry logic
- Add logging for debugging

### Step 3: Individual Collectors
1. **Log Analytics Collector**
   - Query application logs and system logs via KQL
   - Parse timestamps, severity, messages
   - Map to ApplicationPayload

2. **Application Insights Collector**
   - Query request metrics, error rates, response times
   - Parse dependency traces
   - Map to ApplicationPayload

3. **Network Watcher Collector**
   - Query NSG flow logs for denied connections
   - Detect packet loss and latency patterns
   - Map to NetworkPayload

4. **Azure Monitor Metrics Collector**
   - Query resource metrics (CPU, memory, connections)
   - Parse time-series data
   - Map to DatabasePayload (for DB metrics) or infrastructure metrics

5. **Activity & Health Collector**
   - Query `AzureActivity` for deploy/config/RBAC change events
   - Query Resource Health + Service Health signals
   - Emit normalized layer telemetry with correlation fields

### Step 4: Scheduler
- Create background task that runs collectors on interval (e.g., every 30 seconds)
- Aggregate results and POST to /telemetry endpoint
- Implement error recovery and circuit breaker logic
- Apply watermark windows and event deduplication to avoid repeat incident triggers

### Step 5: Configuration
- Add environment variables for Azure credentials, workspace IDs, resource IDs
- Create `.env.example` with required keys

---

## Authentication Strategy

### Option A: Managed Identity (Recommended for Production)
- Deploy AzureRCAPlanner to Azure App Service or Container Instance
- Enable system-assigned managed identity
- Grant RBAC permissions: `Monitoring Reader`, `Log Analytics Reader`

### Option B: Service Principal (Development/Testing)
- Create app registration in Entra ID
- Assign RBAC permissions
- Store credentials in `.env` (local development only)

### Option C: Azure CLI (Local Development)
- Use `az login` credentials
- Automatically picks up from Azure CLI cache

---

## Expected Telemetry Format After Integration

```json
// Log Analytics application summary
{
  "source": "application",
  "origin": "log_analytics",
  "timestamp": "2026-05-21T14:23:45Z",
  "resource_id": "/subscriptions/.../resourceGroups/.../providers/Microsoft.Web/sites/customer-api",
  "subscription_id": "xxxx-xxxx",
  "region": "eastus",
  "operation_name": "ApplicationRequestsSummary",
  "correlation_id": "optional-correlation-id",
  "payload": {
    "application_name": "customer-api",
    "request_rate_per_min": 120,
    "error_rate_pct": 2.5,
    "avg_response_ms": 850,
    "p95_response_ms": 1200,
    "status_5xx_count": 3
  }
}

// Network Watcher signal
{
  "source": "network",
  "origin": "network_watcher",
  "timestamp": "2026-05-21T14:24:15Z",
  "operation_name": "NetworkWatcherNSGFlowSummary",
  "payload": {
    "source_ip": "10.0.1.5",
    "destination_ip": "10.0.2.10",
    "nsg_denied_connections": 15,
    "packet_loss": 8.5,
    "avg_latency_ms": 120,
    "tcp_retry_count": 3
  }
}

// Azure Monitor metrics with enriched correlation
{
  "source": "database",
  "origin": "azure_monitor_metrics",
  "timestamp": "2026-05-21T14:24:30Z",
  "resource_id": "/subscriptions/.../resourceGroups/.../providers/Microsoft.Sql/servers/s1/databases/orders-db",
  "subscription_id": "xxxx-xxxx",
  "region": "eastus",
  "operation_name": "AzureMonitorSQLMetricsSummary",
  "correlation_id": "synthetic-or-diagnostics-correlation",
  "payload": {
    "database_name": "orders-db",
    "cpu_percent": 78,
    "timeout_count": 2,
    "deadlock_count": 1,
    "avg_query_duration_ms": 1950
  }
}
```

---

## Success Criteria

- [ ] All 5 collectors implemented and tested
- [ ] Scheduler continuously polls Azure sources without errors
- [ ] RCA engine successfully processes real Azure telemetry
- [ ] Incidents are detected from live infrastructure metrics
- [ ] Dashboard shows real incidents (not just simulated)
- [ ] Error rate and latency thresholds match actual infrastructure health

---

## Timeline Estimate
- **Setup & auth**: 1-2 hours
- **Collectors (5x)**: 2-3 hours each = 10-15 hours
- **Scheduler**: 1-2 hours
- **Testing & validation**: 2-3 hours
- **Total**: ~15 hours

---

## Next Phase
Once Phase 3 is complete, move to Phase 4 (Persistent Storage) to replace in-memory store with Cosmos DB or Azure SQL for production scalability.
