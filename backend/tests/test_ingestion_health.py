import unittest
from datetime import datetime, timedelta

from backend import app as app_module
from backend.ingestion_health import build_ingestion_checklist


class _DummyScheduler:
    def __init__(self, status):
        self._status = status

    def get_status(self):
        return self._status


class IngestionHealthTests(unittest.TestCase):
    def test_build_checklist_marks_pass_for_healthy_sample_replay(self):
        now = datetime(2026, 5, 22, 10, 0, 0)
        recent = (now - timedelta(seconds=15)).isoformat()
        scheduler_status = {
            "is_running": True,
            "interval_seconds": 10,
            "collection_count": 2,
            "total_events_collected": 10,
            "total_events_posted": 5,
            "total_events_deduped": 5,
            "dedup_cache_size": 5,
            "last_collection_time": recent,
            "collectors": [
                {
                    "name": "BlobSampleLogAnalyticsCollector",
                    "source": "application",
                    "status": "healthy",
                    "last_error": None,
                    "last_collection_time": recent,
                    "events_collected": 2,
                },
                {
                    "name": "BlobSampleAppInsightsCollector",
                    "source": "application",
                    "status": "healthy",
                    "last_error": None,
                    "last_collection_time": recent,
                    "events_collected": 2,
                },
                {
                    "name": "BlobSampleNetworkWatcherCollector",
                    "source": "network",
                    "status": "healthy",
                    "last_error": None,
                    "last_collection_time": recent,
                    "events_collected": 2,
                },
            ],
        }

        checklist = build_ingestion_checklist(scheduler_status, now_utc=now)
        self.assertEqual(checklist["overall_status"], "pass")
        self.assertEqual(checklist["ingestion_mode"], "sample_blob")
        self.assertEqual(checklist["summary"]["checks_failed"], 0)
        self.assertEqual(checklist["summary"]["checks_warned"], 0)

    def test_build_checklist_marks_fail_for_non_running_and_errors(self):
        now = datetime(2026, 5, 22, 10, 0, 0)
        stale = (now - timedelta(minutes=20)).isoformat()
        scheduler_status = {
            "is_running": False,
            "interval_seconds": 10,
            "collection_count": 3,
            "total_events_collected": 4,
            "total_events_posted": 0,
            "total_events_deduped": 0,
            "dedup_cache_size": 0,
            "last_collection_time": stale,
            "collectors": [
                {
                    "name": "BlobSampleLogAnalyticsCollector",
                    "source": "application",
                    "status": "error",
                    "last_error": "list failed",
                    "last_collection_time": stale,
                    "events_collected": 0,
                }
            ],
        }

        checklist = build_ingestion_checklist(scheduler_status, now_utc=now)
        self.assertEqual(checklist["overall_status"], "fail")
        self.assertGreaterEqual(checklist["summary"]["checks_failed"], 2)
        self.assertIn("BlobSampleLogAnalyticsCollector", checklist["collector_overview"]["stale_collectors"])

    def test_ingestion_checklist_endpoint_returns_503_when_scheduler_not_initialized(self):
        old_scheduler = app_module.scheduler
        try:
            app_module.scheduler = None
            response = app_module.ingestion_checklist()
        finally:
            app_module.scheduler = old_scheduler

        self.assertEqual(response.status_code, 503)
        body = response.body.decode("utf-8")
        self.assertIn('"overall_status":"fail"', body)

    def test_ingestion_checklist_endpoint_returns_200_for_warn_state(self):
        now = datetime(2026, 5, 22, 10, 0, 0)
        recent = (now - timedelta(seconds=20)).isoformat()
        status = {
            "is_running": True,
            "interval_seconds": 10,
            "collection_count": 1,
            "total_events_collected": 0,
            "total_events_posted": 0,
            "total_events_deduped": 0,
            "dedup_cache_size": 0,
            "last_collection_time": recent,
            "collectors": [
                {
                    "name": "BlobSampleLogAnalyticsCollector",
                    "source": "application",
                    "status": "healthy",
                    "last_error": None,
                    "last_collection_time": recent,
                    "events_collected": 0,
                }
            ],
        }

        old_scheduler = app_module.scheduler
        try:
            app_module.scheduler = _DummyScheduler(status)
            response = app_module.ingestion_checklist()
        finally:
            app_module.scheduler = old_scheduler

        self.assertEqual(response.status_code, 200)
        body = response.body.decode("utf-8")
        self.assertIn('"overall_status":"warn"', body)


if __name__ == "__main__":
    unittest.main()

