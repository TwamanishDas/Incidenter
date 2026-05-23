# Phase 3: Azure Integration Setup Guide

## Overview
Phase 3 integrates real Azure telemetry sources into the RCA system, replacing simulated data with live infrastructure metrics.

## Prerequisites
- Azure subscription with resources to monitor
- Azure CLI installed: `az login`
- Python 3.9+
- Running AzureRCAPlanner backend

## Installation

### 1. Install Azure SDK dependencies
```bash
pip install -r backend/requirements.txt
```

This installs:
- `azure-monitor-query`: Query Log Analytics and Application Insights
- `azure-identity`: Handle authentication (Managed Identity, Service Principal, Azure CLI)
- `azure-core`: Azure SDK core utilities
- `python-dotenv`: Load environment variables from .env file

### 2. Configure Environment Variables
Copy `.env.example` to `.env` and fill in your Azure resource IDs:

```bash
cp .env.example .env
# Edit .env with your Azure resource IDs
```

### 3. Authentication Setup

Choose one of three methods:

#### Option A: Azure CLI (Local Development - Easiest)
```bash
az login
# App will automatically use your CLI credentials
```

#### Option B: Service Principal (Development/CI)
```bash
# Create service principal
az ad sp create-for-rbac --name myapp --role Reader

# Copy output values into .env
AZURE_TENANT_ID=<your-tenant-id>
AZURE_CLIENT_ID=<your-client-id>
AZURE_CLIENT_SECRET=<your-client-secret>
AZURE_SUBSCRIPTION_ID=<your-subscription-id>
```

#### Option C: Managed Identity (Production in Azure)
1. Deploy AzureRCAPlanner to Azure (App Service, Container Apps, AKS)
2. Enable system-assigned managed identity in Azure Portal
3. Grant RBAC permissions:
   ```bash
   az role assignment create --assignee-object-id <object-id> \
     --role "Monitoring Reader"
   ```
4. No .env configuration needed - identity is automatic

## Configuration

### Finding Your Azure Resource IDs

#### Log Analytics Workspace ID
```bash
# Find all workspaces
az monitor log-analytics workspace list -o table

# Get specific workspace ID
az monitor log-analytics workspace list \
  --resource-group <your-rg> \
  --query "[0].id" -o tsv
```
Set in `.env`: `LOG_ANALYTICS_WORKSPACE_ID=<workspace-id>`

#### Application Insights Resource ID
```bash
# Find all App Insights resources
az monitor app-insights component list -o table

# Get specific resource ID (preferred)
az monitor app-insights component show \
  --app <app-name> \
  --resource-group <your-rg> \
  --query "id" -o tsv
```
Set in `.env`: `APP_INSIGHTS_RESOURCE_ID=<resource-id>`

#### Azure SQL Database Resource ID
```bash
# Get SQL database resource ID
az sql db list \
  --server <server-name> \
  --resource-group <your-rg> \
  --query "[0].id" -o tsv
```
Set in `.env`: `MONITOR_RESOURCE_IDS=<database-id>`

#### Virtual Machine Resource ID
```bash
# Get VM resource ID
az vm list \
  --resource-group <your-rg> \
  --query "[0].id" -o tsv
```

### Collection Interval
Edit `.env` to set how often the scheduler polls for telemetry:
```
COLLECTION_INTERVAL=30  # seconds
LOOKBACK_MINUTES=5      # query window
LOOKBACK_OVERLAP_SECONDS=30
INGESTION_DELAY_SECONDS=60
DEDUP_WINDOW_MINUTES=10
# Optional region hints for monitor metrics enrichment
RESOURCE_REGION_OVERRIDES_JSON={"<resource-id>":"eastus"}
```

## Running the Integrated System

### Start the Backend
```bash
uvicorn backend.app:app --reload --port 8000
```

The scheduler will automatically:
1. Start on app startup
2. Initialize all collectors (Log Analytics, App Insights, Network Watcher, Monitor Metrics, Activity/Health)
3. Begin polling Azure every 30 seconds (configurable)
4. POST collected telemetry to `/telemetry` endpoint
5. Trigger RCA incident detection automatically

### Monitor Collection Activity

Check scheduler status:
```bash
curl http://localhost:8000/scheduler/status
```

Check ingestion checklist (recommended daily sanity check):
```bash
curl http://localhost:8000/ingestion/checklist
```

