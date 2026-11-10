"""Check Bayesian reasoning against hand calculations and scenario evidence."""

from copy import deepcopy
from pathlib import Path
import unittest

from bayesian import (
    infer_road_beliefs,
    infer_road_probabilities,
    most_likely_road_status,
    road_status_prior,
)
from scenario_loader import load_scenario


SCENARIOS = Path(__file__).resolve().parents[1] / "Scenarios"


class BayesianTests(unittest.TestCase):
    def setUp(self):
        self.scenario = load_scenario(SCENARIOS / "Scenario1")
        self.tables = self.scenario.road_probabilities
        self.reports = [
            report for report in self.scenario.road_reports
            if (report["from"], report["to"]) == ("N1", "N2")
        ]

    def test_posterior_matches_hand_calculation(self):
        # Rain prior with Citizen=Blocked, Police=Blocked, Sensor=Congested.
        # Hand-calculated weights are 0.00012, 0.00384, and 0.00441.
        posterior = infer_road_probabilities(self.reports, self.tables)
        expected = {"Open": 12 / 837, "Congested": 384 / 837, "Blocked": 441 / 837}
        for status, probability in expected.items():
            self.assertAlmostEqual(posterior[status], probability)
        self.assertEqual(most_likely_road_status(posterior), "Blocked")

    def test_known_local_weather_does_not_depend_on_weather_prior(self):
        changed = deepcopy(self.tables)
        changed["weather_prior"] = {"Clear": 1.0, "Rain": 0.0, "Storm": 0.0}
        self.assertEqual(
            infer_road_probabilities(self.reports, self.tables),
            infer_road_probabilities(self.reports, changed),
        )

    def test_no_reports_uses_weather_marginalization(self):
        posterior = infer_road_probabilities([], self.tables)
        expected = {"Open": 0.685, "Congested": 0.18, "Blocked": 0.135}
        for status, probability in expected.items():
            self.assertAlmostEqual(posterior[status], probability)
        self.assertEqual(most_likely_road_status(posterior), "Open")
        self.assertEqual(road_status_prior(self.tables, "Storm"),
                         self.tables["road_status_given_weather"]["Storm"])

    def test_directions_and_unreported_roads_remain_separate(self):
        beliefs = infer_road_beliefs(
            self.scenario.city_graph, self.scenario.road_reports, self.tables
        )
        self.assertEqual(most_likely_road_status(beliefs[("N1", "N2")]), "Blocked")
        self.assertEqual(most_likely_road_status(beliefs[("N2", "N1")]), "Congested")
        self.assertEqual(beliefs[("H1", "N1")], infer_road_probabilities([], self.tables))

    def test_ties_choose_most_restrictive_tied_status(self):
        examples = (
            ({"Open": 0.5, "Congested": 0.5, "Blocked": 0}, "Congested"),
            ({"Open": 0.5, "Congested": 0, "Blocked": 0.5}, "Blocked"),
            ({"Open": 1/3, "Congested": 1/3, "Blocked": 1/3}, "Blocked"),
        )
        for probabilities, expected in examples:
            with self.subTest(probabilities=probabilities):
                self.assertEqual(most_likely_road_status(probabilities), expected)

    def test_impossible_evidence_is_not_given_an_arbitrary_posterior(self):
        changed = deepcopy(self.tables)
        for row in changed["sensor_report"].values():
            row.update(Open=0.0, Congested=0.5, Blocked=0.5)
        reports = [{"weather": "Rain", "source": "Sensor", "reported_status": "Open"}]
        with self.assertRaisesRegex(ValueError, "zero probability"):
            infer_road_probabilities(reports, changed)


if __name__ == "__main__":
    unittest.main()
