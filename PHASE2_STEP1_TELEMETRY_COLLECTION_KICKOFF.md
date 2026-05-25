# Phase 2 Step 1 Kickoff

Working: Phase 2 | Step 1 | Version v0.2.0 (planning)

Purpose: establish a beginner-friendly, executable path to start live telemetry collection setup for AzureRCAPlanner.

Related runbooks:
1. `PHASE1_EXECUTION_RUNBOOK.md`
2. `PHASE2_STEP2_INGESTION_TUNING.md`
3. `DOCUMENTATION_STRUCTURE.md`

## Execution Snapshot (2026-05-23)

1. Subscription: `1f5ee0d1-cee1-4424-9768-4eac65a0ad83`
2. Tenant: `718a9912-4d8d-4d9d-af9a-abe3dca42cb2`
3. Resource Group: `rg-incidenter-pilot` (`eastus`)
4. Log Analytics workspace: `law-incidenter-pilot` (customerId `4755af10-2632-41ff-9bf0-d780e2d5e680`)
5. Application Insights: `appi-incidenter-pilot` (workspace-based)
6. SQL diagnostics target:
   - Server: `sqlincidenter46744` (`centralindia`)
   - Database: `incidenterdb` (`Basic`)
   - Diagnostic setting: `sql-to-law`
7. Flow telemetry path:
   - Network Watcher: `NetworkWatcher_eastus` (`NetworkWatcherRG`)
   - VNet flow log: `incidenter-vnet-flowlog`
8. Validation:
   - `GET /scheduler/status` -> 200
   - `GET /ingestion/checklist` -> overall_status `pass`

## Step 1 - Confirm local prerequisites

Goal: ensure your machine can run Azure setup commands.

Action:
1. Open PowerShell.
2. Run:

```powershell
az --version
az login
az account show
```

Verify:
1. `az --version` returns installed CLI version.
2. `az account show` returns your expected subscription.

Next: set reusable variables.

## Step 2 - Set variables for this session

Goal: avoid copy/paste mistakes in later commands.

Action: update values, then run:

```powershell
$SUBSCRIPTION_ID = "<your-subscription-id>"
$LOCATION = "eastus"
$RG_NAME = "rg-incidenter-pilot"
$LAW_NAME = "law-incidenter-pilot"
$APPINSIGHTS_NAME = "appi-incidenter-pilot"
$APP_NAME = "<your-app-service-name>"   # optional if app already exists
$SQL_SERVER = "<your-sql-server-name>"  # without database.windows.net
$SQL_DB = "<your-sql-db-name>"

az account set --subscription $SUBSCRIPTION_ID
```

Verify: no error from `az account set`.

Next: create or validate resource group.

## Step 3 - Create Resource Group + Log Analytics Workspace

Goal: provision the central workspace used by collectors.

Action:

```powershell
az group create --name $RG_NAME --location $LOCATION

az monitor log-analytics workspace create `
  --resource-group $RG_NAME `
  --workspace-name $LAW_NAME `
  --location $LOCATION
```

Verify:

```powershell
az monitor log-analytics workspace show `
  --resource-group $RG_NAME `
  --workspace-name $LAW_NAME `
  --query "{id:id,customerId:customerId,location:location}" -o table
```

Next: create or connect Application Insights to the same workspace.

## Step 4 - Create workspace-based Application Insights

Goal: ensure app telemetry is routed into Azure Monitor data plane.

Action:

```powershell
$LAW_ID = az monitor log-analytics workspace show `
  --resource-group $RG_NAME `
  --workspace-name $LAW_NAME `
  --query id -o tsv

az monitor app-insights component create `
  --app $APPINSIGHTS_NAME `
  --location $LOCATION `
  --resource-group $RG_NAME `
  --workspace $LAW_ID
```

Verify:

```powershell
az monitor app-insights component show `
  --app $APPINSIGHTS_NAME `
  --resource-group $RG_NAME `
  --query "{id:id,workspaceResourceId:workspaceResourceId}" -o table
```

Next: enable SQL diagnostics to Log Analytics.

## Step 5 - Enable Azure SQL diagnostic settings

Goal: stream SQL logs/metrics to the workspace for database RCA signals.

Action:

```powershell
$LAW_RESOURCE_ID = az monitor log-analytics workspace show `
  --resource-group $RG_NAME `
  --workspace-name $LAW_NAME `
  --query id -o tsv

