"""
Azure Monitor Metrics collector.
Collects real SQL and VM metrics using MetricsQueryClient and enriches SQL waits from diagnostics.
"""

from datetime import datetime, timedelta
import hashlib
import logging

from azure.core.exceptions import HttpResponseError
from azure.monitor.query import LogsQueryClient, MetricsQueryClient

from ..azure_config import AzureConfig, get_azure_credential
from ..models import (
    ApplicationPayload,
    DatabasePayload,
    NetworkPayload,
    TelemetryEvent,
    TelemetryOrigin,
    TelemetryRecordType,
    TelemetrySource,
)
from .collector_base import CollectorBase
from .kql_utils import as_float, as_int, rows_as_dicts

logger = logging.getLogger(__name__)


def _resource_name(resource_id: str) -> str:
    if not resource_id:
        return "unknown-resource"
    return resource_id.rstrip("/").split("/")[-1]


def _subscription_from_resource_id(resource_id: str) -> str | None:
    parts = [p for p in resource_id.strip("/").split("/") if p]
    for index, part in enumerate(parts):
        if part.lower() == "subscriptions" and index + 1 < len(parts):
            return parts[index + 1]
    return None


def _region_from_resource_id(resource_id: str) -> str | None:
    parts = [p for p in resource_id.strip("/").split("/") if p]
    for index, part in enumerate(parts):
        if part.lower() == "locations" and index + 1 < len(parts):
            return parts[index + 1]
    return None


def _to_kql_datetime(value: datetime) -> str:
    return value.strftime("%Y-%m-%dT%H:%M:%SZ")


