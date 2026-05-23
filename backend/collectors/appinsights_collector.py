"""
Application Insights collector.
Queries application and dependency telemetry using LogsQueryClient.query_resource.
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
    TelemetryEvent,
    TelemetryOrigin,
    TelemetrySource,
)
from .collector_base import CollectorBase
from .kql_utils import as_float, as_int, parse_utc_timestamp, rows_as_dicts

logger = logging.getLogger(__name__)


def _to_kql_datetime(value: datetime) -> str:
    return value.strftime("%Y-%m-%dT%H:%M:%SZ")


class AppInsightsCollector(CollectorBase):
    """Collect telemetry from Application Insights resource."""

    def __init__(self, app_insights_resource_id: Optional[str] = None):
        super().__init__("AppInsightsCollector", TelemetrySource.APPLICATION)
        legacy_app_id = AzureConfig.APP_INSIGHTS_APP_ID
        self.resource_id = app_insights_resource_id or AzureConfig.APP_INSIGHTS_RESOURCE_ID
        if not self.resource_id:
            if legacy_app_id:
                logger.error(
                    "AppInsightsCollector: APP_INSIGHTS_APP_ID is deprecated and unsupported for query_resource; "
                    "set APP_INSIGHTS_RESOURCE_ID. Collector disabled."
                )
            else:
                logger.warning("AppInsightsCollector: APP_INSIGHTS_RESOURCE_ID not configured")
        elif not self._is_arm_resource_id(self.resource_id):
            logger.error(
                "AppInsightsCollector: invalid APP_INSIGHTS_RESOURCE_ID format '%s'. "
                "Expected ARM resource ID (/subscriptions/.../providers/microsoft.insights/components/...). "
                "Collector disabled.",
                self.resource_id,
            )
            self.resource_id = None

        try:
            credential = get_azure_credential()
            self.client = LogsQueryClient(credential)
        except Exception as exc:
            logger.error("AppInsightsCollector: failed to initialize client: %s", exc)
            self.client = None

    @staticmethod
    def _is_arm_resource_id(value: str) -> bool:
        return value.strip().lower().startswith("/subscriptions/")

    def collect(self) -> list[TelemetryEvent]:
        if not self.client or not self.resource_id:
            return []

        start_time, end_time = self.get_query_window()
        events: list[TelemetryEvent] = []
        events.extend(self._query_requests(start_time, end_time))
        events.extend(self._query_exceptions(start_time, end_time))
        events.extend(self._query_dependencies(start_time, end_time))
        return events

    def _query_requests(self, start_time: datetime, end_time: datetime) -> list[TelemetryEvent]:
        query = f"""
        requests
        | where timestamp between (datetime({_to_kql_datetime(start_time)}) .. datetime({_to_kql_datetime(end_time)}))
        | summarize
            TotalCount = count(),
            FailureCount = countif(success == false),
            Status5xxCount = countif(tostring(resultCode) startswith "5"),
            AvgDurationMs = avg(todouble(duration)),
            P95DurationMs = percentile(todouble(duration), 95),
            LastSeen = max(timestamp),
            CorrelationId = any(tostring(operation_Id))
          by AppName = tostring(cloud_RoleName)
        | where TotalCount > 0
        """

        events: list[TelemetryEvent] = []
        try:
            response = self.client.query_resource(self.resource_id, query, timespan=(start_time, end_time))
        except HttpResponseError as exc:
            logger.error("AppInsightsCollector: requests query failed: %s", exc)
            return events

        window_minutes = max(1, int((end_time - start_time).total_seconds() / 60))
        for row in rows_as_dicts(response):
            total_count = as_int(row.get("TotalCount"))
            if total_count <= 0:
                continue
            failures = as_int(row.get("FailureCount"))
            status_5xx = as_int(row.get("Status5xxCount"))
            error_rate = min(100.0, (failures / total_count) * 100.0)
            payload = ApplicationPayload(
                application_name=row.get("AppName") or "app-service",
                request_rate_per_min=max(1, int(total_count / window_minutes)),
                error_rate_pct=error_rate,
                avg_response_ms=max(0.0, as_float(row.get("AvgDurationMs"))),
                p95_response_ms=max(0.0, as_float(row.get("P95DurationMs"))),
                status_5xx_count=status_5xx,
            )
            events.append(
                TelemetryEvent(
                    timestamp=parse_utc_timestamp(row.get("LastSeen"), end_time),
                    source=TelemetrySource.APPLICATION,
                    origin=TelemetryOrigin.APP_INSIGHTS,
                    payload=payload.model_dump(),
                    resource_id=self.resource_id,
                    subscription_id=AzureConfig.SUBSCRIPTION_ID,
                    operation_name="AppInsightsRequestsSummary",
                    correlation_id=row.get("CorrelationId") or None,
                )
            )
        return events

    def _query_exceptions(self, start_time: datetime, end_time: datetime) -> list[TelemetryEvent]:
        query = f"""
        exceptions
        | where timestamp between (datetime({_to_kql_datetime(start_time)}) .. datetime({_to_kql_datetime(end_time)}))
        | summarize
            ExceptionCount = count(),
            LastSeen = max(timestamp),
            CorrelationId = any(tostring(operation_Id))
          by AppName = tostring(cloud_RoleName)
        | where ExceptionCount > 0
        """

        events: list[TelemetryEvent] = []
        try:
            response = self.client.query_resource(self.resource_id, query, timespan=(start_time, end_time))
        except HttpResponseError as exc:
            logger.error("AppInsightsCollector: exceptions query failed: %s", exc)
            return events

        window_minutes = max(1, int((end_time - start_time).total_seconds() / 60))
        for row in rows_as_dicts(response):
            exception_count = as_int(row.get("ExceptionCount"))
            payload = ApplicationPayload(
                application_name=(row.get("AppName") or "app-service") + "-exceptions",
                request_rate_per_min=max(1, int(exception_count / window_minutes)),
                error_rate_pct=100.0,
                avg_response_ms=0.0,
                p95_response_ms=0.0,
                status_5xx_count=exception_count,
            )
            events.append(
                TelemetryEvent(
                    timestamp=parse_utc_timestamp(row.get("LastSeen"), end_time),
                    source=TelemetrySource.APPLICATION,
                    origin=TelemetryOrigin.APP_INSIGHTS,
                    payload=payload.model_dump(),
                    resource_id=self.resource_id,
                    subscription_id=AzureConfig.SUBSCRIPTION_ID,
                    operation_name="AppInsightsExceptionsSummary",
                    correlation_id=row.get("CorrelationId") or None,
                )
            )
        return events

    def _query_dependencies(self, start_time: datetime, end_time: datetime) -> list[TelemetryEvent]:
        query = f"""
        dependencies
        | where timestamp between (datetime({_to_kql_datetime(start_time)}) .. datetime({_to_kql_datetime(end_time)}))
        | summarize
            TotalCalls = count(),
            FailureCount = countif(success == false),
            AvgDurationMs = avg(todouble(duration)),
            P95DurationMs = percentile(todouble(duration), 95),
            LastSeen = max(timestamp),
            CorrelationId = any(tostring(operation_Id))
          by DependencyType = tostring(type), Target = tostring(target)
        | where TotalCalls > 0
        """

        events: list[TelemetryEvent] = []
        try:
            response = self.client.query_resource(self.resource_id, query, timespan=(start_time, end_time))
        except HttpResponseError as exc:
            logger.error("AppInsightsCollector: dependencies query failed: %s", exc)
            return events

        window_minutes = max(1, int((end_time - start_time).total_seconds() / 60))
        for row in rows_as_dicts(response):
            dep_type = str(row.get("DependencyType") or "dependency")
            target = str(row.get("Target") or "unknown-target")
            total_calls = as_int(row.get("TotalCalls"))
            failure_count = as_int(row.get("FailureCount"))
            avg_duration = max(0.0, as_float(row.get("AvgDurationMs")))
            p95_duration = max(0.0, as_float(row.get("P95DurationMs")))

            if "sql" in dep_type.lower() or "cosmos" in dep_type.lower():
                payload = DatabasePayload(
                    database_name=target,
                    connection_errors=failure_count,
                    timeout_count=0,
                    deadlock_count=0,
                    avg_query_duration_ms=avg_duration,
                )
                source = TelemetrySource.DATABASE
            else:
                error_rate = min(100.0, (failure_count / max(1, total_calls)) * 100.0)
                payload = ApplicationPayload(
                    application_name=f"{dep_type}:{target}",
                    request_rate_per_min=max(1, int(total_calls / window_minutes)),
                    error_rate_pct=error_rate,
                    avg_response_ms=avg_duration,
                    p95_response_ms=p95_duration,
                    status_5xx_count=failure_count,
                )
                source = TelemetrySource.APPLICATION

            events.append(
                TelemetryEvent(
                    timestamp=parse_utc_timestamp(row.get("LastSeen"), end_time),
                    source=source,
                    origin=TelemetryOrigin.APP_INSIGHTS,
                    payload=payload.model_dump(),
                    resource_id=self.resource_id,
                    subscription_id=AzureConfig.SUBSCRIPTION_ID,
                    operation_name=f"AppInsightsDependency:{dep_type}",
                    correlation_id=row.get("CorrelationId") or None,
                )
            )
        return events
