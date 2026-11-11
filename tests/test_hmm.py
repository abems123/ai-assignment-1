"""Check forward filtering against hand calculations and full path enumeration."""

from copy import deepcopy
from itertools import product
from pathlib import Path
import unittest

from hmm import TRAFFIC_LEVELS, forward_filter, infer_historical_traffic
from scenario_loader import load_scenario


SCENARIOS = Path(__file__).resolve().parents[1] / "Scenarios"


def enumerate_hidden_histories(observations, tables):
    """Independent reference: sum probabilities of every possible hidden history."""
    totals = {level: 0.0 for level in TRAFFIC_LEVELS}
    for hidden in product(TRAFFIC_LEVELS, repeat=len(observations)):
        probability = tables["initial"][hidden[0]]
        for index, observed in enumerate(observations):
            if index > 0:
                probability *= tables["transition"][hidden[index - 1]][hidden[index]]
            probability *= tables["emission"][hidden[index]][observed]
        totals[hidden[-1]] += probability
    normalizer = sum(totals.values())
    return {level: value / normalizer for level, value in totals.items()}


class HMMTests(unittest.TestCase):
    def setUp(self):
        self.scenario = load_scenario(SCENARIOS / "Scenario1")
        self.tables = self.scenario.traffic_probabilities

    def assert_distribution_matches(self, actual, expected):
        for level in TRAFFIC_LEVELS:
            self.assertAlmostEqual(actual[level], expected[level])

    def test_first_observation_updates_initial_prior_without_transition(self):
        # Initial times Low emission: 0.51, 0.03, 0.002; total 0.542.
        expected = {"Low": 255/271, "Medium": 15/271, "High": 1/271}
        self.assert_distribution_matches(forward_filter(["Low"], self.tables), expected)

    def test_two_observations_match_hand_calculation(self):
        # After Low, predict then observe High. Weights share denominator 271000
        # and have numerators 2063, 5660, and 6480, totaling 14203.
        expected = {"Low": 2063/14203, "Medium": 5660/14203, "High": 6480/14203}
        self.assert_distribution_matches(
            forward_filter(["Low", "High"], self.tables), expected
        )

    def test_filter_matches_exhaustive_hidden_history_reference(self):
        observations = ["Low", "Medium", "High", "Medium"]
        for number in (1, 2, 3):
            with self.subTest(scenario=number):
                tables = load_scenario(SCENARIOS / f"Scenario{number}").traffic_probabilities
                expected = enumerate_hidden_histories(observations, tables)
                self.assert_distribution_matches(forward_filter(observations, tables), expected)

    def test_sequence_order_and_road_directions_are_separate(self):
        city = {"roads": [{"from": "A", "to": "B"}, {"from": "B", "to": "A"},
                          {"from": "B", "to": "C"}]}
        observations = [
            {"from": "A", "to": "B", "observation_nr": "2", "traffic_observation": "High"},
            {"from": "B", "to": "A", "observation_nr": "1", "traffic_observation": "High"},
            {"from": "A", "to": "B", "observation_nr": "1", "traffic_observation": "Low"},
        ]
        beliefs = infer_historical_traffic(city, observations, self.tables)
        self.assert_distribution_matches(beliefs[("A", "B")],
                                         forward_filter(["Low", "High"], self.tables))
        self.assert_distribution_matches(beliefs[("B", "A")],
                                         forward_filter(["High"], self.tables))
        self.assertNotIn(("B", "C"), beliefs)

    def test_all_scenarios_use_own_tables_and_preserve_inputs(self):
        first_observation_beliefs = []
        for number, expected_roads in ((1, 14), (2, 3), (3, 10)):
            scenario = load_scenario(SCENARIOS / f"Scenario{number}")
            tables_before = deepcopy(scenario.traffic_probabilities)
            observations_before = deepcopy(scenario.traffic_observations)
            beliefs = infer_historical_traffic(
                scenario.city_graph, scenario.traffic_observations,
                scenario.traffic_probabilities,
            )
            self.assertEqual(len(beliefs), expected_roads)
            for distribution in beliefs.values():
                self.assertAlmostEqual(sum(distribution.values()), 1.0)
                self.assertTrue(all(0 <= value <= 1 for value in distribution.values()))
            self.assertEqual(scenario.traffic_probabilities, tables_before)
            self.assertEqual(scenario.traffic_observations, observations_before)
            first_observation_beliefs.append(forward_filter(["Low"], scenario.traffic_probabilities))
        self.assertNotEqual(first_observation_beliefs[0], first_observation_beliefs[1])

    def test_empty_history_returns_prior_but_does_not_fill_missing_roads(self):
        prior = forward_filter([], self.tables)
        self.assertEqual(prior, self.tables["initial"])
        self.assertIsNot(prior, self.tables["initial"])
        self.assertEqual(infer_historical_traffic(self.scenario.city_graph, [], self.tables), {})

    def test_impossible_observation_is_rejected(self):
        changed = deepcopy(self.tables)
        for row in changed["emission"].values():
            row.update(Low=0.0, Medium=0.5, High=0.5)
        with self.assertRaisesRegex(ValueError, "zero probability"):
            forward_filter(["Low"], changed)


if __name__ == "__main__":
    unittest.main()
