import uuid
from typing import List

from .models import CorrelatedEvidence, EvidenceRecord, Incident, TelemetryEvent


class InMemoryStore:
    def __init__(self) -> None:
        self.telemetry: list[TelemetryEvent] = []
        self.incidents: list[Incident] = []
        self.correlations: list[CorrelatedEvidence] = []
        self.evidence_records: list[EvidenceRecord] = []

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

    def persist_incident_evidence(self, incident: Incident) -> list[EvidenceRecord]:
        existing = [item for item in self.evidence_records if item.incident_id == incident.id]
        if existing:
            incident.supporting_evidence_links = [item.link for item in existing]
            return existing

        records: list[EvidenceRecord] = []
        for index, evidence in enumerate(incident.evidence):
            evidence_id = str(uuid.uuid4())
            link = f"/evidence/{evidence_id}"
            record = EvidenceRecord(
                id=evidence_id,
                incident_id=incident.id,
                incident_type=incident.incident_type,
                severity=evidence.severity,
                evidence_text=evidence.evidence,
                link=link,
                supporting_data={
                    "evidence_index": index,
                    "incident_signature": incident.incident_signature,
                },
            )
            self.evidence_records.append(record)
            records.append(record)

        incident.supporting_evidence_links = [item.link for item in records]
        return records

    def get_evidence_records(self) -> list[EvidenceRecord]:
        return list(self.evidence_records)

    def get_evidence_record(self, evidence_id: str) -> EvidenceRecord | None:
        return next((item for item in self.evidence_records if item.id == evidence_id), None)

    def get_incident_evidence(self, incident_id: str) -> list[EvidenceRecord]:
        return [item for item in self.evidence_records if item.incident_id == incident_id]

    def add_correlation(self, correlation: CorrelatedEvidence) -> CorrelatedEvidence:
        self.correlations.append(correlation)
        return correlation

    def get_correlations(self) -> list[CorrelatedEvidence]:
        return list(self.correlations)

    def get_correlation(self, correlation_id: str) -> CorrelatedEvidence | None:
        return next((item for item in self.correlations if item.id == correlation_id), None)


store = InMemoryStore()
