"""
Azure Network Watcher collector.
Ingests NSG denials, network performance, and TCP retry signals from Log Analytics.
"""

from datetime import datetime
from typing import Optional
import logging

from azure.core.exceptions import HttpResponseError
from azure.monitor.query import LogsQueryClient

from ..azure_config import AzureConfig, get_azure_credential
from ..models import NetworkPayload, TelemetryEvent, TelemetryOrigin, TelemetrySource
from .collector_base import CollectorBase
from .kql_utils import as_float, as_int, parse_utc_timestamp, rows_as_dicts

logger = logging.getLogger(__name__)


def _to_kql_datetime(value: datetime) -> str:
    return value.strftime("%Y-%m-%dT%H:%M:%SZ")


class NetworkWatcherCollector(CollectorBase):
    """Collect network-layer telemetry from Network Watcher logs."""

    def __init__(self, workspace_id: Optional[str] = None):
        super().__init__("NetworkWatcherCollector", TelemetrySource.NETWORK)
        self.workspace_id = workspace_id or AzureConfig.LOG_ANALYTICS_WORKSPACE_ID
        if not self.workspace_id:
            logger.warning("NetworkWatcherCollector: LOG_ANALYTICS_WORKSPACE_ID not configured")

        try:
            credential = get_azure_credential()
            self.client = LogsQueryClient(credential)
        except Exception as exc:
            logger.error("NetworkWatcherCollector: failed to initialize client: %s", exc)
            self.client = None

    def collect(self) -> list[TelemetryEvent]:
        if not self.client or not self.workspace_id:
            return []

        start_time, end_time = self.get_query_window()
        events: list[TelemetryEvent] = []
        events.extend(self._query_nsg_denials(start_time, end_time))
        events.extend(self._query_network_performance(start_time, end_time))
        events.extend(self._query_tcp_retries(start_time, end_time))
        return events

    def _query_nsg_denials(self, start_time: datetime, end_time: datetime) -> list[TelemetryEvent]:
        query = f"""
        AzureNetworkAnalytics_CL
        | where TimeGenerated between (datetime({_to_kql_datetime(start_time)}) .. datetime({_to_kql_datetime(end_time)}))
        | where FlowStatus_s == "D"
        | summarize
            DeniedCount = count(),
            LastSeen = max(TimeGenerated),
            CorrelationId = any(tostring(correlationId_g))
          by SourceIp = tostring(SrcIP_s), DestinationIp = tostring(DestIP_s), DestPort = toint(DestPort_d)
        | where DeniedCount > 0
        """

        events: list[TelemetryEvent] = []
        try:
            response = self.client.query_workspace(self.workspace_id, query, timespan=(start_time, end_time))
        except HttpResponseError as exc:
            logger.error("NetworkWatcherCollector: NSG denials query failed: %s", exc)
            return events

        for row in rows_as_dicts(response):
            payload = NetworkPayload(
                source_ip=row.get("SourceIp") or None,
                destination_ip=row.get("DestinationIp") or None,
                destination_port=as_int(row.get("DestPort"), default=0) or None,
                nsg_denied_connections=as_int(row.get("DeniedCount")),
                packet_loss=0.0,
                avg_latency_ms=0.0,
                tcp_retry_count=0,
            )
            events.append(
                TelemetryEvent(
                    timestamp=parse_utc_timestamp(row.get("LastSeen"), end_time),
                    source=TelemetrySource.NETWORK,
                    origin=TelemetryOrigin.NETWORK_WATCHER,
                    payload=payload.model_dump(),
                    raw_message="NSG denied connections detected",
                    resource_id=None,
                    subscription_id=AzureConfig.SUBSCRIPTION_ID,
                    operation_name="NetworkWatcherNSGFlowSummary",
                    correlation_id=row.get("CorrelationId") or None,
                )
            )
        return events

    def _query_network_performance(self, start_time: datetime, end_time: datetime) -> list[TelemetryEvent]:
        query = f"""
        NetworkMonitoring_Perf_CL
        | where TimeGenerated between (datetime({_to_kql_datetime(start_time)}) .. datetime({_to_kql_datetime(end_time)}))
        | summarize
            AvgLatency = avg(toreal(Latency_d)),
            PacketLoss = avg(toreal(PacketLoss_d)),
            LastSeen = max(TimeGenerated),
            CorrelationId = any(tostring(correlationId_g))
          by Source = tostring(SrcIP_s), Destination = tostring(DestIP_s)
        | where AvgLatency > 0 or PacketLoss > 0
        """

        events: list[TelemetryEvent] = []
        try:
            response = self.client.query_workspace(self.workspace_id, query, timespan=(start_time, end_time))
        except HttpResponseError as exc:
            logger.error("NetworkWatcherCollector: performance query failed: %s", exc)
            return events

        for row in rows_as_dicts(response):
            payload = NetworkPayload(
                source_ip=row.get("Source") or None,
                destination_ip=row.get("Destination") or None,
                destination_port=None,
                nsg_denied_connections=0,
                packet_loss=max(0.0, as_float(row.get("PacketLoss"))),
                avg_latency_ms=max(0.0, as_float(row.get("AvgLatency"))),
                tcp_retry_count=0,
            )
            events.append(
                TelemetryEvent(
                    timestamp=parse_utc_timestamp(row.get("LastSeen"), end_time),
                    source=TelemetrySource.NETWORK,
                    origin=TelemetryOrigin.NETWORK_WATCHER,
                    payload=payload.model_dump(),
                    raw_message="Network performance degradation signal",
                    resource_id=None,
                    subscription_id=AzureConfig.SUBSCRIPTION_ID,
                    operation_name="NetworkWatcherPerformanceSummary",
                    correlation_id=row.get("CorrelationId") or None,
                )
            )
        return events

    def _query_tcp_retries(self, start_time: datetime, end_time: datetime) -> list[TelemetryEvent]:
        query = f"""
        Syslog
        | where TimeGenerated between (datetime({_to_kql_datetime(start_time)}) .. datetime({_to_kql_datetime(end_time)}))
        | where ProcessName == "kernel" and (SyslogMessage contains "TCP" or SyslogMessage contains "retransmit")
        | summarize RetryCount = count(), LastSeen = max(TimeGenerated) by Host = tostring(Computer)
        | where RetryCount > 0
        """

        events: list[TelemetryEvent] = []
        try:
            response = self.client.query_workspace(self.workspace_id, query, timespan=(start_time, end_time))
        except HttpResponseError as exc:
            logger.error("NetworkWatcherCollector: TCP retries query failed: %s", exc)
            return events

        for row in rows_as_dicts(response):
            payload = NetworkPayload(
                source_ip=row.get("Host") or None,
                destination_ip=None,
                destination_port=None,
                nsg_denied_connections=0,
                packet_loss=0.0,
                avg_latency_ms=0.0,
                tcp_retry_count=as_int(row.get("RetryCount")),
            )
            events.append(
                TelemetryEvent(
                    timestamp=parse_utc_timestamp(row.get("LastSeen"), end_time),
                    source=TelemetrySource.NETWORK,
                    origin=TelemetryOrigin.NETWORK_WATCHER,
                    payload=payload.model_dump(),
                    raw_message=f"TCP retry/retransmit spikes on {row.get('Host') or 'host'}",
                    resource_id=None,
                    subscription_id=AzureConfig.SUBSCRIPTION_ID,
                    operation_name="NetworkWatcherTCPRetrySummary",
                )
            )
        return events
