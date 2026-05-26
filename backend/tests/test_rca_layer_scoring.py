import unittest
from datetime import datetime

from backend.models import TelemetryEvent, TelemetryOrigin, TelemetrySource
from backend.processors import analyze_telemetry, reset_repeat_incident_tracker


class RCALayerScoringTests(unittest.TestCase):
    def setUp(self):
        reset_repeat_incident_tracker()

    def test_network_incident_contains_layer_signature_scoring(self):
        event = TelemetryEvent(
            timestamp=datetime.utcnow(),
            source=TelemetrySource.NETWORK,
            origin=TelemetryOrigin.SIMULATOR,
            resource_id="/subscriptions/sub1/resourceGroups/rg1/providers/Microsoft.Network/networkWatchers/nw1",
            correlation_id="corr-net-1",
            operation_name="network_flow_signal",
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
        self.assertEqual(scoring.get("model_version"), "phase4-step1.3-repeat-v1")
        self.assertEqual(scoring.get("layer"), "network")
        self.assertEqual(scoring.get("layer_signature_score"), 1.0)
        self.assertEqual(scoring.get("matched_signal_count"), 4)
        self.assertEqual(scoring.get("top_signal"), "nsg_denied_connections")
        self.assertGreaterEqual(scoring.get("dependency_relationship_score"), 0.75)
        self.assertEqual(scoring.get("estimated_blast_radius"), "high")
        self.assertEqual(scoring.get("dependency_downstream_layers"), ["application", "database"])
        self.assertEqual(scoring.get("repeat_incident_count_prior_window"), 0)
        self.assertEqual(scoring.get("is_repeat_incident"), False)
        self.assertEqual(scoring.get("repeat_weight_bonus"), 0.0)

    def test_application_warning_only_path_has_partial_score(self):
        event = TelemetryEvent(
            timestamp=datetime.utcnow(),
            source=TelemetrySource.APPLICATION,
            origin=TelemetryOrigin.SIMULATOR,
            resource_id="/subscriptions/sub1/resourceGroups/rg1/providers/Microsoft.Web/sites/checkout-api",
            operation_name="request_latency_signal",
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
        self.assertGreaterEqual(scoring.get("dependency_relationship_score"), 0.40)
        self.assertEqual(scoring.get("estimated_blast_radius"), "medium")
        self.assertEqual(scoring.get("dependency_downstream_layers"), ["database"])

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

    def test_repeat_incident_weight_increases_final_score(self):
        event = TelemetryEvent(
            timestamp=datetime.utcnow(),
            source=TelemetrySource.APPLICATION,
            origin=TelemetryOrigin.SIMULATOR,
            resource_id="/subscriptions/sub1/resourceGroups/rg1/providers/Microsoft.Web/sites/payments-api",
            operation_name="error_rate_signal",
            payload={
                "request_rate_per_min": 900,
                "error_rate_pct": 8.2,
                "avg_response_ms": 1350.0,
                "p95_response_ms": 2100.0,
                "status_5xx_count": 12,
                "application_name": "payments-api",
            },
        )

        first = analyze_telemetry(event)
        second = analyze_telemetry(event)

        self.assertIsNotNone(first)
        self.assertIsNotNone(second)
        first_scoring = first.supporting_data.get("rca_scoring", {})
        second_scoring = second.supporting_data.get("rca_scoring", {})

        self.assertEqual(first_scoring.get("repeat_incident_count_prior_window"), 0)
        self.assertEqual(second_scoring.get("repeat_incident_count_prior_window"), 1)
        self.assertEqual(second_scoring.get("is_repeat_incident"), True)
        self.assertGreater(second_scoring.get("repeat_weight_bonus"), 0.0)
        self.assertGreater(
            second_scoring.get("composite_score_final"),
            second_scoring.get("composite_score_pre_repeat"),
        )


if __name__ == "__main__":
    unittest.main()
