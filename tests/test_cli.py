"""Exercise the documented entry point and read its exported plans from disk."""

import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

from ers.bayesian import infer_road_beliefs, most_likely_road_status
from ers.hmm import infer_historical_traffic, initialize_traffic_beliefs
from ers.routing import build_routing_graph
from ers.scenario_loader import load_scenario
from ers.validation import validate_plan


ROOT = Path(__file__).resolve().parents[1]


class CLITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory()
        cls.project = Path(cls.temporary.name) / "project"
        cls.project.mkdir()
        shutil.copy2(ROOT / "run.py", cls.project / "run.py")
        shutil.copytree(ROOT / "ers", cls.project / "ers", ignore=shutil.ignore_patterns("__pycache__"))
        shutil.copytree(ROOT / "data", cls.project / "data")

    @classmethod
    def tearDownClass(cls):
        cls.temporary.cleanup()

    def test_all_scenario_commands_export_valid_plans_and_statistics(self):
        for number in (1, 2, 3):
            with self.subTest(scenario=number):
                result = subprocess.run([sys.executable, "-B", "run.py", str(number)],
                                        cwd=self.project, capture_output=True, text=True, timeout=30)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn("plan validation passed", result.stdout)
                scenario = load_scenario(self.project / "data" / "scenarios" / f"Scenario{number}")
                road_beliefs = infer_road_beliefs(
                    scenario.city_graph, scenario.road_reports, scenario.road_probabilities
                )
                statuses = {road: most_likely_road_status(belief) for road, belief in road_beliefs.items()}
                history = infer_historical_traffic(
                    scenario.city_graph, scenario.traffic_observations, scenario.traffic_probabilities
                )
                traffic = initialize_traffic_beliefs(scenario.city_graph, history,
                                                    scenario.traffic_probabilities)
                graph = build_routing_graph(scenario.city_graph, statuses, traffic)
                folder = self.project / "outputs" / f"scenario{number}"
                plan = json.loads((folder / "plan.json").read_text())
                checked = validate_plan(plan, scenario, graph)
                text = (folder / "statistics.txt").read_text()
                self.assertIn(f"Incidents handled: {len(checked)} of {len(scenario.incidents)}", text)
                self.assertIn("seconds", text)
        self.assertTrue(all((self.project / "outputs" / f"scenario{n}" / "plan.json").exists()
                            for n in (1, 2, 3)))

    def test_entrypoint_is_independent_of_working_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            result = subprocess.run([sys.executable, "-B", str(self.project / "run.py"), "1"],
                                    cwd=directory, capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertFalse((Path(directory) / "outputs").exists())
            self.assertTrue((self.project / "outputs" / "scenario1" / "statistics.txt").exists())

    def test_route_inspection_and_invalid_scenario(self):
        result = subprocess.run([sys.executable, "-B", "run.py", "1", "--route", "N1", "N2"],
                                cwd=self.project, capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Route: N1 -> H1 -> N2", result.stdout)
        self.assertIn("79.399 s", result.stdout)
        for arguments in ([], ["4"]):
            result = subprocess.run([sys.executable, "-B", "run.py", *arguments],
                                    cwd=self.project, capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, 2)


if __name__ == "__main__":
    unittest.main()
