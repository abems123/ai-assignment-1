"""Check route costs, blocked roads, and optimality on the supplied scenarios."""

from math import inf, isinf
from pathlib import Path
import unittest

from bayesian import infer_road_beliefs, most_likely_road_status
from hmm import infer_historical_traffic, initialize_traffic_beliefs
from routing import build_routing_graph, uniform_cost_search
from scenario_loader import load_scenario


SCENARIOS = Path(__file__).resolve().parents[1] / "Scenarios"


def reference_distances(graph):
    """Use Floyd-Warshall as an independent reference for shortest travel times."""
    distances = {}
    for start in graph:
        for goal in graph:
            distances[(start, goal)] = 0.0 if start == goal else inf
    for start, neighbors in graph.items():
        for goal, cost in neighbors:
            distances[(start, goal)] = min(distances[(start, goal)], cost)
    for middle in graph:
        for start in graph:
            for goal in graph:
                via_middle = distances[(start, middle)] + distances[(middle, goal)]
                if via_middle < distances[(start, goal)]:
                    distances[(start, goal)] = via_middle
    return distances


class RoutingTests(unittest.TestCase):
    def test_fastest_route_can_use_more_roads(self):
        graph = {
            "A": [("B", 10), ("C", 2)], "B": [],
            "C": [("D", 2)], "D": [("B", 2)],
        }
        self.assertEqual(uniform_cost_search(graph, "A", "B"),
                         (["A", "C", "D", "B"], 6))

    def test_faster_route_replaces_an_expensive_frontier_entry(self):
        graph = {
            "A": [("B", 5), ("C", 1)], "B": [("D", 1)],
            "C": [("B", 1), ("D", 10)], "D": [],
        }
        self.assertEqual(uniform_cost_search(graph, "A", "D"),
                         (["A", "C", "B", "D"], 3))

    def test_blocked_shortcut_is_excluded(self):
        city = {
            "nodes": [{"id": name} for name in ("A", "B", "C")],
            "roads": [
                {"from": "A", "to": "B", "distance": 15, "speed": 15},
                {"from": "A", "to": "C", "distance": 150, "speed": 15},
                {"from": "C", "to": "B", "distance": 150, "speed": 15},
            ],
        }
        statuses = {("A", "B"): "Blocked", ("A", "C"): "Open", ("C", "B"): "Open"}
        traffic = {road: {"Low": 1.0, "Medium": 0.0, "High": 0.0} for road in statuses}
        graph = build_routing_graph(city, statuses, traffic)
        self.assertEqual(uniform_cost_search(graph, "A", "B"), (["A", "C", "B"], 20))
        self.assertEqual(graph["A"], [("C", 10)])

    def test_congestion_can_make_a_longer_distance_faster(self):
        city = {
            "nodes": [{"id": name} for name in ("A", "B", "C")],
            "roads": [
                {"from": "A", "to": "B", "distance": 150, "speed": 15},
                {"from": "A", "to": "C", "distance": 90, "speed": 15},
                {"from": "C", "to": "B", "distance": 90, "speed": 15},
            ],
        }
        statuses = {("A", "B"): "Congested", ("A", "C"): "Open", ("C", "B"): "Open"}
        traffic = {road: {"Low": 1.0, "Medium": 0.0, "High": 0.0} for road in statuses}
        graph = build_routing_graph(city, statuses, traffic)
        self.assertEqual(uniform_cost_search(graph, "A", "B"), (["A", "C", "B"], 12))

    def test_same_location_has_zero_travel_time(self):
        self.assertEqual(uniform_cost_search({"A": []}, "A", "A"), (["A"], 0))

    def test_directed_unreachable_route(self):
        graph = {"A": [("B", 2)], "B": [], "C": []}
        self.assertEqual(uniform_cost_search(graph, "B", "A"), ([], inf))
        self.assertEqual(uniform_cost_search(graph, "A", "C"), ([], inf))

    def test_unknown_endpoint_is_rejected(self):
        with self.assertRaises(ValueError):
            uniform_cost_search({"A": []}, "A", "Unknown")

    def test_all_scenario_routes_match_independent_reference(self):
        for number in (1, 2, 3):
            scenario = load_scenario(SCENARIOS / f"Scenario{number}")
            beliefs = infer_road_beliefs(
                scenario.city_graph, scenario.road_reports, scenario.road_probabilities
            )
            statuses = {}
            for road, probabilities in beliefs.items():
                statuses[road] = most_likely_road_status(probabilities)
            historical = infer_historical_traffic(
                scenario.city_graph, scenario.traffic_observations,
                scenario.traffic_probabilities,
            )
            traffic = initialize_traffic_beliefs(
                scenario.city_graph, historical, scenario.traffic_probabilities
            )
            graph = build_routing_graph(scenario.city_graph, statuses, traffic)
            reference = reference_distances(graph)
            for endpoints, expected_time in reference.items():
                start, goal = endpoints
                with self.subTest(scenario=number, start=start, goal=goal):
                    path, actual_time = uniform_cost_search(graph, start, goal)
                    if isinf(expected_time):
                        self.assertEqual((path, actual_time), ([], inf))
                        continue
                    self.assertAlmostEqual(actual_time, expected_time)
                    self.assertEqual(path[0], start)
                    self.assertEqual(path[-1], goal)
                    checked_time = 0
                    for source, destination in zip(path, path[1:]):
                        self.assertNotEqual(statuses[(source, destination)], "Blocked")
                        checked_time += dict(graph[source])[destination]
                    self.assertAlmostEqual(checked_time, actual_time)


if __name__ == "__main__":
    unittest.main()
