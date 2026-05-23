# Phase 2 Step 1 Kickoff

Working: Phase 2 | Step 1 | Version v0.2.0 (planning)

Purpose: establish a beginner-friendly, executable path to start live telemetry collection setup for AzureRCAPlanner.

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

## Step 6 - Enable NSG flow logs (Network Watcher)

Goal: capture network deny/flow evidence used by network RCA.

Action:

```powershell
$NW_RG = "NetworkWatcherRG"
$NW_NAME = "NetworkWatcher_$LOCATION"
$NSG_NAME = "<your-nsg-name>"

$NSG_ID = az network nsg show `
  --resource-group $RG_NAME `
  --name $NSG_NAME `
  --query id -o tsv

az network watcher flow-log create `
  --location $LOCATION `
  --resource-group $NW_RG `
  --name "nsg-flowlog-$NSG_NAME" `
  --nsg $NSG_ID `
  --enabled true `
  --workspace $LAW_RESOURCE_ID `
  --traffic-analytics true
```

Verify:

```powershell
az network watcher flow-log show `
  --location $LOCATION `
  --resource-group $NW_RG `
  --name "nsg-flowlog-$NSG_NAME" `
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
   - `AZURE_CLIENT_ID`
   - `AZURE_CLIENT_SECRET`
   - `LOG_ANALYTICS_WORKSPACE_ID` (customerId from workspace)
   - `APP_INSIGHTS_RESOURCE_ID`
   - `NETWORK_WATCHER_RESOURCE_GROUP`
   - `NETWORK_WATCHER_NAME`
   - `MONITOR_RESOURCE_IDS` (include SQL DB + VM IDs)
2. Start backend:

```powershell
uvicorn backend.app:app --reload --port 8000
```

3. Run checks:

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
4. NSG flow logs are enabled with traffic analytics.
5. Local app is running with `INGESTION_MODE=live`.
6. Scheduler and ingestion checklist endpoints are healthy.
