"""Phase 3 correlation enricher for cross-signal evidence linking."""

from __future__ import annotations

from datetime import datetime, timedelta
import hashlib
import json
from typing import Iterable
import uuid

from .models import CorrelatedEvidence, TelemetryEvent


class CorrelationEnricher:
    """Correlate telemetry events by metadata and time-window overlap."""

    def __init__(self, window_minutes: int = 15, max_events: int = 5000):
        self.window = timedelta(minutes=max(1, window_minutes))
        self.max_events = max(100, max_events)
        self._recent_events: list[TelemetryEvent] = []
        self._seen_bundle_keys: set[str] = set()

    def ingest(self, event: TelemetryEvent) -> CorrelatedEvidence | None:
        self._prune(event.timestamp)
        self._recent_events.append(event)
        if len(self._recent_events) > self.max_events:
            self._recent_events = self._recent_events[-self.max_events :]

        related = self._find_related_events(event)
        if not related:
            return None

        all_events = self._unique_events([event, *related])
        distinct_sources = {item.source for item in all_events}
        if len(distinct_sources) < 2:
            return None

        join_key = self._select_join_key(all_events)
        bundle_key = self._bundle_key(join_key, all_events)
        if bundle_key in self._seen_bundle_keys:
            return None
        self._seen_bundle_keys.add(bundle_key)

        window_start = min(item.timestamp for item in all_events)
        window_end = max(item.timestamp for item in all_events)
        confidence = self._confidence_score(all_events)
        event_ids = [item.id for item in all_events if item.id]
        resource_ids = sorted({item.resource_id for item in all_events if item.resource_id})
        correlation_ids = sorted({item.correlation_id for item in all_events if item.correlation_id})

        summary = (
            f"Correlated {len(all_events)} events across {len(distinct_sources)} sources "
            f"within {(window_end - window_start).total_seconds():.0f}s using {join_key}."
        )
        return CorrelatedEvidence(
            id=str(uuid.uuid4()),
            join_key=join_key,
            window_start=window_start,
            window_end=window_end,
            source_types=sorted(distinct_sources, key=lambda value: value.value),
            event_ids=event_ids,
            resource_ids=resource_ids,
            correlation_ids=correlation_ids,
            confidence_score=confidence,
            summary=summary,
            supporting_data={
                "event_count": len(all_events),
                "distinct_source_count": len(distinct_sources),
                "window_seconds": int((window_end - window_start).total_seconds()),
            },
        )

    def _prune(self, reference_time: datetime):
        cutoff = reference_time - self.window
        self._recent_events = [item for item in self._recent_events if item.timestamp >= cutoff]

    def _find_related_events(self, event: TelemetryEvent) -> list[TelemetryEvent]:
        event_keys = self._join_tokens(event)
        if not event_keys:
            return []
        related: list[TelemetryEvent] = []
        for candidate in self._recent_events:
            if candidate is event:
                continue
            if abs((event.timestamp - candidate.timestamp).total_seconds()) > self.window.total_seconds():
                continue
            if event_keys.intersection(self._join_tokens(candidate)):
                related.append(candidate)
        return related

    @staticmethod
    def _component_tokens(event: TelemetryEvent) -> set[str]:
        payload = event.payload or {}
        tokens = set()
        app_name = payload.get("application_name")
        db_name = payload.get("database_name")
        src_ip = payload.get("source_ip")
        dst_ip = payload.get("destination_ip")
        if app_name:
            tokens.add(f"app:{str(app_name).strip().lower()}")
        if db_name:
            tokens.add(f"db:{str(db_name).strip().lower()}")
        if src_ip:
            tokens.add(f"src:{str(src_ip).strip().lower()}")
        if dst_ip:
            tokens.add(f"dst:{str(dst_ip).strip().lower()}")
        return tokens

    def _join_tokens(self, event: TelemetryEvent) -> set[str]:
        keys = set()
        if event.correlation_id:
            keys.add(f"cid:{event.correlation_id.strip().lower()}")
        if event.resource_id:
            keys.add(f"rid:{event.resource_id.strip().lower()}")
        if event.subscription_id:
            keys.add(f"sub:{event.subscription_id.strip().lower()}")
        if event.operation_name:
            keys.add(f"op:{event.operation_name.strip().lower()}")
        keys.update(self._component_tokens(event))
        return keys

    @staticmethod
    def _unique_events(events: Iterable[TelemetryEvent]) -> list[TelemetryEvent]:
        seen: set[str] = set()
        unique: list[TelemetryEvent] = []
        for event in events:
            key = event.id or f"ts:{event.timestamp.isoformat()}|src:{event.source.value}|op:{event.operation_name}"
            if key in seen:
                continue
            seen.add(key)
            unique.append(event)
        unique.sort(key=lambda item: item.timestamp)
        return unique

    def _select_join_key(self, events: list[TelemetryEvent]) -> str:
        token_sets = [self._join_tokens(item) for item in events]
        if not token_sets:
            return "time-window-only"
        common = set.intersection(*token_sets) if token_sets else set()
        if common:
            return sorted(common)[0]
        fallback = sorted(set().union(*token_sets))
        return fallback[0] if fallback else "time-window-only"

    @staticmethod
    def _bundle_key(join_key: str, events: list[TelemetryEvent]) -> str:
        event_ids = [item.id or item.timestamp.isoformat() for item in events]
        normalized = {"join_key": join_key, "event_ids": sorted(event_ids)}
        digest = hashlib.sha256(json.dumps(normalized, sort_keys=True).encode("utf-8")).hexdigest()
        return digest

    def _confidence_score(self, events: list[TelemetryEvent]) -> float:
        distinct_sources = len({item.source for item in events})
        has_shared_resource = len({item.resource_id for item in events if item.resource_id}) > 0
        has_corr_id = len({item.correlation_id for item in events if item.correlation_id}) > 0

        score = 0.35
        score += min(0.30, distinct_sources * 0.12)
        if has_shared_resource:
            score += 0.15
        if has_corr_id:
            score += 0.15
        if len(events) >= 3:
            score += 0.10
        return round(min(score, 0.99), 2)


_enricher: CorrelationEnricher | None = None


def get_correlation_enricher() -> CorrelationEnricher:
    global _enricher
    if _enricher is None:
        _enricher = CorrelationEnricher()
    return _enricher

