import unittest
from unittest.mock import patch

from backend.azure_config import AzureConfig
from backend.azure_scheduler import telemetry_scheduler as scheduler_module


class _DummyBlobCollector:
    def __init__(self, name, source, source_folder):
        self.name = name
        self.source = source
        self.source_folder = source_folder

    def get_status(self):
        return {"name": self.name, "source": self.source.value, "status": "healthy"}


def _named_collector_class(collector_name: str):
    class _NamedCollector:
        def __init__(self):
            self.name = collector_name

        def get_status(self):
            return {"name": self.name, "source": "application", "status": "healthy"}

    _NamedCollector.__name__ = f"{collector_name}Factory"
    return _NamedCollector


class SchedulerSwitchBehaviorTests(unittest.TestCase):
    def setUp(self):
        scheduler_module.stop_scheduler(reset=True)

    def tearDown(self):
        scheduler_module.stop_scheduler(reset=True)

    def test_mode_change_requires_scheduler_reset(self):
        log_cls = _named_collector_class("LogAnalyticsCollector")
        app_cls = _named_collector_class("AppInsightsCollector")
        net_cls = _named_collector_class("NetworkWatcherCollector")
        mon_cls = _named_collector_class("MonitorMetricsCollector")
        act_cls = _named_collector_class("ActivityHealthCollector")

        with (
            patch.object(AzureConfig, "INGESTION_MODE", "sample_blob"),
            patch.object(scheduler_module, "BlobSampleCollector", _DummyBlobCollector),
        ):
            first_scheduler = scheduler_module.get_scheduler(api_base_url="http://localhost:8000")
            first_names = [collector.name for collector in first_scheduler.collectors]
            self.assertIn("BlobSampleLogAnalyticsCollector", first_names)
            self.assertIn("BlobSampleAppInsightsCollector", first_names)

        with (
            patch.object(AzureConfig, "INGESTION_MODE", "live"),
            patch.multiple(
                scheduler_module,
                LogAnalyticsCollector=log_cls,
                AppInsightsCollector=app_cls,
                NetworkWatcherCollector=net_cls,
                MonitorMetricsCollector=mon_cls,
                ActivityHealthCollector=act_cls,
            ),
        ):
            same_scheduler = scheduler_module.get_scheduler(api_base_url="http://localhost:8000")
            self.assertIs(same_scheduler, first_scheduler)
            same_names = [collector.name for collector in same_scheduler.collectors]
            self.assertIn("BlobSampleLogAnalyticsCollector", same_names)
            self.assertNotIn("LogAnalyticsCollector", same_names)

            scheduler_module.stop_scheduler(reset=True)
            replaced_scheduler = scheduler_module.get_scheduler(api_base_url="http://localhost:8000")
            replaced_names = [collector.name for collector in replaced_scheduler.collectors]
            self.assertEqual(
                replaced_names,
                [
                    "LogAnalyticsCollector",
                    "AppInsightsCollector",
                    "NetworkWatcherCollector",
                    "MonitorMetricsCollector",
                    "ActivityHealthCollector",
                ],
            )


if __name__ == "__main__":
    unittest.main()

