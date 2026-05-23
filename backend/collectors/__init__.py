"""
Azure data collectors for RCA system.
Each collector extracts telemetry from specific Azure service.
"""

from .collector_base import CollectorBase
from .log_analytics_collector import LogAnalyticsCollector
from .appinsights_collector import AppInsightsCollector
from .network_watcher_collector import NetworkWatcherCollector
from .monitor_metrics_collector import MonitorMetricsCollector
from .activity_health_collector import ActivityHealthCollector

__all__ = [
    "CollectorBase",
    "LogAnalyticsCollector",
    "AppInsightsCollector",
    "NetworkWatcherCollector",
    "MonitorMetricsCollector",
    "ActivityHealthCollector",
]
