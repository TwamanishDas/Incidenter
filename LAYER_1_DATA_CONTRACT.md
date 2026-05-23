# Layer 1 Data Contract and Ingestion Matrix

## Purpose

This contract defines the normalized telemetry schema, source-to-layer mapping, authentication model, retrieval method, and collection behavior for Layer 1 ingestion in `AzureRCAPlanner`.

---

## Normalized Telemetry Contract

All collectors emit a `TelemetryEvent` with this shape:

```json
{
  "id": "optional-uuid",
  "timestamp": "UTC ISO timestamp",
  "source": "network | application | database",
  "origin": "simulator | log_analytics | app_insights | network_watcher | azure_monitor_metrics | azure_monitor_diagnostics | azure_activity_log | azure_resource_health | azure_service_health | front_door_waf | app_gateway_waf",
  "source_system": "optional source system name",
  "source_category": "optional source category",
  "record_type": "log | metric | event | audit | trace",
  "schema_type": "standard | custom | vendor",
  "collection_channel": "collection channel (API / diagnostics / Event Hub / etc.)",
  "ingestion_timestamp": "UTC ISO timestamp when record was ingested",
  "resource_id": "optional Azure resource ID",
  "subscription_id": "optional subscription id",
  "region": "optional Azure region",
  "environment": "prod | staging | dev",
  "operation_name": "optional operation/metric category",
  "correlation_id": "optional correlation id",
  "fields": [],
  "payload": {},
  "raw": {},
  "parser_version": "required when schema_type=vendor",
  "raw_message": "optional free text"
}
```

## Schema-Type Contract

1. `schema_type=standard`
   - Typed field extraction from known source schema.
2. `schema_type=custom`
   - Persist complete input payload in `raw`.
   - Do not drop unknown fields.
3. `schema_type=vendor`
   - Persist complete input payload in `raw`.
   - `parser_version` is mandatory and must represent vendor parser/firmware mapping.

Reference catalog:
- `TELEMETRY_CATALOG.md`

## Required Correlation Fields

- `resource_id`
- `subscription_id`
- `region`
- `operation_name`
- `correlation_id`

Collectors populate these fields when available from source records.

---

## Authentication Contract

`backend/azure_config.py` uses this credential chain:

1. `ManagedIdentityCredential` (preferred for Azure-hosted runtime)
2. `ClientSecretCredential` using `AZURE_TENANT_ID`, `AZURE_CLIENT_ID`, `AZURE_CLIENT_SECRET`
3. `DefaultAzureCredential` fallback (includes Azure CLI identity for local development)

Note: `AZURE_DISABLE_MANAGED_IDENTITY=true` can be used in local environments to skip Managed Identity probing.
Note: Application Insights ingestion requires `APP_INSIGHTS_RESOURCE_ID` (ARM resource ID). `APP_INSIGHTS_APP_ID` is deprecated and not used for queries.

### Required RBAC

- `Monitoring Reader`
- `Log Analytics Reader`

These roles are required at subscription/resource-group/resource scope depending where monitored resources live.

---

## Ingestion Matrix

