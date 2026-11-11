"""Check allocation constraints, joint backtracking, and the priority objective."""

from copy import deepcopy
from pathlib import Path
import unittest

from allocation import ResponderState, allocate_responders, initialize_responders
from bayesian import infer_road_beliefs, most_likely_road_status
from hmm import infer_historical_traffic, initialize_traffic_beliefs
from routing import build_routing_graph
from scenario_loader import load_scenario


SCENARIOS = Path(__file__).resolve().parents[1] / "Scenarios"


def incident(identifier, location="A", priority="High", capability="Medical",
             timestamp=0, deadline=100, handling=3):
    return {"incident_id": identifier, "location": location, "priority": priority,
            "required_capability": capability, "timestamp": timestamp,
            "deadline": deadline, "time_required": handling}


class AllocationTests(unittest.TestCase):
    def test_backtracking_preserves_a_scarce_capability(self):
        responders = [
            ResponderState("Flexible", "S", {"Medical", "Rescue"}, 0),
            ResponderState("MedicalOnly", "S", {"Medical"}, 0),
        ]
        incidents = [incident("I1", priority="Critical"),
                     incident("I2", "B", "Critical", "Rescue")]
        graph = {"S": [("A", 1), ("B", 1)], "A": [], "B": []}
        selected = allocate_responders(incidents, responders, graph, now=0)
        self.assertEqual({item.incident_id: item.responder_id for item in selected},
                         {"I1": "MedicalOnly", "I2": "Flexible"})

    def test_each_priority_level_dominates_shorter_response_time(self):
        responders = [ResponderState("R", "S", {"Medical"}, 0)]
        graph = {"S": [("A", 10)], "A": []}
        for higher, lower in (("Critical", "High"), ("High", "Medium"), ("Medium", "Low")):
            with self.subTest(higher=higher, lower=lower):
                incidents = [incident("Lower", "S", lower), incident("Higher", "A", higher)]
                selected = allocate_responders(incidents, responders, graph, now=0)
                self.assertEqual([item.incident_id for item in selected], ["Higher"])

    def test_response_time_breaks_equal_priority_counts(self):
        responders = [ResponderState("Slow", "S", {"Medical"}, 0),
                      ResponderState("Fast", "T", {"Medical"}, 0)]
        graph = {"S": [("A", 10)], "T": [("A", 2)], "A": []}
        selected = allocate_responders([incident("I")], responders, graph, now=0)
        self.assertEqual(selected[0].responder_id, "Fast")
        self.assertEqual(selected[0].response_time, 2)

    def test_future_incidents_do_not_influence_the_current_batch(self):
        responders = [ResponderState("R", "S", {"Medical"}, 0)]
        graph = {"S": [("A", 1)], "A": []}
        known = incident("Known", priority="High")
        future = incident("Future", "S", "Critical", timestamp=10)
        selected = allocate_responders([future, known], responders, graph, now=0)
        self.assertEqual([item.incident_id for item in selected], ["Known"])

    def test_busy_responder_becomes_eligible_at_exact_availability_time(self):
        responders = [ResponderState("R", "S", {"Medical"}, 5)]
        graph = {"S": [("A", 1)], "A": []}
        incidents = [incident("I", deadline=10)]
        self.assertEqual(allocate_responders(incidents, responders, graph, now=4.9), [])
        selected = allocate_responders(incidents, responders, graph, now=5)
        self.assertEqual(selected[0].time, 5)
        self.assertEqual(selected[0].arrival_time, 6)
        self.assertEqual(selected[0].response_time, 6)  # Five waiting plus one travelling.
        self.assertEqual(selected[0].completion_time, 9)

    def test_deadline_constrains_arrival_not_service_completion(self):
        responders = [ResponderState("R", "S", {"Medical"}, 0)]
        graph = {"S": [("A", 2)], "A": []}
        incidents = [incident("I", deadline=5, handling=20)]
        selected = allocate_responders(incidents, responders, graph, now=3)
        self.assertEqual(selected[0].arrival_time, 5)
        self.assertEqual(selected[0].completion_time, 25)
        incidents[0]["deadline"] = 4.99
        self.assertEqual(allocate_responders(incidents, responders, graph, now=3), [])

    def test_unreachable_and_incompatible_assignments_are_excluded(self):
        responders = [ResponderState("R", "S", {"Medical"}, 0)]
        graph = {"S": [], "A": []}
        self.assertEqual(allocate_responders([incident("I")], responders, graph, now=0), [])
        self.assertEqual(allocate_responders(
            [incident("I", "S", capability="Rescue")], responders, graph, now=0
        ), [])

    def test_one_responder_cannot_take_two_incidents_in_a_batch(self):
        responders = [ResponderState("R1", "S", {"Medical"}, 0),
                      ResponderState("R2", "S", {"Medical"}, 0)]
        incidents = [incident("I1"), incident("I2"), incident("I3")]
        graph = {"S": [("A", 1)], "A": []}
        selected = allocate_responders(incidents, responders, graph, now=0)
        self.assertEqual(len(selected), 2)
        self.assertEqual(len({item.responder_id for item in selected}), 2)
        self.assertEqual(len({item.incident_id for item in selected}), 2)

    def test_input_state_is_preserved_and_equal_scores_are_deterministic(self):
        responders = [ResponderState("First", "S", {"Medical"}, 0),
                      ResponderState("Second", "S", {"Medical"}, 0)]
        incidents = [incident("I")]
        before = deepcopy((responders, incidents))
        graph = {"S": [("A", 1)], "A": []}
        selected = allocate_responders(incidents, responders, graph, now=0)
        self.assertEqual(selected[0].responder_id, "First")
        self.assertEqual((responders, incidents), before)
        self.assertEqual(selected, allocate_responders(incidents, responders, graph, now=0))

    def test_initial_state_uses_listed_capabilities_and_remaining_busy_time(self):
        rows = [{"responder_id": "R", "type": "Ambulance", "start_location": "S",
                 "capabilities": "Medical; First aid", "availability": "Busy",
                 "time_until_available": "10"}]
        responders = initialize_responders(rows)
        self.assertEqual(responders[0].capabilities, {"Medical", "First aid"})
        self.assertEqual(responders[0].available_at, 10)
        self.assertNotIn("Life support", responders[0].capabilities)

    def test_initial_batches_satisfy_constraints_on_all_scenarios(self):
        for number in (1, 2, 3):
            scenario = load_scenario(SCENARIOS / f"Scenario{number}")
            beliefs = infer_road_beliefs(
                scenario.city_graph, scenario.road_reports, scenario.road_probabilities
            )
            statuses = {road: most_likely_road_status(probabilities)
                        for road, probabilities in beliefs.items()}
            history = infer_historical_traffic(
                scenario.city_graph, scenario.traffic_observations, scenario.traffic_probabilities
            )
            traffic = initialize_traffic_beliefs(
                scenario.city_graph, history, scenario.traffic_probabilities
            )
            graph = build_routing_graph(scenario.city_graph, statuses, traffic)
            responders = initialize_responders(scenario.responders)
            selected = allocate_responders(scenario.incidents, responders, graph, now=0)
            self.assertTrue(selected)
            self.assertEqual(len({item.responder_id for item in selected}), len(selected))
            self.assertEqual(len({item.incident_id for item in selected}), len(selected))
            by_responder = {item.responder_id: item for item in responders}
            by_incident = {item["incident_id"]: item for item in scenario.incidents}
            for item in selected:
                unit = by_responder[item.responder_id]
                event = by_incident[item.incident_id]
                self.assertLessEqual(float(event["timestamp"]), item.time)
                self.assertLessEqual(unit.available_at, item.time)
                self.assertIn(event["required_capability"], unit.capabilities)
                self.assertEqual(item.path[0], unit.location)
                self.assertEqual(item.path[-1], event["location"])
                travel = sum(dict(graph[source])[destination]
                             for source, destination in zip(item.path, item.path[1:]))
                self.assertAlmostEqual(item.arrival_time, item.time + travel)
                self.assertLessEqual(item.arrival_time, float(event["deadline"]))
                self.assertAlmostEqual(item.response_time, item.arrival_time - float(event["timestamp"]))
                self.assertAlmostEqual(item.completion_time,
                                       item.arrival_time + float(event["time_required"]))


if __name__ == "__main__":
    unittest.main()
