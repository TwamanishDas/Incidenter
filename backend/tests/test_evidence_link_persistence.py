import unittest
from datetime import datetime

from backend.data_store import store
from backend.models import TelemetryEvent, TelemetryOrigin, TelemetrySource
from backend.processors import analyze_telemetry, reset_repeat_incident_tracker


class EvidenceLinkPersistenceTests(unittest.TestCase):
    def setUp(self):
        reset_repeat_incident_tracker()
        store.telemetry.clear()
        store.incidents.clear()
        store.correlations.clear()
        store.evidence_records.clear()

    def test_persist_incident_evidence_populates_links(self):
        event = TelemetryEvent(
            timestamp=datetime.utcnow(),
            source=TelemetrySource.NETWORK,
            origin=TelemetryOrigin.SIMULATOR,
            resource_id="/subscriptions/sub1/resourceGroups/rg1/providers/Microsoft.Network/networkWatchers/nw1",
            operation_name="network_error_signal",
            payload={
                "packet_loss": 9.0,
                "avg_latency_ms": 310.0,
                "nsg_denied_connections": 20,
                "tcp_retry_count": 8,
                "source_ip": "10.0.0.10",
                "destination_ip": "10.0.1.20",
                "destination_port": 443,
            },
        )

        incident = analyze_telemetry(event)
        self.assertIsNotNone(incident)
        store.add_incident(incident)
        records = store.persist_incident_evidence(incident)

        self.assertGreaterEqual(len(records), 1)
        self.assertEqual(len(records), incident.evidence_count)
        self.assertEqual(len(incident.supporting_evidence_links), incident.evidence_count)
        self.assertEqual(incident.supporting_evidence_links, [item.link for item in records])

        for link in incident.supporting_evidence_links:
            evidence_id = link.split("/")[-1]
            self.assertIsNotNone(store.get_evidence_record(evidence_id))

    def test_persist_incident_evidence_is_idempotent_for_same_incident(self):
        event = TelemetryEvent(
            timestamp=datetime.utcnow(),
            source=TelemetrySource.APPLICATION,
            origin=TelemetryOrigin.SIMULATOR,
            resource_id="/subscriptions/sub1/resourceGroups/rg1/providers/Microsoft.Web/sites/orders-api",
            operation_name="app_error_signal",
            payload={
                "request_rate_per_min": 800,
                "error_rate_pct": 6.1,
                "avg_response_ms": 1400.0,
                "p95_response_ms": 2200.0,
                "status_5xx_count": 14,
                "application_name": "orders-api",
            },
        )

        incident = analyze_telemetry(event)
        self.assertIsNotNone(incident)
        store.add_incident(incident)

        first = store.persist_incident_evidence(incident)
        second = store.persist_incident_evidence(incident)

        self.assertEqual(len(first), len(second))
        self.assertEqual([item.id for item in first], [item.id for item in second])
        self.assertEqual(len(store.get_incident_evidence(incident.id)), len(first))


if __name__ == "__main__":
    unittest.main()
