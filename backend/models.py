from enum import Enum
from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field


class TelemetrySource(str, Enum):
    NETWORK = "network"
    APPLICATION = "application"
    DATABASE = "database"


class TelemetryOrigin(str, Enum):
    SIMULATOR = "simulator"
    LOG_ANALYTICS = "log_analytics"
    APP_INSIGHTS = "app_insights"
    NETWORK_WATCHER = "network_watcher"
    AZURE_MONITOR_METRICS = "azure_monitor_metrics"
    AZURE_MONITOR_DIAGNOSTICS = "azure_monitor_diagnostics"
    AZURE_ACTIVITY_LOG = "azure_activity_log"
    AZURE_RESOURCE_HEALTH = "azure_resource_health"
    AZURE_SERVICE_HEALTH = "azure_service_health"
    FRONT_DOOR_WAF = "front_door_waf"
    APP_GATEWAY_WAF = "app_gateway_waf"


class Severity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class NetworkPayload(BaseModel):
    packet_loss: float = Field(..., ge=0.0, le=100.0)
    avg_latency_ms: float = Field(..., ge=0.0)
    nsg_denied_connections: int = Field(..., ge=0)
    tcp_retry_count: int = Field(..., ge=0)
    source_ip: Optional[str] = None
    destination_ip: Optional[str] = None
    destination_port: Optional[int] = None


class ApplicationPayload(BaseModel):
    request_rate_per_min: int = Field(..., ge=0)
    error_rate_pct: float = Field(..., ge=0.0, le=100.0)
    avg_response_ms: float = Field(..., ge=0.0)
    p95_response_ms: Optional[float] = None
    status_5xx_count: int = Field(..., ge=0)
    application_name: Optional[str] = None


class DatabasePayload(BaseModel):
    connection_errors: int = Field(..., ge=0)
    timeout_count: int = Field(..., ge=0)
    deadlock_count: int = Field(..., ge=0)
    avg_query_duration_ms: float = Field(..., ge=0.0)
    database_name: Optional[str] = None
    cpu_percent: Optional[float] = None
    worker_count: Optional[int] = None


class TelemetryEvent(BaseModel):
    id: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    source: TelemetrySource
    origin: TelemetryOrigin = TelemetryOrigin.SIMULATOR
    resource_id: Optional[str] = None
    subscription_id: Optional[str] = None
    region: Optional[str] = None
    operation_name: Optional[str] = None
    correlation_id: Optional[str] = None
    payload: dict
    raw_message: Optional[str] = None


class RCALink(BaseModel):
    evidence: str
    severity: Severity


class Incident(BaseModel):
    id: str
    detected_at: datetime = Field(default_factory=datetime.utcnow)
    incident_type: TelemetrySource
    title: str
    description: str
    severity: Severity
    likely_root_cause: str
    affected_component: str
    evidence: list[RCALink]
    supporting_data: dict


class SimulationRequest(BaseModel):
    scenario: Literal["network_spike" ,"app_error" ,"db_latency"] = "network_spike"