$SQL_RESOURCE_ID = "/subscriptions/$SUBSCRIPTION_ID/resourceGroups/$RG_NAME/providers/Microsoft.Sql/servers/$SQL_SERVER/databases/$SQL_DB"

az monitor diagnostic-settings create `
  --name "sql-to-law" `
  --resource $SQL_RESOURCE_ID `
  --workspace $LAW_RESOURCE_ID `
  --metrics '[{"category":"AllMetrics","enabled":true}]' `
  --logs '[{"category":"SQLInsights","enabled":true},{"category":"AutomaticTuning","enabled":true},{"category":"QueryStoreRuntimeStatistics","enabled":true},{"category":"Errors","enabled":true}]'
```

Verify:

```powershell
az monitor diagnostic-settings list --resource $SQL_RESOURCE_ID -o table
```

Next: enable Network Watcher telemetry path.

## Step 6 - Enable VNet flow logs (Network Watcher)

Goal: capture network deny/flow evidence used by network RCA.

Action:

```powershell
$NW_RG = "NetworkWatcherRG"
$NW_NAME = "NetworkWatcher_$LOCATION"
$VNET_NAME = "<your-vnet-name>"
$FLOW_LOG_NAME = "incidenter-vnet-flowlog"
$FLOW_STORAGE = "<your-storage-account-name>"

$VNET_ID = az network vnet show `
  --resource-group $RG_NAME `
  --name $VNET_NAME `
  --query id -o tsv

$FLOW_STORAGE_ID = az storage account show `
  --resource-group $RG_NAME `
  --name $FLOW_STORAGE `
  --query id -o tsv

az network watcher flow-log create `
  --location $LOCATION `
  --resource-group $NW_RG `
  --name $FLOW_LOG_NAME `
  --vnet $VNET_ID `
  --storage-account $FLOW_STORAGE_ID `
  --enabled true `
  --workspace $LAW_RESOURCE_ID `
  --traffic-analytics true
```

Verify:

```powershell
az network watcher flow-log show `
  --location $LOCATION `
  --resource-group $NW_RG `
  --name $FLOW_LOG_NAME `
  --query "{enabled:enabled,workspaceId:flowAnalyticsConfiguration.networkWatcherFlowAnalyticsConfiguration.workspaceId}" -o table
```

Next: bind project `.env` values and run ingestion checks.

## Step 7 - Configure local app for live mode and validate

Goal: connect AzureRCAPlanner to live Azure telemetry.

Action:
1. Update `.env` with values from created resources:
   - `INGESTION_MODE=live`
   - `AZURE_TENANT_ID`
   - `AZURE_SUBSCRIPTION_ID`
   - `AZURE_DISABLE_MANAGED_IDENTITY=true`
   - `LOG_ANALYTICS_WORKSPACE_ID` (customerId from workspace)
   - `APP_INSIGHTS_RESOURCE_ID`
   - `NETWORK_WATCHER_RESOURCE_GROUP`
   - `NETWORK_WATCHER_NAME`
   - `MONITOR_RESOURCE_IDS` (include SQL DB + VM IDs)
   - `RESOURCE_REGION_OVERRIDES_JSON` (for cross-region resources)
2. Authenticate with Azure CLI (device code flow):

```powershell
$env:AZURE_CONFIG_DIR = ".azure_phase2_fresh"
az login --use-device-code --tenant $AZURE_TENANT_ID
az account set --subscription $AZURE_SUBSCRIPTION_ID
```

3. Start backend:

```powershell
$env:AZURE_CONFIG_DIR = ".azure_phase2_fresh"
uvicorn backend.app:app --reload --port 8000
```

4. Run checks:

```powershell
curl http://127.0.0.1:8000/scheduler/status
curl http://127.0.0.1:8000/ingestion/checklist
```

Verify:
1. `/scheduler/status` shows collectors running.
2. `/ingestion/checklist` is `pass` or `warn` (not `fail`) while telemetry starts flowing.

Next: move to Phase 2 Step 2 and tune collection windows after first successful live ingestion cycle.

## Exit Criteria for Phase 2 Step 1

1. Log Analytics workspace exists and is queryable.
2. Application Insights is workspace-based and linked.
3. SQL diagnostics are enabled to workspace.
4. VNet flow logs are enabled with traffic analytics.
5. Local app is running with `INGESTION_MODE=live`.
6. Scheduler and ingestion checklist endpoints are healthy.
