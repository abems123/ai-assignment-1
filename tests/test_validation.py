"""Reject infeasible exported plans and recompute their timings independently."""

from copy import deepcopy
import unittest

from ers.scenario_loader import Scenario
from ers.validation import validate_plan


class ValidationTests(unittest.TestCase):
    def setUp(self):
        self.graph = {"S": [("A", 1), ("B", 3)], "A": [("B", 1)], "B": []}
        self.scenario = Scenario(
            city_graph={"nodes": [{"id": name} for name in self.graph], "roads": []},
            responders=[{"responder_id": "R", "start_location": "S", "capabilities": "Medical",
                         "availability": "Available", "time_until_available": "0"}],
            incidents=[
                {"incident_id": "I1", "location": "A", "required_capability": "Medical",
                 "timestamp": 0, "deadline": 1, "time_required": 3},
                {"incident_id": "I2", "location": "B", "required_capability": "Medical",
                 "timestamp": 2, "deadline": 10, "time_required": 2},
            ], road_reports=[], road_probabilities={}, traffic_observations=[], traffic_probabilities={},
        )
        self.plan = [
            {"responder_id": "R", "incident_id": "I1", "path": ["S", "A"], "time": 0},
            {"responder_id": "R", "incident_id": "I2", "path": ["A", "B"], "time": 4},
        ]

    def test_valid_plan_replays_waiting_locations_and_service_end(self):
        checked = validate_plan(self.plan, self.scenario, self.graph)
        self.assertEqual((checked[0].arrival_time, checked[0].completion_time), (1, 4))
        self.assertEqual((checked[1].arrival_time, checked[1].completion_time,
                          checked[1].response_time), (5, 7, 3))

    def test_invalid_assignment_mutations_are_rejected(self):
        mutations = (
            ("overlap", 1, "time", 3), ("late arrival", 0, "time", 0.5),
            ("unknown responder", 0, "responder_id", "Missing"),
            ("unknown incident", 0, "incident_id", "Missing"),
            ("duplicate incident", 1, "incident_id", "I1"),
            ("empty path", 0, "path", []), ("path string", 0, "path", "S,A"),
            ("unknown node", 0, "path", ["S", "Missing", "A"]),
            ("wrong start", 1, "path", ["S", "B"]),
            ("wrong destination", 0, "path", ["S"]),
            ("missing directed edge", 0, "path", ["S", "B", "A"]),
            ("negative time", 0, "time", -1), ("NaN time", 0, "time", float("nan")),
            ("infinite time", 0, "time", float("inf")), ("boolean time", 0, "time", True),
        )
        for name, index, field, value in mutations:
            with self.subTest(name=name):
                bad = deepcopy(self.plan)
                bad[index][field] = value
                with self.assertRaises(ValueError):
                    validate_plan(bad, self.scenario, self.graph)

    def test_capability_visibility_and_initial_busy_constraints(self):
        for kind in ("capability", "future incident", "initial busy"):
            with self.subTest(kind=kind):
                changed = deepcopy(self.scenario)
                if kind == "capability":
                    changed.responders[0]["capabilities"] = "Rescue"
                elif kind == "future incident":
                    changed.incidents[0]["timestamp"] = 1
                else:
                    changed.responders[0].update(availability="Busy", time_until_available="2")
                with self.assertRaises(ValueError):
                    validate_plan(self.plan, changed, self.graph)

    def test_blocked_edge_cannot_be_claimed_in_plan(self):
        graph = deepcopy(self.graph)
        graph["S"] = [("B", 3)]
        with self.assertRaisesRegex(ValueError, "road"):
            validate_plan(self.plan, self.scenario, graph)

    def test_schema_is_checked(self):
        missing = deepcopy(self.plan)
        del missing[0]["path"]
        extra = deepcopy(self.plan)
        extra[0]["arrival_time"] = 1
        for bad in (missing, extra, {"assignments": self.plan}):
            with self.subTest(plan=bad):
                with self.assertRaises(ValueError):
                    validate_plan(bad, self.scenario, self.graph)

    def test_busy_unit_can_start_at_exact_release_and_stay_after_service(self):
        changed = deepcopy(self.scenario)
        changed.responders[0].update(availability="Busy", time_until_available="2")
        changed.incidents[0]["deadline"] = 3
        plan = deepcopy(self.plan)
        plan[0]["time"] = 2
        plan[1]["time"] = 6
        checked = validate_plan(plan, changed, self.graph)
        self.assertEqual((checked[0].arrival_time, checked[1].arrival_time), (3, 7))

    def test_empty_plan_is_feasible_without_claiming_incidents_handled(self):
        self.assertEqual(validate_plan([], self.scenario, self.graph), [])


if __name__ == "__main__":
    unittest.main()
