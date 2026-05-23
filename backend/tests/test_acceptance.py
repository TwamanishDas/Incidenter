import unittest

from backend.acceptance import evaluate_ingestion_acceptance


class AcceptanceEvaluationTests(unittest.TestCase):
    def test_acceptance_passes_with_expected_healthy_state(self):
        scheduler_status = {
            "is_running": True,
            "collection_count": 2,
            "collectors": [
                {"name": "BlobSampleLogAnalyticsCollector", "status": "healthy"},
                {"name": "BlobSampleAppInsightsCollector", "status": "healthy"},
                {"name": "BlobSampleNetworkWatcherCollector", "status": "healthy"},
                {"name": "BlobSampleMonitorMetricsCollector", "status": "healthy"},
                {"name": "BlobSampleActivityHealthCollector", "status": "healthy"},
            ],
        }
        checklist = {"overall_status": "pass"}

        result = evaluate_ingestion_acceptance(scheduler_status, checklist, incidents_count=2)

        self.assertTrue(result["overall_passed"])
        self.assertEqual(result["summary"]["criteria_failed"], 0)

    def test_acceptance_fails_when_core_criteria_are_not_met(self):
        scheduler_status = {
            "is_running": False,
            "collection_count": 0,
            "collectors": [
                {"name": "BlobSampleLogAnalyticsCollector", "status": "error"},
            ],
        }
        checklist = {"overall_status": "fail"}

        result = evaluate_ingestion_acceptance(scheduler_status, checklist, incidents_count=0)

        self.assertFalse(result["overall_passed"])
        self.assertGreaterEqual(result["summary"]["criteria_failed"], 4)


if __name__ == "__main__":
    unittest.main()

