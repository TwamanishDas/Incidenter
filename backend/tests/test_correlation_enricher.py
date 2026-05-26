import unittest
from datetime import datetime, timedelta

from backend.correlation_enricher import CorrelationEnricher
from backend.models import TelemetryEvent, TelemetryOrigin, TelemetrySource


class CorrelationEnricherTests(unittest.TestCase):
    def _app_event(self, timestamp: datetime, resource_id: str, correlation_id: str | None = None):
        return TelemetryEvent(
            timestamp=timestamp,
            source=TelemetrySource.APPLICATION,
            origin=TelemetryOrigin.LOG_ANALYTICS,
            resource_id=resource_id,
            correlation_id=correlation_id,
            operation_name="app_signal",
            payload={
                "application_name": "orders-api",
                "request_rate_per_min": 100,
                "error_rate_pct": 7.5,
                "avg_response_ms": 1200,
                "p95_response_ms": 2100,
                "status_5xx_count": 11,
            },
        )

    def _db_event(self, timestamp: datetime, resource_id: str, correlation_id: str | None = None):
        return TelemetryEvent(
            timestamp=timestamp,
            source=TelemetrySource.DATABASE,
            origin=TelemetryOrigin.AZURE_MONITOR_DIAGNOSTICS,
            resource_id=resource_id,
            correlation_id=correlation_id,
            operation_name="db_signal",
            payload={
                "database_name": "orders-db",
                "connection_errors": 6,
                "timeout_count": 4,
                "deadlock_count": 1,
                "avg_query_duration_ms": 1800,
            },
        )

    def test_builds_correlation_for_multi_source_same_resource(self):
        enricher = CorrelationEnricher(window_minutes=15)
        now = datetime.utcnow()
        app_event = self._app_event(now, "/subscriptions/s1/resourceGroups/rg/providers/Microsoft.Web/sites/app1")
        db_event = self._db_event(now + timedelta(minutes=1), "/subscriptions/s1/resourceGroups/rg/providers/Microsoft.Web/sites/app1")

        first = enricher.ingest(app_event)
        second = enricher.ingest(db_event)

        self.assertIsNone(first)
        self.assertIsNotNone(second)
        self.assertGreaterEqual(second.confidence_score, 0.5)
        self.assertEqual(len(second.source_types), 2)

    def test_does_not_correlate_without_shared_keys(self):
        enricher = CorrelationEnricher(window_minutes=15)
        now = datetime.utcnow()
        app_event = self._app_event(now, "/subscriptions/s1/resourceGroups/rg/providers/Microsoft.Web/sites/app1")
        db_event = self._db_event(now + timedelta(minutes=1), "/subscriptions/s1/resourceGroups/rg/providers/Microsoft.Sql/servers/s1/databases/db1")

        enricher.ingest(app_event)
        correlation = enricher.ingest(db_event)

        self.assertIsNone(correlation)

    def test_correlates_using_correlation_id_across_resources(self):
        enricher = CorrelationEnricher(window_minutes=15)
        now = datetime.utcnow()
        app_event = self._app_event(
            now,
            "/subscriptions/s1/resourceGroups/rg/providers/Microsoft.Web/sites/app1",
            correlation_id="corr-123",
        )
        db_event = self._db_event(
            now + timedelta(minutes=2),
            "/subscriptions/s1/resourceGroups/rg/providers/Microsoft.Sql/servers/sql1/databases/db1",
            correlation_id="corr-123",
        )

        enricher.ingest(app_event)
        correlation = enricher.ingest(db_event)

        self.assertIsNotNone(correlation)
        self.assertIn("cid:corr-123", correlation.join_key)


if __name__ == "__main__":
    unittest.main()

