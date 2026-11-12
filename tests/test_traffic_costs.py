"""Check the selected fixed traffic model and its effect on route selection."""

from math import inf
from pathlib import Path
import unittest

from ers.hmm import initialize_traffic_beliefs
from ers.routing import build_routing_graph, uniform_cost_search
from ers.scenario_loader import load_scenario
from ers.travel_times import expected_traffic_multiplier, estimated_travel_time_seconds


SCENARIOS = Path(__file__).resolve().parents[1] / "data" / "scenarios"


class TrafficCostTests(unittest.TestCase):
    def test_multiplier_uses_all_probabilities_not_just_most_likely_level(self):
        belief = {"Low": 0.6, "Medium": 0.3, "High": 0.1}
        self.assertAlmostEqual(expected_traffic_multiplier(belief), 1.125)
        road = {"distance": 300, "speed": 15}
        self.assertAlmostEqual(estimated_travel_time_seconds(road, "Open", belief), 22.5)

    def test_congestion_and_traffic_use_larger_delay_without_multiplying(self):
        road = {"distance": 300, "speed": 15}
        beliefs = {
            "low": {"Low": 1.0, "Medium": 0.0, "High": 0.0},
            "mixed": {"Low": 0.6, "Medium": 0.3, "High": 0.1},
            "high": {"Low": 0.0, "Medium": 0.0, "High": 1.0},
        }
        # Road congestion takes 30 s; the traffic estimates are 20, 22.5 and 30 s.
        # Their maximum stays 30 s, without stacking the two congestion effects.
        for name, belief in beliefs.items():
            with self.subTest(traffic=name):
                self.assertEqual(
                    estimated_travel_time_seconds(road, "Congested", belief), 30.0
                )

    def test_low_traffic_cannot_reopen_a_blocked_road(self):
        road = {"distance": 300, "speed": 15}
        low = {"Low": 1.0, "Medium": 0.0, "High": 0.0}
        self.assertEqual(estimated_travel_time_seconds(road, "Blocked", low), inf)

    def test_historical_belief_is_copied_without_an_additional_prediction(self):
        scenario = load_scenario(SCENARIOS / "Scenario1")
        historical = {("H1", "N1"): {"Low": 0.2, "Medium": 0.3, "High": 0.5}}
        beliefs = initialize_traffic_beliefs(
            scenario.city_graph, historical, scenario.traffic_probabilities
        )
        self.assertEqual(beliefs[("H1", "N1")], historical[("H1", "N1")])
        self.assertIsNot(beliefs[("H1", "N1")], historical[("H1", "N1")])
        beliefs[("H1", "N1")]["Low"] = 0.9
        self.assertEqual(historical[("H1", "N1")]["Low"], 0.2)

    def test_missing_history_uses_this_scenarios_initial_distribution(self):
        scenario = load_scenario(SCENARIOS / "Scenario2")
        beliefs = initialize_traffic_beliefs(
            scenario.city_graph, {}, scenario.traffic_probabilities
        )
        self.assertEqual(len(beliefs), len(scenario.city_graph["roads"]))
        first = beliefs[("N1", "N2")]
        self.assertEqual(first, {"Low": 0.5, "Medium": 0.35, "High": 0.15})
        self.assertAlmostEqual(expected_traffic_multiplier(first), 1.1625)
        self.assertIsNot(first, scenario.traffic_probabilities["initial"])
        self.assertIsNot(first, beliefs[("N2", "N1")])

    def test_traffic_can_change_the_selected_route(self):
        city = {
            "nodes": [{"id": name} for name in ("A", "B", "C")],
            "roads": [
                {"from": "A", "to": "B", "distance": 150, "speed": 15},
                {"from": "A", "to": "C", "distance": 90, "speed": 15},
                {"from": "C", "to": "B", "distance": 90, "speed": 15},
            ],
        }
        statuses = {("A", "B"): "Open", ("A", "C"): "Open", ("C", "B"): "Open"}
        traffic = {road: {"Low": 1.0, "Medium": 0.0, "High": 0.0} for road in statuses}
        graph = build_routing_graph(city, statuses, traffic)
        self.assertEqual(uniform_cost_search(graph, "A", "B"), (["A", "B"], 10.0))
        traffic[("A", "B")] = {"Low": 0.0, "Medium": 0.0, "High": 1.0}
        graph = build_routing_graph(city, statuses, traffic)
        self.assertEqual(uniform_cost_search(graph, "A", "B"), (["A", "C", "B"], 12.0))


if __name__ == "__main__":
    unittest.main()
