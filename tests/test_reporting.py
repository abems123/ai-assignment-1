"""Check output schema, response-time definitions, and unhandled denominators."""

import json
from pathlib import Path
import tempfile
import unittest

from ers.allocation import Assignment
from ers.reporting import calculate_statistics, format_statistics, make_plan, write_outputs


class ReportingTests(unittest.TestCase):
    def setUp(self):
        self.incidents = [
            {"incident_id": "I1", "deadline": 20},
            {"incident_id": "I2", "deadline": 20},
            {"incident_id": "I3", "deadline": 30},
        ]
        self.assignments = [Assignment("R", "I2", ["S", "A"], 5, 7, 8, 2),
                            Assignment("R", "I1", ["A", "B"], 8, 10, 11, 10)]

    def test_statistics_include_unhandled_in_deadline_denominator(self):
        statistics = calculate_statistics(self.incidents, self.assignments)
        self.assertEqual(statistics["incidents_handled"], 2)
        self.assertEqual(statistics["incidents_unhandled"], 1)
        self.assertEqual(statistics["responders_used"], 1)
        self.assertEqual(statistics["average_response_time"], 6)
        self.assertAlmostEqual(statistics["deadlines_met_percentage"], 200/3)
        self.assertEqual(statistics["unhandled_incident_ids"], ["I3"])

    def test_zero_handled_and_empty_input_have_defined_output(self):
        statistics = calculate_statistics(self.incidents, [])
        self.assertIsNone(statistics["average_response_time"])
        self.assertEqual(statistics["deadlines_met_percentage"], 0)
        self.assertIn("Average response time: N/A", format_statistics(statistics))
        empty = calculate_statistics([], [])
        self.assertIsNone(empty["deadlines_met_percentage"])
        self.assertIn("Deadlines met: N/A", format_statistics(empty))

    def test_files_keep_exact_plan_fields_and_readable_statistics(self):
        plan = make_plan(self.assignments)
        for entry in plan:
            self.assertEqual(set(entry), {"responder_id", "incident_id", "path", "time"})
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory) / "scenario"
            write_outputs(folder, plan, calculate_statistics(self.incidents, self.assignments))
            self.assertEqual(json.loads((folder / "plan.json").read_text()), plan)
            text = (folder / "statistics.txt").read_text()
            self.assertIn("Average response time: 6.000 s", text)
            self.assertIn("Deadlines met: 66.667% (2/3)", text)
            self.assertIn("Unhandled incident IDs: I3", text)


if __name__ == "__main__":
    unittest.main()
