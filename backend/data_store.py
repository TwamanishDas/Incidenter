import uuid
from typing import List

from .models import Incident, TelemetryEvent


class InMemoryStore:
    def __init__(self) -> None:
        self.telemetry: list[TelemetryEvent] = []
        self.incidents: list[Incident] = []

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


store = InMemoryStore()
