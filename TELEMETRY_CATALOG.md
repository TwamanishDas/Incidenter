# Telemetry Ingestion Catalog

Working: Phase 2 | Step 1 | Version v0.2.0 (planning)

Purpose: reference catalog for ingestion engine schema handling and source metrics onboarding.

## Schema Column Legend

| Value | Meaning | Ingestion Engine Handling |
|---|---|---|
| `standard` | Microsoft / RFC / project-documented, stable field names | Fixed mapper and typed parser |
| `custom` | Application-defined or session-defined; fields vary | Dynamic path; persist full `raw` payload |
| `vendor` | Vendor-documented but format varies by firmware/version | Versioned parser; stamp `parser_version` |

## Ingestion Rules

1. `schema_type == "custom"`:
   - persist full raw payload in `raw`,
   - do not drop unknown keys.
2. `schema_type == "vendor"`:
   - require `parser_version`,
   - persist full raw payload in `raw`.
3. `schema_type == "standard"`:
   - parse known keys to normalized payload fields.

## Canonical Record Shape

```python
from dataclasses import dataclass, field
from typing import Literal, Optional

@dataclass
class TelemetryRecord:
    source_system: str
    source_category: str
    record_type: Literal["log", "metric", "event", "audit", "trace"]
    schema_type: Literal["standard", "custom", "vendor"]
    collection_channel: str
    ingestion_timestamp: str
    name: str
    fields: list[str]
    raw: dict = field(default_factory=dict)
    resource_id: Optional[str] = None
    subscription_id: Optional[str] = None
    region: Optional[str] = None
    environment: str = "prod"
    parser_version: Optional[str] = None
```

## Custom and Vendor Entries (Flexible Ingestion Path)

| # | Source System | Name | Schema | Why |
|---|---|---|---|---|
| 1 | Azure Monitor Agent | Custom log ingestion (DCR) | Custom | DCR schema is app-defined |
| 2 | Azure App Service | Application logs | Custom | Framework-specific fields vary |
| 3 | Azure Functions | App Insights traces (`customDimensions`) | Custom | Per-function custom keys |
| 4 | SQL Server | Extended Events (XE) | Custom | Session DDL defines schema |
| 5 | MongoDB | Profiler (`db.system.profile`) | Custom | Shape varies by op type |
| 6 | Network Watcher | Packet Capture (pcap) | Custom | Decoder-dependent fields |
| 7 | Kubernetes / AKS | Container stdout/stderr | Custom | Free-form app output |
| 8 | Application Insights | Trace telemetry (custom logs) | Custom | message + dimensions are app-defined |
| 9 | Application Insights | Custom metrics | Custom | metric names/dimensions app-defined |
| 10 | App/Middleware | Log4j/Logback/SLF4J app logs | Custom | MDC/appender fields vary |
| 11 | Palo Alto (PAN-OS) | Traffic log | Vendor | Field order varies by firmware |
| 12 | Palo Alto (PAN-OS) | Threat log | Vendor | Enum values vary by content version |
| 13 | Palo Alto (PAN-OS) | System log | Vendor | `eventid` is firmware-specific |
| 14 | Fortinet (FortiGate) | Traffic/UTM log | Vendor | Field set varies by FortiOS and UTM features |
| 15 | Java / JVM | GC logs | Vendor | Format varies by JVM vendor + GC algorithm |

## Source Catalog (Current Ingestion Coverage)

The following source metrics are now mapped in `MonitorMetricsCollector`:

### Azure SQL / SQL Database

- `cpu_percent`, `sqlserver_process_core_percent`
- `sessions_percent`, `sessions_count`
- `workers_percent`
- `deadlock`
- SQL wait enrichment from diagnostics (`AzureDiagnostics`)

### Azure VM

- `Percentage CPU`
- `Available Memory Bytes`
- `Network In Total`, `Network Out Total`
- `Disk Read Bytes`, `Disk Write Bytes`
- `OS Disk Queue Depth`

### Azure App Service

- `Http2xx`, `Http3xx`, `Http4xx`, `Http5xx`
- `AverageResponseTime`
- `RequestsInApplicationQueue`, `HttpQueueLength`
- `CpuPercentage`, `MemoryPercentage`

### Azure Firewall

- `ApplicationRuleHit`
- `NetworkRuleHit`
- `DataProcessed`
- `SNATPortUtilization`
- `ThreatIntelAlerts`

### Azure Cosmos DB

- `TotalRequestUnits`, `MongoRequestCharge`
- `TotalRequests`
- `Availability`, `AvailabilityPercent`
- `ReplicationLatency`, `ReplicationLatencyMs`

### Azure Cache for Redis

- `CacheHits`, `CacheMisses`
- `CacheRead`, `CacheWrite`
- `ConnectedClients`
- `UsedMemoryPercentage`
- `ServerLoad`

## Extended Source Catalog (Planned Parser/Collector Backlog)

1. Azure Platform:
   - Activity Log (administrative, policy, service/resource health, autoscale)
   - Azure Entra ID logs (sign-in, audit, risk)
   - Key Vault and Storage diagnostics
2. Windows:
   - System/Security Event IDs, perf counters, IIS, Defender
3. Linux:
   - syslog facilities, auditd, `/proc` metrics, journal
4. Databases:
   - SQL DMVs, PostgreSQL stats/logs, MySQL slow/error/general logs
5. NoSQL/Cache:
   - Mongo profiler and change streams, Redis slowlog and keyspace events
6. Firewall/Network:
   - NSG flow logs v2, WAF logs, DDoS metrics, VPN/ExpressRoute metrics
7. AKS/Kubernetes:
   - control plane logs, node/pod metrics, kube events, Prometheus exporters
8. Application/Middleware:
   - App Insights traces/dependencies/exceptions, Nginx/Apache, JVM logs/JMX, Service Bus/Event Hub/Kafka

## Implementation Linkage

1. Data contract:
   - `LAYER_1_DATA_CONTRACT.md`
2. Ingestion model:
   - `backend/models.py`
3. Metrics collector:
   - `backend/collectors/monitor_metrics_collector.py`
4. Tracker:
   - `MASTER_PHASE_STEP_TRACKER.md`
