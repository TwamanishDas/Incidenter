import unittest

from backend.app import list_active_incident_cards, simulate
from backend.data_store import store
from backend.models import SimulationRequest
from backend.processors import reset_repeat_incident_tracker


class DashboardActiveIncidentTests(unittest.TestCase):
    def setUp(self):
        reset_repeat_incident_tracker()
        store.telemetry.clear()
        store.incidents.clear()
        store.correlations.clear()
        store.evidence_records.clear()

    def test_dashboard_active_incidents_returns_empty_list_when_no_incidents(self):
        cards = list_active_incident_cards()
        self.assertEqual(cards, [])

    def test_dashboard_active_incidents_returns_sorted_cards(self):
        simulate(SimulationRequest(scenario="network_spike"))
        simulate(SimulationRequest(scenario="app_error"))

        cards = list_active_incident_cards()

        self.assertEqual(len(cards), 2)
        incident_types = {item.incident_type.value for item in cards}
        self.assertEqual(incident_types, {"network", "application"})
        self.assertGreaterEqual(cards[0].detected_at, cards[1].detected_at)
        self.assertEqual(cards[0].status, "active")
        self.assertTrue(cards[0].incident_id)
        self.assertGreaterEqual(cards[0].evidence_count, 1)
        self.assertTrue(cards[0].primary_evidence)


if __name__ == "__main__":
    unittest.main()
