"""Exercise event timing, committed work, responder reuse, and visibility."""

from copy import deepcopy
import unittest

from ers.allocation import ResponderState
from ers.simulation import run_simulation


def incident(identifier, location="S", priority="High", timestamp=0, deadline=100,
             handling=1, capability="Medical"):
    return {"incident_id": identifier, "location": location, "priority": priority,
            "timestamp": timestamp, "deadline": deadline, "time_required": handling,
            "required_capability": capability}


class SimulationTests(unittest.TestCase):
    def test_reuse_waits_for_handling_and_starts_from_incident_location(self):
        units = [ResponderState("R", "S", {"Medical"}, 0)]
        incidents = [incident("First", "A", "Critical", handling=4),
                     incident("Second", "B")]
        before = deepcopy((incidents, units))
        graph = {"S": [("A", 1)], "A": [("B", 2)], "B": []}
        result = run_simulation(incidents, units, graph)
        first, second = result.assignments
        self.assertEqual((first.time, first.arrival_time, first.completion_time), (0, 1, 5))
        self.assertEqual((second.time, second.path, second.arrival_time), (5, ["A", "B"], 7))
        self.assertEqual(result.finish_time, 8)
        self.assertEqual(result.unhandled_incident_ids, [])
        self.assertEqual((incidents, units), before)

    def test_initial_busy_release_retries_pending_incident_at_supplied_location(self):
        units = [ResponderState("R", "S", {"Medical"}, 5)]
        result = run_simulation([incident("I", "A", handling=3)], units,
                                {"S": [("A", 1)], "A": []})
        item = result.assignments[0]
        self.assertEqual((item.time, item.path, item.response_time), (5, ["S", "A"], 6))
        self.assertEqual(result.finish_time, 9)

    def test_later_critical_incident_does_not_interrupt_active_job(self):
        units = [ResponderState("R", "S", {"Medical"}, 0)]
        incidents = [incident("First", "A", handling=5),
                     incident("Urgent", "S", "Critical", timestamp=2)]
        result = run_simulation(incidents, units, {"S": [("A", 5)], "A": [("S", 5)]})
        self.assertEqual([(item.incident_id, item.time) for item in result.assignments],
                         [("First", 0), ("Urgent", 10)])

    def test_simultaneous_arrivals_are_allocated_as_one_batch(self):
        incidents = [incident("LowFirstInFile", priority="Low", deadline=0),
                     incident("Critical", priority="Critical", deadline=0)]
        result = run_simulation(incidents, [ResponderState("R", "S", {"Medical"}, 0)], {"S": []})
        self.assertEqual([item.incident_id for item in result.assignments], ["Critical"])
        self.assertEqual(result.unhandled_incident_ids, ["LowFirstInFile"])

    def test_simultaneous_release_updates_position_before_new_dispatch(self):
        incidents = [incident("First", "A", handling=0.5),
                     incident("AtRelease", "A", "Critical", timestamp=1, deadline=1)]
        result = run_simulation(incidents, [ResponderState("R", "S", {"Medical"}, 0)],
                                {"S": [("A", 0.5)], "A": []})
        self.assertEqual(len(result.assignments), 2)
        self.assertEqual((result.assignments[1].time, result.assignments[1].path), (1, ["A"]))

    def test_zero_duration_jobs_can_chain_without_advancing_time(self):
        incidents = [incident("I1", handling=0, deadline=0),
                     incident("I2", handling=0, deadline=0)]
        result = run_simulation(incidents, [ResponderState("R", "S", {"Medical"}, 0)], {"S": []})
        self.assertEqual(len(result.assignments), 2)
        self.assertTrue(all(item.time == 0 for item in result.assignments))
        self.assertEqual(result.finish_time, 0)

    def test_no_future_event_leaves_unreachable_incident_unhandled(self):
        result = run_simulation([incident("I", "A")],
                                [ResponderState("R", "S", {"Medical"}, 0)], {"S": [], "A": []})
        self.assertEqual(result.assignments, [])
        self.assertEqual(result.unhandled_incident_ids, ["I"])

    def test_future_fields_cannot_change_dispatches_before_reveal(self):
        units = [ResponderState("R", "S", {"Medical"}, 0)]
        incidents = [incident("Known", "A"), incident("Future", timestamp=0.5)]
        graph = {"S": [("A", 1)], "A": [("S", 1)]}
        first = run_simulation(incidents, units, graph)
        changed = deepcopy(incidents)
        changed[1].update(priority="Critical", required_capability="Rescue", location="A")
        second = run_simulation(changed, units, graph)
        self.assertEqual([item for item in first.assignments if item.time < 0.5],
                         [item for item in second.assignments if item.time < 0.5])

    def test_first_dispatch_waits_for_timestamp_and_all_handling_finishes(self):
        result = run_simulation([incident("I", timestamp=1000, deadline=1001, handling=0.25)],
                                [ResponderState("R", "S", {"Medical"}, 0)], {"S": []})
        self.assertEqual(result.assignments[0].time, 1000)
        self.assertEqual(result.finish_time, 1000.25)

    def test_empty_input_terminates(self):
        result = run_simulation([], [], {})
        self.assertEqual((result.assignments, result.unhandled_incident_ids, result.finish_time),
                         ([], [], 0))


if __name__ == "__main__":
    unittest.main()
