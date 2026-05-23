"""
Azure collector configuration and authentication setup.
Handles credentials for Azure SDK clients.
"""

import json
import os
from azure.identity import ClientSecretCredential, DefaultAzureCredential
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class AzureConfig:
    """Configuration for Azure data sources"""
    
    # Authentication
    TENANT_ID = os.getenv("AZURE_TENANT_ID")
    SUBSCRIPTION_ID = os.getenv("AZURE_SUBSCRIPTION_ID")
    
    # Log Analytics
    LOG_ANALYTICS_WORKSPACE_ID = os.getenv("LOG_ANALYTICS_WORKSPACE_ID")
    
    # Application Insights
    APP_INSIGHTS_APP_ID = os.getenv("APP_INSIGHTS_APP_ID")  # Deprecated: use APP_INSIGHTS_RESOURCE_ID
    APP_INSIGHTS_RESOURCE_ID = os.getenv("APP_INSIGHTS_RESOURCE_ID")
    
    # Network Watcher
    NETWORK_WATCHER_RESOURCE_GROUP = os.getenv("NETWORK_WATCHER_RESOURCE_GROUP", "NetworkWatcherRG")
    NETWORK_WATCHER_NAME = os.getenv("NETWORK_WATCHER_NAME", "NetworkWatcher_eastus")
    
    # Azure Monitor
    MONITOR_RESOURCE_IDS = [
        item.strip()
        for item in os.getenv("MONITOR_RESOURCE_IDS", "").split(",")
        if item.strip()
    ]
    _resource_region_overrides_raw = os.getenv("RESOURCE_REGION_OVERRIDES_JSON", "{}")
    try:
        _resource_region_overrides_obj = json.loads(_resource_region_overrides_raw)
        if isinstance(_resource_region_overrides_obj, dict):
            RESOURCE_REGION_OVERRIDES = {
                str(key).strip().lower(): str(value).strip()
                for key, value in _resource_region_overrides_obj.items()
                if str(key).strip() and str(value).strip()
            }
        else:
            RESOURCE_REGION_OVERRIDES = {}
    except Exception:
        RESOURCE_REGION_OVERRIDES = {}

    # Sample replay blob configuration
    SAMPLE_BLOB_SAS_URL = os.getenv("SAMPLE_BLOB_SAS_URL")
    SAMPLE_BLOB_CONTAINER = os.getenv("SAMPLE_BLOB_CONTAINER", "rca-sample-ingestion").strip()
    SAMPLE_BLOB_PREFIX = os.getenv("SAMPLE_BLOB_PREFIX", "v1").strip().strip("/")
    SAMPLE_REPLAY_REBASE_TIMESTAMPS = (
        os.getenv("SAMPLE_REPLAY_REBASE_TIMESTAMPS", "true").strip().lower()
        in {"1", "true", "yes", "on"}
    )

    # Polling interval (seconds)
    COLLECTION_INTERVAL = int(os.getenv("COLLECTION_INTERVAL", "30"))

    # Lookback window for queries (minutes)
    LOOKBACK_MINUTES = int(os.getenv("LOOKBACK_MINUTES", "5"))

    # Overlap window to protect against late-arriving records (seconds)
    LOOKBACK_OVERLAP_SECONDS = int(os.getenv("LOOKBACK_OVERLAP_SECONDS", "30"))

    # Ingestion delay to avoid querying not-yet-indexed telemetry (seconds)
    INGESTION_DELAY_SECONDS = int(os.getenv("INGESTION_DELAY_SECONDS", "60"))

    # Event deduplication TTL in minutes (scheduler cache)
    DEDUP_WINDOW_MINUTES = int(os.getenv("DEDUP_WINDOW_MINUTES", "10"))

    # Ingestion mode
    # live: use Azure API collectors
    # sample_blob: replay normalized TelemetryEvent JSONL from blob storage
    INGESTION_MODE = os.getenv("INGESTION_MODE", "live").strip().lower()


def get_azure_credential():
    """
    Get Azure credential using DefaultAzureCredential chain.
    By default, managed identity remains enabled for Azure-hosted runtimes.
    For local environments that cannot reach IMDS, set:
    AZURE_DISABLE_MANAGED_IDENTITY=true

    If service principal environment variables are set, use ClientSecretCredential
    to enforce least-privilege SP authentication and avoid dependency on Azure CLI
    user/device login state.

    Returns:
        azure.identity credential object
    """
    tenant_id = (os.getenv("AZURE_TENANT_ID") or "").strip()
    client_id = (os.getenv("AZURE_CLIENT_ID") or "").strip()
    client_secret = (os.getenv("AZURE_CLIENT_SECRET") or "").strip()
    if tenant_id and client_id and client_secret:
        return ClientSecretCredential(
            tenant_id=tenant_id,
            client_id=client_id,
            client_secret=client_secret,
        )

    disable_managed_identity = (
        os.getenv("AZURE_DISABLE_MANAGED_IDENTITY", "false").strip().lower()
        in {"1", "true", "yes", "on"}
    )
    return DefaultAzureCredential(
        exclude_managed_identity_credential=disable_managed_identity
    )
