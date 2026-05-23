import unittest
from datetime import datetime, timedelta
from unittest.mock import patch

from backend.collectors.monitor_metrics_collector import MonitorMetricsCollector


class MonitorMetricsCollectorRoutingTests(unittest.TestCase):
    def test_collect_routes_supported_resource_types(self):
        resources = [
            "/subscriptions/sub1/resourceGroups/rg1/providers/Microsoft.Sql/servers/sql1/databases/db1",
            "/subscriptions/sub1/resourceGroups/rg1/providers/Microsoft.Compute/virtualMachines/vm1",
            "/subscriptions/sub1/resourceGroups/rg1/providers/Microsoft.Web/sites/app1",
            "/subscriptions/sub1/resourceGroups/rg1/providers/Microsoft.Network/azureFirewalls/fw1",
            "/subscriptions/sub1/resourceGroups/rg1/providers/Microsoft.DocumentDB/databaseAccounts/cosmos1",
            "/subscriptions/sub1/resourceGroups/rg1/providers/Microsoft.Cache/redis/redis1",
            "/subscriptions/sub1/resourceGroups/rg1/providers/Microsoft.Storage/storageAccounts/sa1",
        ]
        collector = MonitorMetricsCollector(resource_ids=resources)
        collector.metrics_client = object()
        collector.logs_client = object()
        start_time = datetime.utcnow() - timedelta(minutes=5)
        end_time = datetime.utcnow()

        sql_event = object()
        vm_event = object()
        app_event = object()
        firewall_event = object()
        cosmos_event = object()
        redis_event = object()

        with (
            patch.object(collector, "get_query_window", return_value=(start_time, end_time)),
            patch.object(collector, "_query_sql_metrics", return_value=sql_event) as sql_patch,
            patch.object(collector, "_query_vm_metrics", return_value=vm_event) as vm_patch,
            patch.object(collector, "_query_app_service_metrics", return_value=app_event) as app_patch,
            patch.object(collector, "_query_azure_firewall_metrics", return_value=firewall_event) as fw_patch,
            patch.object(collector, "_query_cosmos_metrics", return_value=cosmos_event) as cosmos_patch,
            patch.object(collector, "_query_redis_metrics", return_value=redis_event) as redis_patch,
        ):
            events = collector.collect()

        self.assertEqual(events, [sql_event, vm_event, app_event, firewall_event, cosmos_event, redis_event])
        sql_patch.assert_called_once()
        vm_patch.assert_called_once()
        app_patch.assert_called_once()
        fw_patch.assert_called_once()
        cosmos_patch.assert_called_once()
        redis_patch.assert_called_once()


if __name__ == "__main__":
    unittest.main()
