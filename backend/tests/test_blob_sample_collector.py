import unittest
from unittest.mock import Mock, patch

from backend.azure_config import AzureConfig
from backend.models import TelemetrySource
from backend.replay.blob_sample_collector import BlobSampleCollector


def _mock_response(status_code: int, text: str = "", raise_for_status_error: Exception | None = None) -> Mock:
    response = Mock()
    response.status_code = status_code
    response.text = text
    if raise_for_status_error is None:
        response.raise_for_status.return_value = None
    else:
        response.raise_for_status.side_effect = raise_for_status_error
    return response


class BlobSampleCollectorTests(unittest.TestCase):
    def test_collect_parses_latest_blob_and_updates_diagnostics(self):
        list_xml = """
        <EnumerationResults>
          <Blobs>
            <Blob><Name>v1/log_analytics/2026/05/20/batch-001.jsonl</Name></Blob>
            <Blob><Name>v1/log_analytics/2026/05/21/batch-002.jsonl</Name></Blob>
          </Blobs>
        </EnumerationResults>
        """
        blob_text = (
            '{"timestamp":"2026-05-21T18:00:00Z","source":"application",'
            '"origin":"log_analytics","payload":{"sample":"ok"}}'
        )

        with patch.multiple(
            AzureConfig,
            SAMPLE_BLOB_SAS_URL="https://example.blob.core.windows.net/?sv=test&sig=test",
            SAMPLE_BLOB_CONTAINER="rca-sample-ingestion",
            SAMPLE_BLOB_PREFIX="v1",
            SAMPLE_REPLAY_REBASE_TIMESTAMPS=False,
        ):
            collector = BlobSampleCollector(
                name="BlobSampleLogAnalyticsCollector",
                source=TelemetrySource.APPLICATION,
                source_folder="log_analytics",
            )
            with patch(
                "backend.replay.blob_sample_collector.requests.get",
                side_effect=[
                    _mock_response(200, list_xml),
                    _mock_response(200, blob_text),
                ],
            ):
                events = collector.safe_collect()

        self.assertEqual(len(events), 1)
        status = collector.get_status()
        self.assertEqual(status["last_blob_name"], "v1/log_analytics/2026/05/21/batch-002.jsonl")
        self.assertEqual(status["last_blob_candidate_count"], 2)
        self.assertEqual(status["last_blob_list_status_code"], 200)
        self.assertEqual(status["last_blob_download_status_code"], 200)
        self.assertEqual(status["last_blob_records_parsed"], 1)
        self.assertEqual(status["last_replay_outcome"], "processed")
        self.assertIsNone(status["last_replay_error"])
        self.assertEqual(status["status"], "healthy")

    def test_collect_marks_error_when_blob_listing_fails(self):
        with patch.multiple(
            AzureConfig,
            SAMPLE_BLOB_SAS_URL="https://example.blob.core.windows.net/?sv=test&sig=test",
            SAMPLE_BLOB_CONTAINER="rca-sample-ingestion",
            SAMPLE_BLOB_PREFIX="v1",
            SAMPLE_REPLAY_REBASE_TIMESTAMPS=False,
        ):
            collector = BlobSampleCollector(
                name="BlobSampleLogAnalyticsCollector",
                source=TelemetrySource.APPLICATION,
                source_folder="log_analytics",
            )
            with patch(
                "backend.replay.blob_sample_collector.requests.get",
                side_effect=[_mock_response(403, "forbidden")],
            ):
                events = collector.safe_collect()

        self.assertEqual(events, [])
        status = collector.get_status()
        self.assertEqual(status["last_replay_outcome"], "list_error")
        self.assertIn("List blobs failed with status 403", status["last_replay_error"])
        self.assertEqual(status["last_blob_list_status_code"], 403)
        self.assertEqual(status["status"], "error")
        self.assertIsNotNone(status["last_error"])


if __name__ == "__main__":
    unittest.main()