class MonitorMetricsCollector(CollectorBase):
    """Collect resource metrics from Azure Monitor Metrics API."""

    def __init__(self, resource_ids: list[str] | None = None):
        super().__init__("MonitorMetricsCollector", TelemetrySource.DATABASE)
        self.resource_ids = resource_ids if resource_ids is not None else AzureConfig.MONITOR_RESOURCE_IDS
        if not self.resource_ids:
            logger.warning("MonitorMetricsCollector: MONITOR_RESOURCE_IDS not configured")

        try:
            credential = get_azure_credential()
            self.metrics_client = MetricsQueryClient(credential)
            self.logs_client = LogsQueryClient(credential)
        except Exception as exc:
            logger.error("MonitorMetricsCollector: failed to initialize clients: %s", exc)
            self.metrics_client = None
            self.logs_client = None

    def collect(self) -> list[TelemetryEvent]:
        if not self.metrics_client or not self.resource_ids:
            return []

        start_time, end_time = self.get_query_window()
        events: list[TelemetryEvent] = []
        for resource_id in self.resource_ids:
            resource_id_lower = resource_id.lower()
            if "/providers/microsoft.sql/servers/" in resource_id_lower:
                sql_event = self._query_sql_metrics(resource_id, start_time, end_time)
                if sql_event:
                    events.append(sql_event)
            elif "/providers/microsoft.compute/virtualmachines/" in resource_id_lower:
                vm_event = self._query_vm_metrics(resource_id, start_time, end_time)
                if vm_event:
                    events.append(vm_event)
            elif "/providers/microsoft.web/sites/" in resource_id_lower:
                app_service_event = self._query_app_service_metrics(resource_id, start_time, end_time)
                if app_service_event:
                    events.append(app_service_event)
            elif "/providers/microsoft.network/azurefirewalls/" in resource_id_lower:
                firewall_event = self._query_azure_firewall_metrics(resource_id, start_time, end_time)
                if firewall_event:
                    events.append(firewall_event)
            elif "/providers/microsoft.documentdb/databaseaccounts/" in resource_id_lower:
                cosmos_event = self._query_cosmos_metrics(resource_id, start_time, end_time)
                if cosmos_event:
                    events.append(cosmos_event)
            elif "/providers/microsoft.cache/redis/" in resource_id_lower:
                redis_event = self._query_redis_metrics(resource_id, start_time, end_time)
                if redis_event:
                    events.append(redis_event)
            else:
                logger.debug("MonitorMetricsCollector: unsupported resource type for %s", resource_id)
        return events

    def _resolve_region(self, resource_id: str, source_region: str | None = None) -> str | None:
        if source_region:
            return source_region
        override = AzureConfig.RESOURCE_REGION_OVERRIDES.get(resource_id.lower())
        if override:
            return override
        return _region_from_resource_id(resource_id)

    @staticmethod
    def _synthetic_correlation_id(resource_id: str, operation_name: str, start_time: datetime, end_time: datetime) -> str:
        raw = f"{resource_id}|{operation_name}|{start_time.isoformat()}|{end_time.isoformat()}"
        return hashlib.sha1(raw.encode("utf-8")).hexdigest()

    def _query_sql_metrics(
        self,
        resource_id: str,
        start_time: datetime,
        end_time: datetime,
    ) -> TelemetryEvent | None:
        cpu_percent = self._first_available_metric(resource_id, ["cpu_percent", "sqlserver_process_core_percent"], start_time, end_time)
        sessions_percent = self._first_available_metric(resource_id, ["sessions_percent", "sessions_count"], start_time, end_time)
        workers_percent = self._first_available_metric(resource_id, ["workers_percent"], start_time, end_time)
        deadlocks_total = self._first_available_metric(resource_id, ["deadlock"], start_time, end_time, preferred=("total", "maximum", "average"))
        avg_query_duration = self._first_available_metric(resource_id, ["avg_cpu_percent", "cpu_percent"], start_time, end_time)

        wait_count, avg_wait_ms, wait_correlation_id, wait_region = self._query_sql_wait_signals(resource_id, start_time, end_time)
        if all(value is None for value in (cpu_percent, sessions_percent, workers_percent, deadlocks_total, avg_query_duration)) and wait_count == 0 and avg_wait_ms <= 0:
            return None
        operation_name = "AzureMonitorSQLMetricsSummary"
        correlation_id = wait_correlation_id or self._synthetic_correlation_id(resource_id, operation_name, start_time, end_time)
        region = self._resolve_region(resource_id, wait_region)

        payload = DatabasePayload(
            database_name=_resource_name(resource_id),
            connection_errors=0,
            timeout_count=max(0, wait_count),
            deadlock_count=max(0, int(deadlocks_total or 0)),
            avg_query_duration_ms=max(0.0, avg_wait_ms if avg_wait_ms > 0 else (avg_query_duration or 0.0)),
            cpu_percent=max(0.0, float(cpu_percent or 0.0)),
            worker_count=max(0, int(workers_percent or 0.0)),
        )
        payload_data = payload.model_dump()
        payload_data["sessions_percent"] = max(0.0, float(sessions_percent or 0.0))
        payload_data["wait_event_count"] = max(0, wait_count)

        return TelemetryEvent(
            timestamp=end_time,
            source=TelemetrySource.DATABASE,
            origin=TelemetryOrigin.AZURE_MONITOR_METRICS,
            source_system="Azure SQL Database",
            source_category="sql_platform_metrics",
            record_type=TelemetryRecordType.METRIC,
            collection_channel="Azure Monitor Metrics API",
            payload=payload_data,
            raw_message="Azure Monitor SQL metrics summary",
            resource_id=resource_id,
            subscription_id=_subscription_from_resource_id(resource_id) or AzureConfig.SUBSCRIPTION_ID,
            region=region,
            operation_name=operation_name,
            correlation_id=correlation_id,
        )

    def _query_vm_metrics(
        self,
        resource_id: str,
        start_time: datetime,
        end_time: datetime,
    ) -> TelemetryEvent | None:
        cpu_percent = self._first_available_metric(resource_id, ["Percentage CPU"], start_time, end_time)
        available_memory_bytes = self._first_available_metric(resource_id, ["Available Memory Bytes"], start_time, end_time, preferred=("average", "minimum", "maximum", "total"))
        network_in = self._first_available_metric(resource_id, ["Network In Total"], start_time, end_time, preferred=("total", "average", "maximum"))
        network_out = self._first_available_metric(resource_id, ["Network Out Total"], start_time, end_time, preferred=("total", "average", "maximum"))
        disk_read = self._first_available_metric(resource_id, ["Disk Read Bytes"], start_time, end_time, preferred=("total", "average", "maximum"))
        disk_write = self._first_available_metric(resource_id, ["Disk Write Bytes"], start_time, end_time, preferred=("total", "average", "maximum"))
        os_disk_queue_depth = self._first_available_metric(resource_id, ["OS Disk Queue Depth"], start_time, end_time, preferred=("maximum", "average", "total"))

        if all(
            value is None
            for value in (
                cpu_percent,
                available_memory_bytes,
                network_in,
                network_out,
                disk_read,
                disk_write,
                os_disk_queue_depth,
            )
        ):
            return None

        inferred_error_rate = 0.0
        if cpu_percent is not None and cpu_percent > 90:
            inferred_error_rate = min(100.0, (cpu_percent - 90) * 10)
        operation_name = "AzureMonitorVMMetricsSummary"
        correlation_id = self._synthetic_correlation_id(resource_id, operation_name, start_time, end_time)
        region = self._resolve_region(resource_id)

        payload = ApplicationPayload(
            application_name=f"vm:{_resource_name(resource_id)}",
            request_rate_per_min=0,
            error_rate_pct=inferred_error_rate,
            avg_response_ms=0.0,
            p95_response_ms=0.0,
            status_5xx_count=0,
        )
        payload_data = payload.model_dump()
        payload_data["vm_cpu_percent"] = max(0.0, float(cpu_percent or 0.0))
        payload_data["network_in_total"] = max(0.0, float(network_in or 0.0))
        payload_data["network_out_total"] = max(0.0, float(network_out or 0.0))
        payload_data["disk_read_bytes"] = max(0.0, float(disk_read or 0.0))
        payload_data["disk_write_bytes"] = max(0.0, float(disk_write or 0.0))
        payload_data["available_memory_bytes"] = max(0.0, float(available_memory_bytes or 0.0))
        payload_data["os_disk_queue_depth"] = max(0.0, float(os_disk_queue_depth or 0.0))

        return TelemetryEvent(
            timestamp=end_time,
            source=TelemetrySource.APPLICATION,
            origin=TelemetryOrigin.AZURE_MONITOR_METRICS,
            source_system="Azure Virtual Machine",
            source_category="vm_platform_metrics",
            record_type=TelemetryRecordType.METRIC,
            collection_channel="Azure Monitor Metrics API",
            payload=payload_data,
            raw_message="Azure Monitor VM metrics summary",
            resource_id=resource_id,
            subscription_id=_subscription_from_resource_id(resource_id) or AzureConfig.SUBSCRIPTION_ID,
            region=region,
            operation_name=operation_name,
            correlation_id=correlation_id,
        )

    def _query_app_service_metrics(
        self,
        resource_id: str,
        start_time: datetime,
        end_time: datetime,
    ) -> TelemetryEvent | None:
        http_2xx = self._first_available_metric(resource_id, ["Http2xx"], start_time, end_time, preferred=("total", "average", "maximum"))
        http_3xx = self._first_available_metric(resource_id, ["Http3xx"], start_time, end_time, preferred=("total", "average", "maximum"))
        http_4xx = self._first_available_metric(resource_id, ["Http4xx"], start_time, end_time, preferred=("total", "average", "maximum"))
        http_5xx = self._first_available_metric(resource_id, ["Http5xx"], start_time, end_time, preferred=("total", "average", "maximum"))
        avg_response_ms = self._first_available_metric(resource_id, ["AverageResponseTime"], start_time, end_time)
        app_queue = self._first_available_metric(resource_id, ["RequestsInApplicationQueue", "HttpQueueLength"], start_time, end_time, preferred=("maximum", "average", "total"))
        cpu_percent = self._first_available_metric(resource_id, ["CpuPercentage"], start_time, end_time)
        memory_percent = self._first_available_metric(resource_id, ["MemoryPercentage"], start_time, end_time)

        if all(
            value is None
            for value in (http_2xx, http_3xx, http_4xx, http_5xx, avg_response_ms, app_queue, cpu_percent, memory_percent)
        ):
            return None

        total_requests = max(0.0, float(http_2xx or 0.0) + float(http_3xx or 0.0) + float(http_4xx or 0.0) + float(http_5xx or 0.0))
        error_rate = min(100.0, (float(http_5xx or 0.0) / max(1.0, total_requests)) * 100.0)
        window_minutes = max(1, int((end_time - start_time).total_seconds() / 60))
        operation_name = "AzureMonitorAppServiceMetricsSummary"
        correlation_id = self._synthetic_correlation_id(resource_id, operation_name, start_time, end_time)

        payload = ApplicationPayload(
            application_name=f"appservice:{_resource_name(resource_id)}",
            request_rate_per_min=max(0, int(total_requests / window_minutes)),
            error_rate_pct=error_rate,
            avg_response_ms=max(0.0, float(avg_response_ms or 0.0)),
            p95_response_ms=None,
            status_5xx_count=max(0, int(http_5xx or 0.0)),
        )
        payload_data = payload.model_dump()
        payload_data["http_2xx"] = max(0.0, float(http_2xx or 0.0))
        payload_data["http_3xx"] = max(0.0, float(http_3xx or 0.0))
        payload_data["http_4xx"] = max(0.0, float(http_4xx or 0.0))
        payload_data["http_5xx"] = max(0.0, float(http_5xx or 0.0))
        payload_data["requests_in_application_queue"] = max(0.0, float(app_queue or 0.0))
        payload_data["plan_cpu_percent"] = max(0.0, float(cpu_percent or 0.0))
        payload_data["plan_memory_percent"] = max(0.0, float(memory_percent or 0.0))

        return TelemetryEvent(
            timestamp=end_time,
            source=TelemetrySource.APPLICATION,
            origin=TelemetryOrigin.AZURE_MONITOR_METRICS,
            source_system="Azure App Service",
            source_category="app_service_http_and_plan_metrics",
            record_type=TelemetryRecordType.METRIC,
            collection_channel="Azure Monitor Metrics API",
            payload=payload_data,
            raw_message="Azure Monitor App Service metrics summary",
            resource_id=resource_id,
            subscription_id=_subscription_from_resource_id(resource_id) or AzureConfig.SUBSCRIPTION_ID,
            region=self._resolve_region(resource_id),
            operation_name=operation_name,
            correlation_id=correlation_id,
        )

    def _query_azure_firewall_metrics(
        self,
        resource_id: str,
        start_time: datetime,
        end_time: datetime,
    ) -> TelemetryEvent | None:
        app_rule_hits = self._first_available_metric(resource_id, ["ApplicationRuleHit"], start_time, end_time, preferred=("total", "maximum", "average"))
        network_rule_hits = self._first_available_metric(resource_id, ["NetworkRuleHit"], start_time, end_time, preferred=("total", "maximum", "average"))
        data_processed = self._first_available_metric(resource_id, ["DataProcessed"], start_time, end_time, preferred=("total", "maximum", "average"))
        snat_utilization = self._first_available_metric(resource_id, ["SNATPortUtilization"], start_time, end_time, preferred=("maximum", "average", "total"))
        threat_intel_alerts = self._first_available_metric(resource_id, ["ThreatIntelAlerts"], start_time, end_time, preferred=("total", "maximum", "average"))

        if all(value is None for value in (app_rule_hits, network_rule_hits, data_processed, snat_utilization, threat_intel_alerts)):
            return None

        operation_name = "AzureMonitorAzureFirewallMetricsSummary"
        correlation_id = self._synthetic_correlation_id(resource_id, operation_name, start_time, end_time)
        payload = NetworkPayload(
            source_ip=None,
            destination_ip=None,
            destination_port=0,
            packet_loss=0.0,
            avg_latency_ms=0.0,
            nsg_denied_connections=max(0, int(threat_intel_alerts or 0.0)),
            tcp_retry_count=max(0, int((snat_utilization or 0.0) / 10)),
        )
        payload_data = payload.model_dump()
        payload_data["application_rule_hit"] = max(0.0, float(app_rule_hits or 0.0))
        payload_data["network_rule_hit"] = max(0.0, float(network_rule_hits or 0.0))
        payload_data["data_processed"] = max(0.0, float(data_processed or 0.0))
        payload_data["snat_port_utilization"] = max(0.0, float(snat_utilization or 0.0))
        payload_data["threat_intel_alerts"] = max(0.0, float(threat_intel_alerts or 0.0))

        return TelemetryEvent(
            timestamp=end_time,
            source=TelemetrySource.NETWORK,
            origin=TelemetryOrigin.AZURE_MONITOR_METRICS,
            source_system="Azure Firewall",
            source_category="azure_firewall_metrics",
            record_type=TelemetryRecordType.METRIC,
            collection_channel="Azure Monitor Metrics API",
            payload=payload_data,
            raw_message="Azure Monitor Azure Firewall metrics summary",
            resource_id=resource_id,
            subscription_id=_subscription_from_resource_id(resource_id) or AzureConfig.SUBSCRIPTION_ID,
            region=self._resolve_region(resource_id),
            operation_name=operation_name,
            correlation_id=correlation_id,
        )

    def _query_cosmos_metrics(
        self,
        resource_id: str,
        start_time: datetime,
        end_time: datetime,
    ) -> TelemetryEvent | None:
        request_units = self._first_available_metric(
            resource_id,
            ["TotalRequestUnits", "MongoRequestCharge", "Request Units consumed"],
            start_time,
            end_time,
            preferred=("total", "average", "maximum"),
        )
        total_requests = self._first_available_metric(
            resource_id,
            ["TotalRequests", "Total Requests"],
            start_time,
            end_time,
            preferred=("total", "average", "maximum"),
        )
        availability = self._first_available_metric(
            resource_id,
            ["Availability", "AvailabilityPercent"],
            start_time,
            end_time,
            preferred=("average", "minimum", "maximum"),
        )
        replication_latency_ms = self._first_available_metric(
            resource_id,
            ["ReplicationLatency", "ReplicationLatencyMs"],
            start_time,
            end_time,
            preferred=("average", "maximum", "total"),
        )

        if all(value is None for value in (request_units, total_requests, availability, replication_latency_ms)):
            return None

        operation_name = "AzureMonitorCosmosMetricsSummary"
        correlation_id = self._synthetic_correlation_id(resource_id, operation_name, start_time, end_time)
        payload = DatabasePayload(
            database_name=f"cosmos:{_resource_name(resource_id)}",
            connection_errors=0,
            timeout_count=0,
            deadlock_count=0,
            avg_query_duration_ms=max(0.0, float(replication_latency_ms or 0.0)),
            cpu_percent=None,
            worker_count=None,
        )
        payload_data = payload.model_dump()
        payload_data["request_units_consumed"] = max(0.0, float(request_units or 0.0))
        payload_data["total_requests"] = max(0.0, float(total_requests or 0.0))
        payload_data["availability_percent"] = max(0.0, float(availability or 0.0))
        payload_data["replication_latency_ms"] = max(0.0, float(replication_latency_ms or 0.0))

        return TelemetryEvent(
            timestamp=end_time,
            source=TelemetrySource.DATABASE,
            origin=TelemetryOrigin.AZURE_MONITOR_METRICS,
            source_system="Azure Cosmos DB",
            source_category="cosmos_metrics",
            record_type=TelemetryRecordType.METRIC,
            collection_channel="Azure Monitor Metrics API",
            payload=payload_data,
            raw_message="Azure Monitor Cosmos DB metrics summary",
            resource_id=resource_id,
            subscription_id=_subscription_from_resource_id(resource_id) or AzureConfig.SUBSCRIPTION_ID,
            region=self._resolve_region(resource_id),
            operation_name=operation_name,
            correlation_id=correlation_id,
        )

    def _query_redis_metrics(
        self,
        resource_id: str,
        start_time: datetime,
        end_time: datetime,
    ) -> TelemetryEvent | None:
        cache_hits = self._first_available_metric(resource_id, ["CacheHits"], start_time, end_time, preferred=("total", "average", "maximum"))
        cache_misses = self._first_available_metric(resource_id, ["CacheMisses"], start_time, end_time, preferred=("total", "average", "maximum"))
        cache_read = self._first_available_metric(resource_id, ["CacheRead"], start_time, end_time, preferred=("total", "average", "maximum"))
        cache_write = self._first_available_metric(resource_id, ["CacheWrite"], start_time, end_time, preferred=("total", "average", "maximum"))
        connected_clients = self._first_available_metric(resource_id, ["ConnectedClients"], start_time, end_time, preferred=("average", "maximum", "total"))
        used_memory_pct = self._first_available_metric(resource_id, ["UsedMemoryPercentage"], start_time, end_time, preferred=("average", "maximum", "total"))
        server_load = self._first_available_metric(resource_id, ["ServerLoad"], start_time, end_time, preferred=("average", "maximum", "total"))

        if all(value is None for value in (cache_hits, cache_misses, cache_read, cache_write, connected_clients, used_memory_pct, server_load)):
            return None

        total_lookup = max(0.0, float(cache_hits or 0.0) + float(cache_misses or 0.0))
        miss_rate_pct = min(100.0, (float(cache_misses or 0.0) / max(1.0, total_lookup)) * 100.0)
        load_error_rate = 0.0 if server_load is None else min(100.0, max(0.0, float(server_load) - 85.0))
        error_rate = max(miss_rate_pct, load_error_rate)
        window_minutes = max(1, int((end_time - start_time).total_seconds() / 60))
        total_ops = max(0.0, float(cache_read or 0.0) + float(cache_write or 0.0))
        operation_name = "AzureMonitorRedisMetricsSummary"
        correlation_id = self._synthetic_correlation_id(resource_id, operation_name, start_time, end_time)

        payload = ApplicationPayload(
            application_name=f"redis:{_resource_name(resource_id)}",
            request_rate_per_min=max(0, int(total_ops / window_minutes)),
            error_rate_pct=error_rate,
            avg_response_ms=0.0,
            p95_response_ms=None,
            status_5xx_count=0,
        )
        payload_data = payload.model_dump()
        payload_data["cache_hits"] = max(0.0, float(cache_hits or 0.0))
        payload_data["cache_misses"] = max(0.0, float(cache_misses or 0.0))
        payload_data["cache_read"] = max(0.0, float(cache_read or 0.0))
        payload_data["cache_write"] = max(0.0, float(cache_write or 0.0))
        payload_data["connected_clients"] = max(0.0, float(connected_clients or 0.0))
        payload_data["used_memory_percentage"] = max(0.0, float(used_memory_pct or 0.0))
        payload_data["server_load"] = max(0.0, float(server_load or 0.0))
        payload_data["cache_miss_rate_pct"] = miss_rate_pct

        return TelemetryEvent(
            timestamp=end_time,
            source=TelemetrySource.APPLICATION,
            origin=TelemetryOrigin.AZURE_MONITOR_METRICS,
            source_system="Azure Cache for Redis",
            source_category="redis_cache_metrics",
            record_type=TelemetryRecordType.METRIC,
            collection_channel="Azure Monitor Metrics API",
            payload=payload_data,
            raw_message="Azure Monitor Redis metrics summary",
            resource_id=resource_id,
            subscription_id=_subscription_from_resource_id(resource_id) or AzureConfig.SUBSCRIPTION_ID,
            region=self._resolve_region(resource_id),
            operation_name=operation_name,
            correlation_id=correlation_id,
        )

    def _first_available_metric(
        self,
        resource_id: str,
        metric_names: list[str],
        start_time: datetime,
        end_time: datetime,
        preferred: tuple[str, ...] = ("average", "maximum", "total"),
    ) -> float | None:
        for metric_name in metric_names:
            value = self._query_metric_value(resource_id, metric_name, start_time, end_time, preferred)
            if value is not None:
                return value
        return None

    def _query_metric_value(
        self,
        resource_id: str,
        metric_name: str,
        start_time: datetime,
        end_time: datetime,
        preferred: tuple[str, ...],
    ) -> float | None:
        try:
            result = self.metrics_client.query_resource(
                resource_uri=resource_id,
                metric_names=[metric_name],
                timespan=(start_time, end_time),
                granularity=timedelta(minutes=1),
                aggregations=["Average", "Maximum", "Total", "Minimum"],
            )
        except HttpResponseError:
            return None
        except Exception as exc:
            logger.debug("MonitorMetricsCollector: metric query failed for %s (%s): %s", metric_name, resource_id, exc)
            return None

        if not getattr(result, "metrics", None):
            return None

        for metric in result.metrics:
            for series in metric.timeseries:
                for point in reversed(series.data):
                    for aggregation in preferred:
                        value = getattr(point, aggregation, None)
                        if value is not None:
                            return float(value)
        return None

    def _query_sql_wait_signals(
        self,
        resource_id: str,
        start_time: datetime,
        end_time: datetime,
    ) -> tuple[int, float, str | None, str | None]:
        workspace_id = AzureConfig.LOG_ANALYTICS_WORKSPACE_ID
        if not workspace_id or not self.logs_client:
            return 0, 0.0, None, None

        safe_resource_id = resource_id.replace("'", "''")
        query = f"""
        AzureDiagnostics
        | where TimeGenerated between (datetime({_to_kql_datetime(start_time)}) .. datetime({_to_kql_datetime(end_time)}))
        | where tostring(coalesce(_ResourceId, ResourceId)) =~ "{safe_resource_id}"
        | where Category has "Wait" or Category has "QueryStore"
        | extend WaitDurationMs = todouble(coalesce(durationMs_s, DurationMs, timeTaken_d))
        | summarize
            WaitCount = count(),
            AvgWaitMs = avg(WaitDurationMs),
            LastSeen = max(TimeGenerated),
            CorrelationId = any(tostring(coalesce(CorrelationId, correlationId_g))),
            Region = any(tostring(ResourceLocation))
        """

        try:
            response = self.logs_client.query_workspace(workspace_id, query, timespan=(start_time, end_time))
        except HttpResponseError:
            return 0, 0.0, None, None
        except Exception as exc:
            logger.debug("MonitorMetricsCollector: SQL wait query failed for %s: %s", resource_id, exc)
            return 0, 0.0, None, None

        rows = rows_as_dicts(response)
        if not rows:
            return 0, 0.0, None, None

        row = rows[0]
        return (
            as_int(row.get("WaitCount")),
            as_float(row.get("AvgWaitMs")),
            row.get("CorrelationId") or None,
            row.get("Region") or None,
        )
