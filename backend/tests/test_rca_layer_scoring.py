import unittest
from datetime import datetime

from backend.models import TelemetryEvent, TelemetryOrigin, TelemetrySource
from backend.processors import analyze_telemetry


class RCALayerScoringTests(unittest.TestCase):
    def test_network_incident_contains_layer_signature_scoring(self):
        event = TelemetryEvent(
            timestamp=datetime.utcnow(),
            source=TelemetrySource.NETWORK,
            origin=TelemetryOrigin.SIMULATOR,
            payload={
                "packet_loss": 9.0,
                "avg_latency_ms": 320.0,
                "nsg_denied_connections": 42,
                "tcp_retry_count": 12,
            },
        )

        incident = analyze_telemetry(event)

        self.assertIsNotNone(incident)
        self.assertEqual(incident.severity.value, "critical")
        scoring = incident.supporting_data.get("rca_scoring", {})
        self.assertEqual(scoring.get("model_version"), "phase4-step1.1-layer-signature-v1")
        self.assertEqual(scoring.get("layer"), "network")
        self.assertEqual(scoring.get("layer_signature_score"), 1.0)
        self.assertEqual(scoring.get("matched_signal_count"), 4)
        self.assertEqual(scoring.get("top_signal"), "nsg_denied_connections")

    def test_application_warning_only_path_has_partial_score(self):
        event = TelemetryEvent(
            timestamp=datetime.utcnow(),
            source=TelemetrySource.APPLICATION,
            origin=TelemetryOrigin.SIMULATOR,
            payload={
                "request_rate_per_min": 150,
                "error_rate_pct": 1.0,
                "avg_response_ms": 1200.0,
                "p95_response_ms": 1400.0,
                "status_5xx_count": 1,
                "application_name": "checkout-api",
            },
        )

        incident = analyze_telemetry(event)

        self.assertIsNotNone(incident)
        self.assertEqual(incident.severity.value, "warning")
        scoring = incident.supporting_data.get("rca_scoring", {})
        self.assertEqual(scoring.get("layer"), "application")
        self.assertEqual(scoring.get("layer_signature_score"), 0.3)
        self.assertEqual(scoring.get("matched_signal_count"), 1)
        self.assertEqual(scoring.get("top_signal"), "avg_response_ms")

    def test_database_event_below_thresholds_returns_none(self):
        event = TelemetryEvent(
            timestamp=datetime.utcnow(),
            source=TelemetrySource.DATABASE,
            origin=TelemetryOrigin.SIMULATOR,
            payload={
                "connection_errors": 0,
                "timeout_count": 0,
                "deadlock_count": 0,
                "avg_query_duration_ms": 180.0,
                "database_name": "orders-db",
            },
        )

        incident = analyze_telemetry(event)
        self.assertIsNone(incident)


if __name__ == "__main__":
    unittest.main()
