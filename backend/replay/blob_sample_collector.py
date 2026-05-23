"""
Sample blob replay collector.
Reads normalized TelemetryEvent JSONL records from Azure Blob and replays them.
"""

from datetime import datetime, timezone
import json
import logging
from typing import Optional
import urllib.parse
import xml.etree.ElementTree as ET

import requests

from ..azure_config import AzureConfig
from ..models import TelemetryEvent, TelemetrySource
from ..collectors.collector_base import CollectorBase

logger = logging.getLogger(__name__)


class BlobSampleCollector(CollectorBase):
    """Replay collector that reads sample JSONL events for a single source folder."""

    def __init__(self, name: str, source: TelemetrySource, source_folder: str):
        super().__init__(name, source)
        self.source_folder = source_folder
        self.sas_url = AzureConfig.SAMPLE_BLOB_SAS_URL
        self.container = AzureConfig.SAMPLE_BLOB_CONTAINER
        self.prefix = AzureConfig.SAMPLE_BLOB_PREFIX

        self._account_base_url: Optional[str] = None
        self._sas_params: dict[str, str] = {}
        self._validated = False
        self.last_blob_name: Optional[str] = None
        self.last_blob_candidate_count = 0
        self.last_blob_discovery_time: Optional[datetime] = None
        self.last_blob_list_status_code: Optional[int] = None
        self.last_blob_download_status_code: Optional[int] = None
        self.last_blob_records_parsed = 0
        self.last_replay_outcome = "not_started"
        self.last_replay_error: Optional[str] = None

    def collect(self) -> list[TelemetryEvent]:
        self.last_blob_records_parsed = 0
        self.last_blob_download_status_code = None
        if not self._validate_config():
            self._set_replay_outcome("config_invalid", "Sample blob replay configuration is incomplete or invalid")
            return []

        try:
            blob_name = self._latest_blob_name()
        except Exception as exc:
            self._set_replay_outcome("list_error", str(exc))
            raise
        if not blob_name:
            self.last_blob_name = None
            self._set_replay_outcome("no_blob_found")
            logger.debug("%s: no sample blob found under %s", self.name, self._source_prefix())
            return []

        self.last_blob_name = blob_name
        try:
            content = self._download_blob_text(blob_name)
        except Exception as exc:
            self._set_replay_outcome("download_error", str(exc))
            raise

        events: list[TelemetryEvent] = []
        invalid_records = 0
        for line in content.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
                event = TelemetryEvent(**record)
                if AzureConfig.SAMPLE_REPLAY_REBASE_TIMESTAMPS:
                    event.timestamp = datetime.utcnow()
                events.append(event)
            except Exception as exc:
                invalid_records += 1
                logger.warning("%s: invalid JSONL record skipped: %s", self.name, exc)
        self.last_blob_records_parsed = len(events)
        if invalid_records:
            self._set_replay_outcome(
                "processed_with_skips",
                f"Skipped {invalid_records} invalid JSONL records",
            )
        else:
            self._set_replay_outcome("processed")
        return events

    def _validate_config(self) -> bool:
        if self._validated:
            return True
        if not self.sas_url:
            logger.warning("%s: SAMPLE_BLOB_SAS_URL not configured", self.name)
            return False
        if not self.container:
            logger.warning("%s: SAMPLE_BLOB_CONTAINER not configured", self.name)
            return False
        parsed = urllib.parse.urlparse(self.sas_url)
        if not parsed.scheme or not parsed.netloc or not parsed.query:
            logger.warning("%s: SAMPLE_BLOB_SAS_URL is invalid", self.name)
            return False

        self._account_base_url = f"{parsed.scheme}://{parsed.netloc}"
        self._sas_params = dict(urllib.parse.parse_qsl(parsed.query, keep_blank_values=True))
        self._validated = True
        return True

    def _source_prefix(self) -> str:
        return f"{self.prefix}/{self.source_folder}/".strip("/")

    def _signed_blob_url(self, blob_path: str, extra_params: Optional[dict[str, str]] = None) -> str:
        params = self._sas_params.copy()
        if extra_params:
            params.update(extra_params)
        query = urllib.parse.urlencode(params)
        return f"{self._account_base_url}/{blob_path}?{query}"

    def _latest_blob_name(self) -> Optional[str]:
        url = self._signed_blob_url(
            self.container,
            {
                "restype": "container",
                "comp": "list",
                "prefix": self._source_prefix(),
            },
        )
        self.last_blob_discovery_time = datetime.now(timezone.utc).replace(tzinfo=None)
        response = requests.get(url, timeout=20)
        self.last_blob_list_status_code = response.status_code
        if response.status_code != 200:
            raise RuntimeError(f"List blobs failed with status {response.status_code}")

        root = ET.fromstring(response.text)
        names = [node.text for node in root.findall(".//Blob/Name") if node.text and node.text.endswith(".jsonl")]
        self.last_blob_candidate_count = len(names)
        if not names:
            return None
        names.sort()
        return names[-1]

    def _download_blob_text(self, blob_name: str) -> str:
        url = self._signed_blob_url(f"{self.container}/{blob_name}")
        response = requests.get(url, timeout=20)
        self.last_blob_download_status_code = response.status_code
        response.raise_for_status()
        return response.text

    def _set_replay_outcome(self, outcome: str, error: Optional[str] = None):
        self.last_replay_outcome = outcome
        self.last_replay_error = error

    def get_status(self) -> dict:
        status = super().get_status()
        status.update(
            {
                "source_folder": self.source_folder,
                "source_prefix": self._source_prefix(),
                "last_blob_name": self.last_blob_name,
                "last_blob_candidate_count": self.last_blob_candidate_count,
                "last_blob_discovery_time": (
                    self.last_blob_discovery_time.isoformat() if self.last_blob_discovery_time else None
                ),
                "last_blob_list_status_code": self.last_blob_list_status_code,
                "last_blob_download_status_code": self.last_blob_download_status_code,
                "last_blob_records_parsed": self.last_blob_records_parsed,
                "last_replay_outcome": self.last_replay_outcome,
                "last_replay_error": self.last_replay_error,
            }
        )
        return status