| Source | Retrieval API/Method | Origin Enum | Layer Mapping (`source`) | Data Ingested | Default Frequency |
|---|---|---|---|---|---|
| Log Analytics app logs (`AppRequests`/`requests`) | `LogsQueryClient.query_workspace` (KQL summarize) | `log_analytics` | `application` | request counts, failure rate, 5xx, avg/p95 latency | every `COLLECTION_INTERVAL` (default 30s), query window from watermark |
| Azure Monitor Diagnostics (`AzureDiagnostics`) | `LogsQueryClient.query_workspace` (KQL summarize) | `azure_monitor_diagnostics` | inferred by provider/category (`network`/`database`/`application`) | diagnostic error counts, durations, category/provider summaries | every 30s, watermark window |
| Ingress logs (Front Door/App Gateway/WAF via `AzureDiagnostics`) | `LogsQueryClient.query_workspace` (KQL summarize) | `front_door_waf` / `app_gateway_waf` | `network` | request count, blocked requests, avg latency, WAF signal | every 30s, watermark window |
| Application Insights (`requests`/`exceptions`/`dependencies`) | `LogsQueryClient.query_resource` | `app_insights` | `application` + dependency-driven `database` | request/error/latency, exceptions, dependency failures | every 30s, watermark window |
| Network Watcher logs (`AzureNetworkAnalytics_CL`, `NetworkMonitoring_Perf_CL`, `Syslog`) | `LogsQueryClient.query_workspace` | `network_watcher` | `network` | NSG denies, packet loss, latency, TCP retries | every 30s, watermark window |
| Azure Monitor Metrics (SQL + VM + App Service + Azure Firewall + Cosmos DB + Redis) | `MetricsQueryClient.query_resource` | `azure_monitor_metrics` | SQL/Cosmos -> `database`, VM/App Service/Redis -> `application`, Firewall -> `network` | SQL CPU/sessions/workers/deadlocks/waits, VM CPU/memory/network/disk, App Service HTTP + queue + plan metrics, Firewall rule/SNAT/threat metrics, Cosmos RU/request/availability/replication metrics, Redis hit/miss/read/write/load metrics | every 30s, watermark window |
| Activity Log changes (`AzureActivity`) | `LogsQueryClient.query_workspace` (Administrative/Policy/Security) | `azure_activity_log` | inferred by provider/operation | deploy/config/RBAC change events, failed operation counts | every 30s, watermark window |
| Resource Health (`AzureActivity` category `ResourceHealth`) | `LogsQueryClient.query_workspace` | `azure_resource_health` | inferred by provider/operation | resource health status transitions | every 30s, watermark window |
| Service Health (`AzureActivity` category `ServiceHealth`) | `LogsQueryClient.query_workspace` | `azure_service_health` | inferred by provider/operation | platform service health incidents/advisories | every 30s, watermark window |

---

## Retrieval and Frequency Contract

### Scheduler

- Runs continuously in FastAPI startup lifecycle.
- Interval: `COLLECTION_INTERVAL` (default `30` seconds).
- Collectors run in parallel (`asyncio.to_thread` + `gather`).

### Watermark Strategy

Per collector:

- First run window: `now - LOOKBACK_MINUTES` to `now - INGESTION_DELAY_SECONDS`
- Subsequent runs: `watermark - LOOKBACK_OVERLAP_SECONDS` to `now - INGESTION_DELAY_SECONDS`
- Watermark advances to latest emitted event timestamp (or fallback end time)

This prevents gaps while handling ingestion lag.

### Dedup Strategy

Scheduler dedup cache TTL: `DEDUP_WINDOW_MINUTES` (default `10`).

Fingerprint key includes:

- `source`
- `origin`
- `resource_id`
- `subscription_id`
- `region`
- `operation_name`
- `correlation_id`
- rounded timestamp minute
- normalized `payload`

Duplicate events inside TTL are suppressed before posting to `/telemetry`.

---

## Prerequisites for Full Layer 1 Coverage

1. Send diagnostic logs to a Log Analytics workspace for:
   - Activity Log
   - Resource Health
   - Service Health
   - Front Door/App Gateway/WAF logs
   - SQL diagnostics (for wait/event enrichment)
2. Configure:
   - `LOG_ANALYTICS_WORKSPACE_ID`
   - `APP_INSIGHTS_RESOURCE_ID`
   - `MONITOR_RESOURCE_IDS` (SQL DB, VMs, etc.)
   - `RESOURCE_REGION_OVERRIDES_JSON` (optional region hints keyed by resource id)
3. Ensure identity has monitoring/log reader permissions.

---

## Notes

- RCA remains rule-based (`network`, `application`, `database`) and consumes normalized payloads.
- Control-plane and health events are normalized into layer payloads so they can participate in RCA correlation.
- Monitor metrics collector now supports SQL, VM, App Service, Azure Firewall, Cosmos DB, and Redis resource IDs in `MONITOR_RESOURCE_IDS`.
- Custom and vendor schema behaviors are enforced by model validation (`backend/models.py`).
