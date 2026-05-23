"""
Activity and health collector.
Ingests Azure Activity Log change events plus Resource Health/Service Health signals.
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
from .kql_utils import as_int, parse_utc_timestamp, rows_as_dicts

logger = logging.getLogger(__name__)


def _to_kql_datetime(value: datetime) -> str:
    return value.strftime("%Y-%m-%dT%H:%M:%SZ")


class ActivityHealthCollector(CollectorBase):
    """Collect control-plane and health posture signals from AzureActivity."""

    def __init__(self, workspace_id: Optional[str] = None):
        super().__init__("ActivityHealthCollector", TelemetrySource.APPLICATION)
        self.workspace_id = workspace_id or AzureConfig.LOG_ANALYTICS_WORKSPACE_ID
        if not self.workspace_id:
            logger.warning("ActivityHealthCollector: LOG_ANALYTICS_WORKSPACE_ID not configured")

        try:
            credential = get_azure_credential()
            self.client = LogsQueryClient(credential)
        except Exception as exc:
            logger.error("ActivityHealthCollector: failed to initialize client: %s", exc)
            self.client = None

    def collect(self) -> list[TelemetryEvent]:
        if not self.client or not self.workspace_id:
            return []
        start_time, end_time = self.get_query_window()

        events: list[TelemetryEvent] = []
        events.extend(self._query_activity_changes(start_time, end_time))
        events.extend(self._query_resource_health(start_time, end_time))
        events.extend(self._query_service_health(start_time, end_time))
        return events

    def _query_activity_changes(self, start_time: datetime, end_time: datetime) -> list[TelemetryEvent]:
        query = f"""
        AzureActivity
        | where TimeGenerated between (datetime({_to_kql_datetime(start_time)}) .. datetime({_to_kql_datetime(end_time)}))
        | where CategoryValue in~ ("Administrative", "Policy", "Security")
        | where OperationNameValue has_any ("write", "delete", "deploy", "roleAssignments")
        | summarize
            EventCount = count(),
            FailedCount = countif(ActivityStatusValue !in~ ("Succeeded", "Success")),
            LastSeen = max(TimeGenerated),
            Region = any(tostring(ResourceLocation)),
            Provider = any(tostring(ResourceProviderValue)),
            CorrelationId = any(tostring(CorrelationId))
          by SubscriptionId = tostring(SubscriptionId), ResourceId = tostring(ResourceId), OperationName = tostring(OperationNameValue)
        | where EventCount > 0
        """

        events: list[TelemetryEvent] = []
        try:
            response = self.client.query_workspace(self.workspace_id, query, timespan=(start_time, end_time))
        except HttpResponseError as exc:
            logger.error("ActivityHealthCollector: activity query failed: %s", exc)
            return events

        for row in rows_as_dicts(response):
            source = self._infer_layer(str(row.get("Provider") or ""), str(row.get("OperationName") or ""))
            payload = self._build_change_payload(
                source=source,
                event_count=as_int(row.get("EventCount")),
                failed_count=as_int(row.get("FailedCount")),
                resource_id=str(row.get("ResourceId") or ""),
            )
            events.append(
                TelemetryEvent(
                    timestamp=parse_utc_timestamp(row.get("LastSeen"), end_time),
                    source=source,
                    origin=TelemetryOrigin.AZURE_ACTIVITY_LOG,
                    payload=payload,
                    raw_message="Azure Activity Log change event summary",
                    resource_id=row.get("ResourceId") or None,
                    subscription_id=row.get("SubscriptionId") or AzureConfig.SUBSCRIPTION_ID,
                    region=row.get("Region") or None,
                    operation_name=row.get("OperationName") or None,
                    correlation_id=row.get("CorrelationId") or None,
                )
            )
        return events

    def _query_resource_health(self, start_time: datetime, end_time: datetime) -> list[TelemetryEvent]:
        query = f"""
        AzureActivity
        | where TimeGenerated between (datetime({_to_kql_datetime(start_time)}) .. datetime({_to_kql_datetime(end_time)}))
        | where CategoryValue =~ "ResourceHealth"
        | extend ParsedProps = parse_json(Properties)
        | summarize
            EventCount = count(),
            LastSeen = max(TimeGenerated),
            HealthStatus = any(tostring(coalesce(ParsedProps.currentHealthStatus, ParsedProps.status, ActivityStatusValue))),
            Region = any(tostring(ResourceLocation)),
            Provider = any(tostring(ResourceProviderValue)),
            CorrelationId = any(tostring(CorrelationId))
          by SubscriptionId = tostring(SubscriptionId), ResourceId = tostring(ResourceId), OperationName = tostring(OperationNameValue)
        """

        events: list[TelemetryEvent] = []
        try:
            response = self.client.query_workspace(self.workspace_id, query, timespan=(start_time, end_time))
        except HttpResponseError as exc:
            logger.error("ActivityHealthCollector: resource health query failed: %s", exc)
            return events

        for row in rows_as_dicts(response):
            source = self._infer_layer(str(row.get("Provider") or ""), str(row.get("OperationName") or ""))
            payload = self._build_health_payload(
                source=source,
                resource_id=str(row.get("ResourceId") or ""),
                health_status=str(row.get("HealthStatus") or ""),
                event_count=as_int(row.get("EventCount")),
            )
            events.append(
                TelemetryEvent(
                    timestamp=parse_utc_timestamp(row.get("LastSeen"), end_time),
                    source=source,
                    origin=TelemetryOrigin.AZURE_RESOURCE_HEALTH,
                    payload=payload,
                    raw_message=f"Resource Health state: {row.get('HealthStatus') or 'unknown'}",
                    resource_id=row.get("ResourceId") or None,
                    subscription_id=row.get("SubscriptionId") or AzureConfig.SUBSCRIPTION_ID,
                    region=row.get("Region") or None,
                    operation_name=row.get("OperationName") or None,
                    correlation_id=row.get("CorrelationId") or None,
                )
            )
        return events

    def _query_service_health(self, start_time: datetime, end_time: datetime) -> list[TelemetryEvent]:
        query = f"""
        AzureActivity
        | where TimeGenerated between (datetime({_to_kql_datetime(start_time)}) .. datetime({_to_kql_datetime(end_time)}))
        | where CategoryValue =~ "ServiceHealth"
        | extend ParsedProps = parse_json(Properties)
        | summarize
            EventCount = count(),
            LastSeen = max(TimeGenerated),
            HealthStatus = any(tostring(coalesce(ParsedProps.status, ActivityStatusValue))),
            Region = any(tostring(ResourceLocation)),
            Provider = any(tostring(ResourceProviderValue)),
            CorrelationId = any(tostring(CorrelationId))
          by SubscriptionId = tostring(SubscriptionId), ResourceId = tostring(ResourceId), OperationName = tostring(OperationNameValue)
        """

        events: list[TelemetryEvent] = []
        try:
            response = self.client.query_workspace(self.workspace_id, query, timespan=(start_time, end_time))
        except HttpResponseError as exc:
            logger.error("ActivityHealthCollector: service health query failed: %s", exc)
            return events

        for row in rows_as_dicts(response):
            source = self._infer_layer(str(row.get("Provider") or ""), str(row.get("OperationName") or ""))
            payload = self._build_health_payload(
                source=source,
                resource_id=str(row.get("ResourceId") or ""),
                health_status=str(row.get("HealthStatus") or ""),
                event_count=as_int(row.get("EventCount")),
            )
            events.append(
                TelemetryEvent(
                    timestamp=parse_utc_timestamp(row.get("LastSeen"), end_time),
                    source=source,
                    origin=TelemetryOrigin.AZURE_SERVICE_HEALTH,
                    payload=payload,
                    raw_message=f"Service Health state: {row.get('HealthStatus') or 'unknown'}",
                    resource_id=row.get("ResourceId") or None,
                    subscription_id=row.get("SubscriptionId") or AzureConfig.SUBSCRIPTION_ID,
                    region=row.get("Region") or None,
                    operation_name=row.get("OperationName") or None,
                    correlation_id=row.get("CorrelationId") or None,
                )
            )
        return events

    def _infer_layer(self, provider: str, operation_name: str) -> TelemetrySource:
        value = (provider + " " + operation_name).lower()
        if "microsoft.network" in value or "nsg" in value or "gateway" in value:
            return TelemetrySource.NETWORK
        if "microsoft.sql" in value or "database" in value:
            return TelemetrySource.DATABASE
        return TelemetrySource.APPLICATION

    def _build_change_payload(
        self,
        source: TelemetrySource,
        event_count: int,
        failed_count: int,
        resource_id: str,
    ) -> dict:
        if source == TelemetrySource.NETWORK:
            payload = NetworkPayload(
                source_ip=None,
                destination_ip=None,
                destination_port=None,
                packet_loss=0.0,
                avg_latency_ms=0.0,
                nsg_denied_connections=max(0, failed_count),
                tcp_retry_count=0,
            ).model_dump()
        elif source == TelemetrySource.DATABASE:
            payload = DatabasePayload(
                database_name=resource_id.rstrip("/").split("/")[-1] if resource_id else "database",
                connection_errors=max(0, failed_count),
                timeout_count=0,
                deadlock_count=0,
                avg_query_duration_ms=0.0,
                cpu_percent=0.0,
                worker_count=0,
            ).model_dump()
        else:
            error_rate = min(100.0, (max(0, failed_count) / max(1, event_count)) * 100.0)
            payload = ApplicationPayload(
                application_name=resource_id.rstrip("/").split("/")[-1] if resource_id else "application",
                request_rate_per_min=max(1, event_count),
                error_rate_pct=error_rate,
                avg_response_ms=0.0,
                p95_response_ms=0.0,
                status_5xx_count=max(0, failed_count),
            ).model_dump()

        payload["control_plane_change_count"] = max(0, event_count)
        payload["control_plane_failed_count"] = max(0, failed_count)
        return payload

    def _build_health_payload(
        self,
        source: TelemetrySource,
        resource_id: str,
        health_status: str,
        event_count: int,
    ) -> dict:
        unhealthy = health_status.lower() not in {"available", "succeeded", "success", "healthy"}
        if source == TelemetrySource.NETWORK:
            payload = NetworkPayload(
                source_ip=None,
                destination_ip=None,
                destination_port=None,
                packet_loss=8.0 if unhealthy else 0.0,
                avg_latency_ms=250.0 if unhealthy else 0.0,
                nsg_denied_connections=1 if unhealthy else 0,
                tcp_retry_count=1 if unhealthy else 0,
            ).model_dump()
        elif source == TelemetrySource.DATABASE:
            payload = DatabasePayload(
                database_name=resource_id.rstrip("/").split("/")[-1] if resource_id else "database",
                connection_errors=5 if unhealthy else 0,
                timeout_count=3 if unhealthy else 0,
                deadlock_count=1 if unhealthy else 0,
                avg_query_duration_ms=2200.0 if unhealthy else 0.0,
                cpu_percent=90.0 if unhealthy else 0.0,
                worker_count=100 if unhealthy else 0,
            ).model_dump()
        else:
            payload = ApplicationPayload(
                application_name=resource_id.rstrip("/").split("/")[-1] if resource_id else "application",
                request_rate_per_min=max(1, event_count),
                error_rate_pct=12.0 if unhealthy else 0.0,
                avg_response_ms=1500.0 if unhealthy else 0.0,
                p95_response_ms=2500.0 if unhealthy else 0.0,
                status_5xx_count=10 if unhealthy else 0,
            ).model_dump()

        payload["health_status"] = health_status or "unknown"
        payload["health_event_count"] = max(0, event_count)
        return payload