Checklist semantics:
- `overall_status=pass`: ingestion healthy
- `overall_status=warn`: ingestion running but needs attention
- `overall_status=fail`: ingestion is not ready/reliable

Response example:
```json
{
  "is_running": true,
  "interval_seconds": 30,
  "collection_count": 15,
  "total_events_collected": 47,
  "last_collection_time": "2026-05-21T14:30:45.123456",
  "collectors": [
    {
      "name": "LogAnalyticsCollector",
      "source": "application",
      "events_collected": 12,
      "last_error": null,
      "status": "healthy"
    },
    ...
  ]
}
```

### View Real Incidents from Azure

Once telemetry is collected, view incidents:
```bash
# List all incidents (including Azure-sourced ones)
curl http://localhost:8000/incidents

# View specific incident
curl http://localhost:8000/incidents/{incident-id}
```

## Troubleshooting

### "Collector initialization failed"
**Cause**: Credentials not configured or invalid  
**Fix**: 
1. Verify Azure CLI is logged in: `az account show`
2. Check .env file is in project root: `.env`
3. Verify environment variables: `echo $LOG_ANALYTICS_WORKSPACE_ID`

### "No events collected"
**Cause**: No telemetry in specified time window  
**Fix**:
1. Ensure resources are actively generating metrics
2. Check that LOOKBACK_MINUTES is set appropriately
3. Validate workspace has diagnostic settings for Activity/Health/WAF logs
4. Verify resource IDs are correct: `az monitor log-analytics workspace show --ids <workspace-id>`

### "Query failed: Insufficient permissions"
**Cause**: Service principal/Managed Identity lacks required RBAC roles  
**Fix**:
```bash
# Grant required roles
az role assignment create \
  --assignee <service-principal-id> \
  --role "Monitoring Reader"

az role assignment create \
  --assignee <service-principal-id> \
  --role "Log Analytics Reader"
```

### "KQL Query failed"
**Cause**: Invalid KQL syntax or table doesn't exist  
**Fix**:
1. Test KQL query in Azure Portal > Log Analytics > Query Explorer
2. Verify telemetry is being generated in your resources
3. Check collector logs for specific error message

## Next Steps

1. **Validate Collection**: Run test scenarios in your infrastructure and verify incidents are detected
2. **Tune Thresholds**: Adjust processor.py thresholds based on your infrastructure baselines
3. **Phase 4**: Migrate in-memory store to Cosmos DB or Azure SQL for production
4. **Phase 5**: Add forecasting and anomaly detection
5. **Phase 6**: Build dashboard for incident visualization

## API Endpoints

### Health Check
```bash
curl http://localhost:8000/health
```

### Scheduler Status
```bash
curl http://localhost:8000/scheduler/status
```

### Ingestion Checklist
```bash
curl http://localhost:8000/ingestion/checklist
```

### Step 6 Acceptance Run
```bash
.\.venv\Scripts\python.exe backend\scripts\run_step6_acceptance.py
```

Outputs:
- JSON report: `artifacts/step6_acceptance_latest.json`
- Exit code `0` on pass, `1` on fail

### List Incidents
```bash
curl http://localhost:8000/incidents
```

### Forecast
```bash
curl http://localhost:8000/forecast
```

### Manual Telemetry (for testing)
```bash
curl -X POST http://localhost:8000/telemetry \
  -H "Content-Type: application/json" \
  -d '{
    "source": "application",
    "origin": "log_analytics",
    "payload": {
      "application_name": "test-app",
      "request_rate_per_min": 100,
      "error_rate_pct": 5,
      "avg_response_ms": 500,
      "p95_response_ms": 1000,
      "status_5xx_count": 5
    }
  }'
```

## Architecture Summary

```
┌─────────────────────────────────┐
│  Azure Data Sources             │
│  • Log Analytics                │
│  • App Insights                 │
│  • Network Watcher              │
│  • Monitor Metrics              │
└────────────┬────────────────────┘
             │ (every 30 seconds)
             ↓
┌─────────────────────────────────┐
│  TelemetryScheduler             │
│  • Runs all collectors          │
│  • Aggregates events            │
└────────────┬────────────────────┘
             │ POST /telemetry
             ↓
┌─────────────────────────────────┐
│  FastAPI RCA Engine             │
│  • Validates telemetry          │
│  • Analyzes for incidents       │
│  • Stores in memory/DB          │
│  • Returns incidents via API    │
└─────────────────────────────────┘
```
