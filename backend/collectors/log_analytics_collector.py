"""
Azure Log Analytics collector.
Ingests application summaries, Azure Monitor diagnostics, and ingress/WAF logs.
"""

from datetime import datetime
from typing import Optional
import logging

from azure.core.exceptions import HttpResponseError
from azure.monitor.query import LogsQueryClient

from ..azure_config import AzureConfig, get_azure_credential
from ..models import (
    ApplicationPayload,
    DatabasePayload,
    NetworkPayload,
    TelemetryEvent,
    TelemetryOrigin,
    TelemetrySource,
)
from .collector_base import CollectorBase
from .kql_utils import as_float, as_int, parse_utc_timestamp, rows_as_dicts

logger = logging.getLogger(__name__)


def _to_kql_datetime(value: datetime) -> str:
    return value.strftime("%Y-%m-%dT%H:%M:%SZ")


def _resource_name_from_id(resource_id: str) -> str:
    if not resource_id:
        return "unknown-resource"
    return resource_id.rstrip("/").split("/")[-1]


class LogAnalyticsCollector(CollectorBase):
    """Collect telemetry from Azure Log Analytics workspace."""

    def __init__(self, workspace_id: Optional[str] = None):
        super().__init__("LogAnalyticsCollector", TelemetrySource.APPLICATION)
        self.workspace_id = workspace_id or AzureConfig.LOG_ANALYTICS_WORKSPACE_ID
        if not self.workspace_id:
            logger.warning("LogAnalyticsCollector: LOG_ANALYTICS_WORKSPACE_ID not configured")

        try:
            credential = get_azure_credential()
            self.client = LogsQueryClient(credential)
        except Exception as exc:
            logger.error("LogAnalyticsCollector: failed to initialize client: %s", exc)
            self.client = None

    def collect(self) -> list[TelemetryEvent]:
        if not self.client or not self.workspace_id:
            return []

        start_time, end_time = self.get_query_window()
        events: list[TelemetryEvent] = []
        events.extend(self._query_application_metrics(start_time, end_time))
        events.extend(self._query_diagnostic_signals(start_time, end_time))
        events.extend(self._query_ingress_waf_signals(start_time, end_time))
        return events

    def _query_application_metrics(self, start_time: datetime, end_time: datetime) -> list[TelemetryEvent]:
        query = f"""
        union isfuzzy=true AppRequests, requests
        | extend EventTime = coalesce(
            todatetime(column_ifexists("TimeGenerated", datetime(null))),
            todatetime(column_ifexists("timestamp", datetime(null)))
          )
        | where isnotnull(EventTime)
        | where EventTime between (datetime({_to_kql_datetime(start_time)}) .. datetime({_to_kql_datetime(end_time)}))
        | summarize
            TotalRequests = count(),
            FailedRequests = countif(
                tobool(coalesce(column_ifexists("Success", bool(null)), column_ifexists("success", bool(null)))) == false
              ),
            Errors5xx = countif(
                tostring(coalesce(column_ifexists("ResultCode", ""), column_ifexists("resultCode", ""))) startswith "5"
              ),
            AvgDurationMs = avg(
                todouble(coalesce(column_ifexists("DurationMs", real(null)), column_ifexists("duration", real(null))))
              ),
            P95DurationMs = percentile(
                todouble(coalesce(column_ifexists("DurationMs", real(null)), column_ifexists("duration", real(null)))),
                95
              ),
            LastSeen = max(EventTime),
            ResourceId = any(tostring(coalesce(column_ifexists("_ResourceId", ""), column_ifexists("ResourceId", "")))),
            SubscriptionId = any(tostring(coalesce(column_ifexists("_SubscriptionId", ""), column_ifexists("SubscriptionId", "")))),
            Region = any(tostring(coalesce(
                column_ifexists("ResourceLocation", ""),
                column_ifexists("AppRoleInstance", ""),
                column_ifexists("cloud_RoleInstance", "")
              )))
          by AppName = tostring(coalesce(
              column_ifexists("AppId", ""),
              column_ifexists("cloud_RoleName", ""),
              column_ifexists("AppRoleName", ""),
              "unknown-app"
            ))
        | where TotalRequests > 0
        """

        events: list[TelemetryEvent] = []
        response = self.client.query_workspace(self.workspace_id, query, timespan=(start_time, end_time))
        for row in rows_as_dicts(response):
            total_requests = as_int(row.get("TotalRequests"))
            if total_requests <= 0:
                continue

            failed_requests = as_int(row.get("FailedRequests"))
            errors_5xx = as_int(row.get("Errors5xx"))
            avg_duration_ms = as_float(row.get("AvgDurationMs"))
            p95_duration_ms = as_float(row.get("P95DurationMs"))
            window_minutes = max(1, int((end_time - start_time).total_seconds() / 60))
            error_rate = min(100.0, (failed_requests / total_requests) * 100.0)

            payload = ApplicationPayload(
                application_name=str(row.get("AppName") or "unknown-app"),
                request_rate_per_min=max(1, int(total_requests / window_minutes)),
                error_rate_pct=error_rate,
                avg_response_ms=avg_duration_ms,
                p95_response_ms=p95_duration_ms,
                status_5xx_count=errors_5xx,
            )

            event = TelemetryEvent(
                timestamp=parse_utc_timestamp(row.get("LastSeen"), end_time),
                source=TelemetrySource.APPLICATION,
                origin=TelemetryOrigin.LOG_ANALYTICS,
                payload=payload.model_dump(),
                resource_id=row.get("ResourceId") or None,
                subscription_id=row.get("SubscriptionId") or AzureConfig.SUBSCRIPTION_ID,
                region=row.get("Region") or None,
                operation_name="ApplicationRequestsSummary",
            )
            events.append(event)
        return events

    def _query_diagnostic_signals(self, start_time: datetime, end_time: datetime) -> list[TelemetryEvent]:
        query = f"""
        AzureDiagnostics
        | where TimeGenerated between (datetime({_to_kql_datetime(start_time)}) .. datetime({_to_kql_datetime(end_time)}))
        | extend
            Provider = tostring(ResourceProvider),
            CategoryNorm = tostring(Category),
            LevelNorm = tostring(coalesce(Level, SeverityLevel, resultType_s)),
            DurationMs = todouble(coalesce(DurationMs, timeTaken_d, durationMs_s)),
            ResourceIdNorm = tostring(coalesce(_ResourceId, ResourceId)),
            SubscriptionNorm = tostring(coalesce(_SubscriptionId, SubscriptionId)),
            CorrelationNorm = tostring(coalesce(CorrelationId, correlationId_g))
        | summarize
            RecordCount = count(),
            ErrorCount = countif(LevelNorm in~ ("Error", "Critical", "Sev3", "Sev4")),
            AvgDurationMs = avg(DurationMs),
            LastSeen = max(TimeGenerated),
            Region = any(tostring(ResourceLocation)),
            OperationName = any(tostring(OperationName)),
            CorrelationId = any(CorrelationNorm)
          by ResourceId = ResourceIdNorm, SubscriptionId = SubscriptionNorm, Provider, Category = CategoryNorm
        | where RecordCount > 0
        """

        events: list[TelemetryEvent] = []
        try:
            response = self.client.query_workspace(self.workspace_id, query, timespan=(start_time, end_time))
        except HttpResponseError as exc:
            logger.error("LogAnalyticsCollector: diagnostics query failed: %s", exc)
            return events

        window_minutes = max(1, int((end_time - start_time).total_seconds() / 60))
        for row in rows_as_dicts(response):
            provider = str(row.get("Provider") or "").lower()
            category = str(row.get("Category") or "")
            error_count = as_int(row.get("ErrorCount"))
            record_count = as_int(row.get("RecordCount"))
            avg_duration = as_float(row.get("AvgDurationMs"))
            source, payload = self._map_diagnostic_payload(
                provider=provider,
                category=category,
                resource_id=str(row.get("ResourceId") or ""),
                record_count=record_count,
                error_count=error_count,
                avg_duration_ms=avg_duration,
                window_minutes=window_minutes,
            )
            if payload is None:
                continue

            event = TelemetryEvent(
                timestamp=parse_utc_timestamp(row.get("LastSeen"), end_time),
                source=source,
                origin=TelemetryOrigin.AZURE_MONITOR_DIAGNOSTICS,
                payload=payload,
                raw_message=f"Diagnostics summary: {category}",
                resource_id=row.get("ResourceId") or None,
                subscription_id=row.get("SubscriptionId") or AzureConfig.SUBSCRIPTION_ID,
                region=row.get("Region") or None,
                operation_name=row.get("OperationName") or "AzureDiagnosticsSummary",
                correlation_id=row.get("CorrelationId") or None,
            )
            events.append(event)
        return events

    def _map_diagnostic_payload(
        self,
        provider: str,
        category: str,
        resource_id: str,
        record_count: int,
        error_count: int,
        avg_duration_ms: float,
        window_minutes: int,
    ) -> tuple[TelemetrySource, Optional[dict]]:
        resource_name = _resource_name_from_id(resource_id)
        if "microsoft.sql" in provider or "sql" in category.lower():
            payload = DatabasePayload(
                database_name=resource_name,
                connection_errors=max(0, error_count),
                timeout_count=0,
                deadlock_count=0,
                avg_query_duration_ms=max(0.0, avg_duration_ms),
            )
            return TelemetrySource.DATABASE, payload.model_dump()

        if "microsoft.network" in provider or "network" in category.lower() or "nsg" in category.lower():
            payload = NetworkPayload(
                source_ip=None,
                destination_ip=None,
                destination_port=None,
                packet_loss=0.0,
                avg_latency_ms=max(0.0, avg_duration_ms),
                nsg_denied_connections=max(0, error_count),
                tcp_retry_count=0,
            )
            return TelemetrySource.NETWORK, payload.model_dump()

        if record_count <= 0:
            return TelemetrySource.APPLICATION, None

        error_rate = min(100.0, (max(0, error_count) / max(1, record_count)) * 100.0)
        payload = ApplicationPayload(
            application_name=resource_name,
            request_rate_per_min=max(1, int(record_count / max(1, window_minutes))),
            error_rate_pct=error_rate,
            avg_response_ms=max(0.0, avg_duration_ms),
            p95_response_ms=None,
            status_5xx_count=max(0, error_count),
        )
        return TelemetrySource.APPLICATION, payload.model_dump()

    def _query_ingress_waf_signals(self, start_time: datetime, end_time: datetime) -> list[TelemetryEvent]:
        query = f"""
        AzureDiagnostics
        | where TimeGenerated between (datetime({_to_kql_datetime(start_time)}) .. datetime({_to_kql_datetime(end_time)}))
        | where Category in~ (
            "FrontDoorAccessLog",
            "FrontDoorWebApplicationFirewallLog",
            "ApplicationGatewayAccessLog",
            "ApplicationGatewayFirewallLog",
            "ApplicationGatewayPerformanceLog"
          )
        | extend
            ResourceIdNorm = tostring(coalesce(_ResourceId, ResourceId)),
            SubscriptionNorm = tostring(coalesce(_SubscriptionId, SubscriptionId)),
            CorrelationNorm = tostring(coalesce(CorrelationId, trackingReference_s)),
            IsBlocked = iif(Action_s in~ ("Block", "Blocked") or action_s in~ ("Block", "Blocked"), 1, 0),
            DurationMs = todouble(coalesce(timeTaken_d, DurationMs, durationMs_s))
        | summarize
            RequestCount = count(),
            BlockCount = sum(IsBlocked),
            AvgLatencyMs = avg(DurationMs),
            LastSeen = max(TimeGenerated),
            Region = any(tostring(ResourceLocation)),
            OperationName = any(tostring(OperationName)),
            CorrelationId = any(CorrelationNorm)
          by ResourceId = ResourceIdNorm, SubscriptionId = SubscriptionNorm, Category
        """

        events: list[TelemetryEvent] = []
        try:
            response = self.client.query_workspace(self.workspace_id, query, timespan=(start_time, end_time))
        except HttpResponseError as exc:
            logger.error("LogAnalyticsCollector: ingress query failed: %s", exc)
            return events

        for row in rows_as_dicts(response):
            category = str(row.get("Category") or "")
            block_count = as_int(row.get("BlockCount"))
            avg_latency = as_float(row.get("AvgLatencyMs"))
            origin = (
                TelemetryOrigin.FRONT_DOOR_WAF
                if "FrontDoor" in category
                else TelemetryOrigin.APP_GATEWAY_WAF
            )
            payload = NetworkPayload(
                source_ip=None,
                destination_ip=None,
                destination_port=443,
                packet_loss=0.0,
                avg_latency_ms=max(0.0, avg_latency),
                nsg_denied_connections=max(0, block_count),
                tcp_retry_count=0,
            )
            event = TelemetryEvent(
                timestamp=parse_utc_timestamp(row.get("LastSeen"), end_time),
                source=TelemetrySource.NETWORK,
                origin=origin,
                payload=payload.model_dump(),
                raw_message=f"Ingress summary from {category}",
                resource_id=row.get("ResourceId") or None,
                subscription_id=row.get("SubscriptionId") or AzureConfig.SUBSCRIPTION_ID,
                region=row.get("Region") or None,
                operation_name=row.get("OperationName") or category,
                correlation_id=row.get("CorrelationId") or None,
            )
            events.append(event)
        return events
