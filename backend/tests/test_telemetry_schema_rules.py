import unittest

from pydantic import ValidationError

from backend.models import (
    TelemetryEvent,
    TelemetryOrigin,
    TelemetrySchemaType,
    TelemetrySource,
)


class TelemetrySchemaRulesTests(unittest.TestCase):
    def test_custom_schema_persists_full_raw_payload(self):
        payload = {"message": "hello", "customDimensions": {"tenant": "acme"}}
        event = TelemetryEvent(
            source=TelemetrySource.APPLICATION,
            origin=TelemetryOrigin.APP_INSIGHTS,
            schema_type=TelemetrySchemaType.CUSTOM,
            payload=payload,
        )

        self.assertEqual(event.raw, payload)
        self.assertEqual(event.fields, ["customDimensions", "message"])
        self.assertEqual(event.source_system, "Application Insights")
        self.assertEqual(event.collection_channel, "Application Insights Query API")

    def test_vendor_schema_requires_parser_version(self):
        with self.assertRaises(ValidationError):
            TelemetryEvent(
                source=TelemetrySource.NETWORK,
                origin=TelemetryOrigin.NETWORK_WATCHER,
                schema_type=TelemetrySchemaType.VENDOR,
                payload={"eventid": "12345", "severity": "high"},
            )

    def test_vendor_schema_stores_raw_when_parser_version_present(self):
        payload = {"eventid": "12345", "severity": "high"}
        event = TelemetryEvent(
            source=TelemetrySource.NETWORK,
            origin=TelemetryOrigin.NETWORK_WATCHER,
            schema_type=TelemetrySchemaType.VENDOR,
            parser_version="panos-11.0",
            payload=payload,
        )

        self.assertEqual(event.raw, payload)
        self.assertEqual(event.parser_version, "panos-11.0")


if __name__ == "__main__":
    unittest.main()
