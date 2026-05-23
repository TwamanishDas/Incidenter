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
from ..models import ApplicationPayload, DatabasePayload, TelemetryEvent, TelemetryOrigin, TelemetrySource
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
            if "/providers/Microsoft.Sql/servers/" in resource_id:
                sql_event = self._query_sql_metrics(resource_id, start_time, end_time)
                if sql_event:
                    events.append(sql_event)
            elif "/providers/Microsoft.Compute/virtualMachines/" in resource_id:
                vm_event = self._query_vm_metrics(resource_id, start_time, end_time)
                if vm_event:
                    events.append(vm_event)
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
        network_in = self._first_available_metric(resource_id, ["Network In Total"], start_time, end_time, preferred=("total", "average", "maximum"))
        network_out = self._first_available_metric(resource_id, ["Network Out Total"], start_time, end_time, preferred=("total", "average", "maximum"))
        disk_read = self._first_available_metric(resource_id, ["Disk Read Bytes"], start_time, end_time, preferred=("total", "average", "maximum"))
        disk_write = self._first_available_metric(resource_id, ["Disk Write Bytes"], start_time, end_time, preferred=("total", "average", "maximum"))

        if all(value is None for value in (cpu_percent, network_in, network_out, disk_read, disk_write)):
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

        return TelemetryEvent(
            timestamp=end_time,
            source=TelemetrySource.APPLICATION,
            origin=TelemetryOrigin.AZURE_MONITOR_METRICS,
            payload=payload_data,
            raw_message="Azure Monitor VM metrics summary",
            resource_id=resource_id,
            subscription_id=_subscription_from_resource_id(resource_id) or AzureConfig.SUBSCRIPTION_ID,
            region=region,
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
                aggregations=["Average", "Maximum", "Total"],
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
