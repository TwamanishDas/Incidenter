import uuid
from typing import List

from .models import CorrelatedEvidence, Incident, TelemetryEvent


class InMemoryStore:
    def __init__(self) -> None:
        self.telemetry: list[TelemetryEvent] = []
        self.incidents: list[Incident] = []
        self.correlations: list[CorrelatedEvidence] = []

    def add_telemetry(self, event: TelemetryEvent) -> TelemetryEvent:
        if not event.id:
            event.id = str(uuid.uuid4())
        self.telemetry.append(event)
        return event

    def get_telemetry(self) -> list[TelemetryEvent]:
        return list(self.telemetry)

    def add_incident(self, incident: Incident) -> Incident:
        self.incidents.append(incident)
        return incident

    def get_incidents(self) -> list[Incident]:
        return list(self.incidents)

    def get_incident(self, incident_id: str) -> Incident | None:
        return next((incident for incident in self.incidents if incident.id == incident_id), None)

    def add_correlation(self, correlation: CorrelatedEvidence) -> CorrelatedEvidence:
        self.correlations.append(correlation)
        return correlation

    def get_correlations(self) -> list[CorrelatedEvidence]:
        return list(self.correlations)

    def get_correlation(self, correlation_id: str) -> CorrelatedEvidence | None:
        return next((item for item in self.correlations if item.id == correlation_id), None)


store = InMemoryStore()
