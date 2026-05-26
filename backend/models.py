from enum import Enum
from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field, model_validator


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


class TelemetryRecordType(str, Enum):
    LOG = "log"
    METRIC = "metric"
    EVENT = "event"
    AUDIT = "audit"
    TRACE = "trace"


class TelemetrySchemaType(str, Enum):
    STANDARD = "standard"
    CUSTOM = "custom"
    VENDOR = "vendor"


class TelemetryEnvironment(str, Enum):
    PROD = "prod"
    STAGING = "staging"
    DEV = "dev"


_DEFAULT_SOURCE_SYSTEM_BY_ORIGIN = {
    TelemetryOrigin.SIMULATOR: "Simulator",
    TelemetryOrigin.LOG_ANALYTICS: "Azure Log Analytics",
    TelemetryOrigin.APP_INSIGHTS: "Application Insights",
    TelemetryOrigin.NETWORK_WATCHER: "Azure Network Watcher",
    TelemetryOrigin.AZURE_MONITOR_METRICS: "Azure Monitor Metrics",
    TelemetryOrigin.AZURE_MONITOR_DIAGNOSTICS: "Azure Monitor Diagnostics",
    TelemetryOrigin.AZURE_ACTIVITY_LOG: "Azure Activity Log",
    TelemetryOrigin.AZURE_RESOURCE_HEALTH: "Azure Resource Health",
    TelemetryOrigin.AZURE_SERVICE_HEALTH: "Azure Service Health",
    TelemetryOrigin.FRONT_DOOR_WAF: "Azure Front Door WAF",
    TelemetryOrigin.APP_GATEWAY_WAF: "Application Gateway WAF",
}


_DEFAULT_COLLECTION_CHANNEL_BY_ORIGIN = {
    TelemetryOrigin.SIMULATOR: "internal_simulator",
    TelemetryOrigin.LOG_ANALYTICS: "Log Analytics Query API",
    TelemetryOrigin.APP_INSIGHTS: "Application Insights Query API",
    TelemetryOrigin.NETWORK_WATCHER: "Log Analytics Query API",
    TelemetryOrigin.AZURE_MONITOR_METRICS: "Azure Monitor Metrics API",
    TelemetryOrigin.AZURE_MONITOR_DIAGNOSTICS: "Log Analytics Query API",
    TelemetryOrigin.AZURE_ACTIVITY_LOG: "Log Analytics Query API",
    TelemetryOrigin.AZURE_RESOURCE_HEALTH: "Log Analytics Query API",
    TelemetryOrigin.AZURE_SERVICE_HEALTH: "Log Analytics Query API",
    TelemetryOrigin.FRONT_DOOR_WAF: "Log Analytics Query API",
    TelemetryOrigin.APP_GATEWAY_WAF: "Log Analytics Query API",
}


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
    source_system: Optional[str] = None
    source_category: Optional[str] = None
    record_type: TelemetryRecordType = TelemetryRecordType.METRIC
    schema_type: TelemetrySchemaType = TelemetrySchemaType.STANDARD
    collection_channel: Optional[str] = None
    ingestion_timestamp: datetime = Field(default_factory=datetime.utcnow)
    resource_id: Optional[str] = None
    subscription_id: Optional[str] = None
    region: Optional[str] = None
    environment: TelemetryEnvironment = TelemetryEnvironment.PROD
    operation_name: Optional[str] = None
    correlation_id: Optional[str] = None
    fields: list[str] = Field(default_factory=list)
    payload: dict
    raw: dict = Field(default_factory=dict)
    parser_version: Optional[str] = None
    raw_message: Optional[str] = None

    @model_validator(mode="after")
    def _apply_schema_rules(self) -> "TelemetryEvent":
        if not self.source_system:
            self.source_system = _DEFAULT_SOURCE_SYSTEM_BY_ORIGIN.get(self.origin, "Unknown Source")
        if not self.source_category:
            self.source_category = self.source.value
        if not self.collection_channel:
            self.collection_channel = _DEFAULT_COLLECTION_CHANNEL_BY_ORIGIN.get(self.origin, "internal")
        if not self.fields:
            self.fields = sorted(str(key) for key in self.payload.keys())

        if self.schema_type == TelemetrySchemaType.CUSTOM:
            if not self.raw:
                self.raw = dict(self.payload)
            return self

        if self.schema_type == TelemetrySchemaType.VENDOR:
            if not self.parser_version:
                raise ValueError("parser_version is required when schema_type is 'vendor'")
            if not self.raw:
                self.raw = dict(self.payload)
        return self


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


class CorrelatedEvidence(BaseModel):
    id: str
    correlated_at: datetime = Field(default_factory=datetime.utcnow)
    join_key: str
    window_start: datetime
    window_end: datetime
    source_types: list[TelemetrySource]
    event_ids: list[str]
    resource_ids: list[str] = Field(default_factory=list)
    correlation_ids: list[str] = Field(default_factory=list)
    confidence_score: float = Field(..., ge=0.0, le=1.0)
    summary: str
    supporting_data: dict = Field(default_factory=dict)


class SimulationRequest(BaseModel):
    scenario: Literal["network_spike" ,"app_error" ,"db_latency"] = "network_spike"
