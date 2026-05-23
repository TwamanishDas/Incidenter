"""
Azure telemetry scheduler.
Runs collectors on a periodic interval and posts normalized telemetry to the API.
"""

import asyncio
from datetime import datetime, timedelta
import hashlib
import json
import logging

import requests

from ..azure_config import AzureConfig
from ..collectors import (
    ActivityHealthCollector,
    AppInsightsCollector,
    LogAnalyticsCollector,
    MonitorMetricsCollector,
    NetworkWatcherCollector,
)
from ..models import TelemetryEvent
from ..models import TelemetrySource
from ..replay import BlobSampleCollector

logger = logging.getLogger(__name__)


class TelemetryScheduler:
    """Manages telemetry collection from all Azure sources on a schedule."""

    def __init__(self, api_base_url: str = "http://localhost:8000", interval_seconds: int | None = None):
        self.api_base_url = api_base_url.rstrip("/")
        self.interval_seconds = interval_seconds or AzureConfig.COLLECTION_INTERVAL
        self.collectors = []
        self.is_running = False
        self.collection_count = 0
        self.last_collection_time = None
        self.total_events_collected = 0
        self.total_events_posted = 0
        self.total_events_deduped = 0
        self._dedup_seen: dict[str, datetime] = {}
        self._dedup_ttl = timedelta(minutes=AzureConfig.DEDUP_WINDOW_MINUTES)
        self._stop_event = asyncio.Event()
        self._initialize_collectors()

    def _initialize_collectors(self):
        if AzureConfig.INGESTION_MODE == "sample_blob":
            collector_factories = [
                lambda: BlobSampleCollector(
                    name="BlobSampleLogAnalyticsCollector",
                    source=TelemetrySource.APPLICATION,
                    source_folder="log_analytics",
                ),
                lambda: BlobSampleCollector(
                    name="BlobSampleAppInsightsCollector",
                    source=TelemetrySource.APPLICATION,
                    source_folder="app_insights",
                ),
                lambda: BlobSampleCollector(
                    name="BlobSampleNetworkWatcherCollector",
                    source=TelemetrySource.NETWORK,
                    source_folder="network_watcher",
                ),
                lambda: BlobSampleCollector(
                    name="BlobSampleMonitorMetricsCollector",
                    source=TelemetrySource.DATABASE,
                    source_folder="azure_monitor_metrics",
                ),
                lambda: BlobSampleCollector(
                    name="BlobSampleActivityHealthCollector",
                    source=TelemetrySource.APPLICATION,
                    source_folder="activity_health",
                ),
            ]
            logger.info("TelemetryScheduler ingestion mode: sample_blob")
        else:
            collector_factories = [
                LogAnalyticsCollector,
                AppInsightsCollector,
                NetworkWatcherCollector,
                MonitorMetricsCollector,
                ActivityHealthCollector,
            ]
            logger.info("TelemetryScheduler ingestion mode: live")

        for factory in collector_factories:
            try:
                collector = factory()
                self.collectors.append(collector)
                logger.info("Initialized %s", collector.name)
            except Exception as exc:
                logger.error("Failed to initialize %s: %s", factory.__name__, exc)

        if not self.collectors:
            logger.warning("No collectors initialized")

    async def start(self):
        if self.is_running:
            logger.info("TelemetryScheduler is already running")
            return

        self._stop_event.clear()
        self.is_running = True
        logger.info("TelemetryScheduler started; interval=%ss", self.interval_seconds)

        try:
            while not self._stop_event.is_set():
                await self._collect_once()
                try:
                    await asyncio.wait_for(self._stop_event.wait(), timeout=self.interval_seconds)
                except asyncio.TimeoutError:
                    pass
        except Exception as exc:
            logger.error("Scheduler error: %s", exc)
        finally:
            self.is_running = False
            logger.info("TelemetryScheduler run loop exited")

    def stop(self):
        if not self.is_running and self._stop_event.is_set():
            return
        self.is_running = False
        self._stop_event.set()
        logger.info("TelemetryScheduler stopped")

    async def _collect_once(self):
        self.collection_count += 1
        self.last_collection_time = datetime.utcnow()
        logger.debug("Collection #%s started at %s", self.collection_count, self.last_collection_time.isoformat())

        results = await asyncio.gather(
            *(asyncio.to_thread(collector.safe_collect) for collector in self.collectors),
            return_exceptions=True,
        )

        all_events: list[TelemetryEvent] = []
        for collector, result in zip(self.collectors, results):
            if isinstance(result, Exception):
                logger.error("Collector %s failed: %s", collector.name, result)
                continue
            all_events.extend(result)

        self.total_events_collected += len(all_events)
        posted_count, deduped_count = await self._post_events(all_events)
        self.total_events_posted += posted_count
        self.total_events_deduped += deduped_count

        logger.info(
            "Collection #%s complete: collected=%s posted=%s deduped=%s",
            self.collection_count,
            len(all_events),
            posted_count,
            deduped_count,
        )
        self._log_collector_status()

    async def _post_events(self, events: list[TelemetryEvent]) -> tuple[int, int]:
        if not events:
            return 0, 0

        posted = 0
        deduped = 0
        for event in events:
            if self._is_duplicate(event):
                deduped += 1
                continue
            try:
                response = await asyncio.to_thread(
                    requests.post,
                    f"{self.api_base_url}/telemetry",
                    json=event.model_dump(mode="json"),
                    timeout=10,
                )
                if response.status_code != 200:
                    logger.warning("Failed to post event: %s - %s", response.status_code, response.text)
                    continue
                posted += 1
            except Exception as exc:
                logger.error("Error posting event: %s", exc)
        return posted, deduped

    def _is_duplicate(self, event: TelemetryEvent) -> bool:
        now_utc = datetime.utcnow()
        self._prune_dedup_cache(now_utc)
        key = self._dedup_key(event)
        seen_at = self._dedup_seen.get(key)
        if seen_at and (now_utc - seen_at) <= self._dedup_ttl:
            return True
        self._dedup_seen[key] = now_utc
        return False

    def _prune_dedup_cache(self, now_utc: datetime):
        expired_keys = [key for key, ts in self._dedup_seen.items() if (now_utc - ts) > self._dedup_ttl]
        for key in expired_keys:
            self._dedup_seen.pop(key, None)

    def _dedup_key(self, event: TelemetryEvent) -> str:
        rounded_minute = event.timestamp.replace(second=0, microsecond=0).isoformat()
        normalized_payload = {
            "source": event.source.value,
            "origin": event.origin.value,
            "resource_id": event.resource_id,
            "subscription_id": event.subscription_id,
            "region": event.region,
            "operation_name": event.operation_name,
            "correlation_id": event.correlation_id,
            "timestamp_minute": rounded_minute,
            "payload": event.payload,
        }
        digest = hashlib.sha256(json.dumps(normalized_payload, sort_keys=True, default=str).encode("utf-8"))
        return digest.hexdigest()

    def get_status(self) -> dict:
        return {
            "is_running": self.is_running,
            "interval_seconds": self.interval_seconds,
            "collection_count": self.collection_count,
            "total_events_collected": self.total_events_collected,
            "total_events_posted": self.total_events_posted,
            "total_events_deduped": self.total_events_deduped,
            "dedup_cache_size": len(self._dedup_seen),
            "last_collection_time": self.last_collection_time.isoformat() if self.last_collection_time else None,
            "collectors": [collector.get_status() for collector in self.collectors],
        }

    def _log_collector_status(self):
        for collector in self.collectors:
            logger.debug("Collector status: %s", json.dumps(collector.get_status(), default=str))


_scheduler = None


def get_scheduler(api_base_url: str = "http://localhost:8000") -> TelemetryScheduler:
    global _scheduler
    if _scheduler is None:
        _scheduler = TelemetryScheduler(api_base_url=api_base_url)
    return _scheduler


async def start_scheduler():
    scheduler = get_scheduler()
    await scheduler.start()


def stop_scheduler(reset: bool = False):
    global _scheduler
    if _scheduler:
        _scheduler.stop()
        if reset:
            _scheduler = None
