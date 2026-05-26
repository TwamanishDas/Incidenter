import unittest
from datetime import datetime

from backend.models import TelemetryEvent, TelemetryOrigin, TelemetrySource
from backend.processors import analyze_telemetry, reset_repeat_incident_tracker


class IncidentOutputContractTests(unittest.TestCase):
    def setUp(self):
        reset_repeat_incident_tracker()

    def test_incident_contract_fields_exist_and_are_consistent(self):
        event = TelemetryEvent(
            timestamp=datetime.utcnow(),
            source=TelemetrySource.DATABASE,
            origin=TelemetryOrigin.SIMULATOR,
            resource_id="/subscriptions/sub1/resourceGroups/rg1/providers/Microsoft.Sql/servers/sql1/databases/orders-db",
            operation_name="db_health_signal",
            payload={
                "connection_errors": 9,
                "timeout_count": 4,
                "deadlock_count": 1,
                "avg_query_duration_ms": 2700.0,
                "database_name": "orders-db",
            },
        )

        incident = analyze_telemetry(event)

        self.assertIsNotNone(incident)
        self.assertIn(incident.confidence_label, ["low", "medium", "high"])
        self.assertGreaterEqual(incident.probability_score, 0.0)
        self.assertLessEqual(incident.probability_score, 1.0)
        self.assertTrue(incident.incident_signature)
        self.assertTrue(incident.scoring_model_version)
        self.assertGreaterEqual(incident.evidence_count, 1)
        self.assertEqual(incident.evidence_count, len(incident.supporting_evidence))
        self.assertEqual(incident.primary_evidence, incident.supporting_evidence[0])
        self.assertEqual(incident.scoring_model_version, "phase4-step1.3-repeat-v1")

        scoring = incident.supporting_data.get("rca_scoring", {})
        self.assertEqual(incident.probability_score, scoring.get("composite_score_final"))
        self.assertEqual(incident.incident_signature, scoring.get("incident_signature"))


if __name__ == "__main__":
    unittest.main()
