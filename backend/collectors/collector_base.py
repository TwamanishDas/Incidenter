"""
Base class for all Azure data collectors.
Defines interface and common functionality.
"""

from abc import ABC, abstractmethod
from typing import List, Optional
from datetime import datetime, timedelta
import logging

from ..azure_config import AzureConfig
from ..models import TelemetryEvent, TelemetrySource
from .kql_utils import to_utc_naive

logger = logging.getLogger(__name__)


class CollectorBase(ABC):
    """Abstract base class for Azure collectors"""
    
    def __init__(self, name: str, source: TelemetrySource):
        """
        Initialize collector
        
        Args:
            name: Collector name for logging
            source: TelemetrySource enum value
        """
        self.name = name
        self.source = source
        self.last_error: Optional[str] = None
        self.collection_count = 0
        self.last_collection_time: Optional[datetime] = None
        self.watermark_time: Optional[datetime] = None
        self.last_query_start_time: Optional[datetime] = None
        self.last_query_end_time: Optional[datetime] = None
    
    @abstractmethod
    def collect(self) -> List[TelemetryEvent]:
        """
        Collect telemetry from Azure source
        
        Returns:
            List of TelemetryEvent objects
            
        Raises:
            Exception: On collection failure
        """
        pass
    
    def safe_collect(self) -> List[TelemetryEvent]:
        """
        Wrapper around collect() with error handling

        Returns:
            List of TelemetryEvent objects (empty list on error)
        """
        try:
            events = self.collect()
            self.collection_count += len(events)
            self.last_error = None
            self.last_collection_time = datetime.utcnow()
            query_end_time = self.last_query_end_time or (
                self.last_collection_time - timedelta(seconds=AzureConfig.INGESTION_DELAY_SECONDS)
            )
            self._update_watermark(events, query_end_time)
            logger.info(f"{self.name}: Collected {len(events)} events")
            return events
        except Exception as e:
            error_msg = f"{self.name}: Collection failed: {str(e)}"
            self.last_error = error_msg
            logger.error(error_msg)
            return []

    def get_query_window(self) -> tuple[datetime, datetime]:
        """
        Compute collector query window using watermark + overlap.

        Returns:
            (start_time_utc, end_time_utc) as naive UTC datetimes
        """
        now_utc = datetime.utcnow()
        end_time = now_utc - timedelta(seconds=AzureConfig.INGESTION_DELAY_SECONDS)
        if self.watermark_time is not None:
            start_time = self.watermark_time - timedelta(seconds=AzureConfig.LOOKBACK_OVERLAP_SECONDS)
        else:
            start_time = end_time - timedelta(minutes=AzureConfig.LOOKBACK_MINUTES)

        if start_time >= end_time:
            start_time = end_time - timedelta(minutes=1)
        self.last_query_start_time = start_time
        self.last_query_end_time = end_time
        return start_time, end_time

    def _update_watermark(self, events: List[TelemetryEvent], fallback_end_time: datetime) -> None:
        """Advance watermark to max ingested event timestamp (or fallback query end time)."""
        latest_event_ts = None
        for event in events:
            event_ts = to_utc_naive(event.timestamp)
            event.timestamp = event_ts
            if latest_event_ts is None or event_ts > latest_event_ts:
                latest_event_ts = event_ts
        self.watermark_time = to_utc_naive(latest_event_ts or fallback_end_time)

    def get_status(self) -> dict:
        """Get collector status"""
        return {
            "name": self.name,
            "source": self.source.value,
            "events_collected": self.collection_count,
            "last_error": self.last_error,
            "last_collection_time": self.last_collection_time.isoformat() if self.last_collection_time else None,
            "last_query_start_time": self.last_query_start_time.isoformat() if self.last_query_start_time else None,
            "last_query_end_time": self.last_query_end_time.isoformat() if self.last_query_end_time else None,
            "watermark_time": self.watermark_time.isoformat() if self.watermark_time else None,
            "status": "healthy" if self.last_error is None else "error"
        }
