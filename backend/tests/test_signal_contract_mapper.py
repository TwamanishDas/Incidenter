import unittest

from backend.models import TelemetryOrigin, TelemetrySource
from backend.signal_contract_mapper import map_signal_row_to_telemetry_event


class SignalContractMapperTests(unittest.TestCase):
    def test_maps_failed_request_rate_row_to_application_event(self):
        row = {
            "TimeGenerated": "2026-05-26T05:00:00Z",
            "AppName": "checkout-api",
            "TotalRequests": 120,
            "FailedRequests": 10,
            "Status5xx": 8,
            "FailureRatePct": 8.33,
            "ResourceId": "/subscriptions/sub1/resourceGroups/rg1/providers/Microsoft.Web/sites/checkout-api",
        }
        event = map_signal_row_to_telemetry_event("failed_request_rate", row, default_subscription_id="sub1")
        self.assertEqual(event.source, TelemetrySource.APPLICATION)
        self.assertEqual(event.origin, TelemetryOrigin.LOG_ANALYTICS)
        self.assertEqual(event.payload["status_5xx_count"], 8)
        self.assertEqual(event.payload["request_rate_per_min"], 120)

    def test_maps_sql_row_to_database_event(self):
        row = {
            "TimeGenerated": "2026-05-26T05:00:00Z",
            "DatabaseName": "orders-db",
            "ConnectivityErrors": 7,
            "TimeoutCount": 4,
            "DeadlockCount": 1,
            "ConnectivityErrorRatePct": 35.0,
            "ResourceId": "/subscriptions/sub1/resourceGroups/rg1/providers/Microsoft.Sql/servers/sql1/databases/orders-db",
        }
        event = map_signal_row_to_telemetry_event("sql_connectivity_errors", row, default_subscription_id="sub1")
        self.assertEqual(event.source, TelemetrySource.DATABASE)
        self.assertEqual(event.origin, TelemetryOrigin.AZURE_MONITOR_DIAGNOSTICS)
        self.assertEqual(event.payload["timeout_count"], 4)
        self.assertEqual(event.payload["connection_errors"], 7)

    def test_rejects_unsupported_query_id(self):
        with self.assertRaises(ValueError):
            map_signal_row_to_telemetry_event("unsupported_query", {"TimeGenerated": "2026-05-26T05:00:00Z"})


if __name__ == "__main__":
    unittest.main()

