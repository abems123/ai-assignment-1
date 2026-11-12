"""Event-driven simulation with committed jobs and no automatic return to base."""

from copy import deepcopy
from dataclasses import dataclass
from heapq import heappop, heappush
from math import isfinite

from .allocation import Assignment, ResponderState, allocate_responders


@dataclass
class SimulationResult:
    assignments: list[Assignment]
    unhandled_incident_ids: list[str]
    finish_time: float


def run_simulation(incidents: list[dict], initial_responders: list[ResponderState],
                   graph: dict) -> SimulationResult:
    """Reveal incidents at their timestamps and dispatch at arrival/release events.

    Complete all events at one time before allocating jointly. Occupancy covers
    travel and handling. A release moves the unit to the incident location; initial
    Busy releases retain the supplied location. No active job is interrupted.
    """
    responders = deepcopy(initial_responders)
    units = {unit.responder_id: unit for unit in responders}
    if len(units) != len(responders):
        raise ValueError("Responder identifiers must be unique.")
    identifiers = [item["incident_id"] for item in incidents]
    if len(identifiers) != len(set(identifiers)):
        raise ValueError("Incident identifiers must be unique.")

    # The counter makes equal-time ordering stable without comparing payloads.
    events = []
    counter = 0
    for incident in incidents:
        timestamp = float(incident["timestamp"])
        if not isfinite(timestamp) or timestamp < 0:
            raise ValueError("Incident timestamps must be finite and non-negative.")
        heappush(events, (timestamp, counter, "incident", incident))
        counter += 1
    for unit in responders:
        if not isfinite(unit.available_at) or unit.available_at < 0:
            raise ValueError("Responder availability times must be finite and non-negative.")
        if unit.available_at > 0:
            heappush(events, (unit.available_at, counter, "release",
                              (unit.responder_id, unit.location)))
            counter += 1

    now = 0.0
    pending = []
    assignments = []
    assigned_ids = set()
    while events:
        now = events[0][0]
        while events and events[0][0] == now:
            _, _, kind, payload = heappop(events)
            if kind == "incident":
                pending.append(payload)
            else:
                responder_id, location = payload
                units[responder_id].location = location
                units[responder_id].available_at = now

        selected = allocate_responders(pending, responders, graph, now)
        selected_ids = set()
        for assignment in selected:
            assignments.append(assignment)
            assigned_ids.add(assignment.incident_id)
            selected_ids.add(assignment.incident_id)
            units[assignment.responder_id].available_at = assignment.completion_time
            heappush(events, (assignment.completion_time, counter, "release",
                              (assignment.responder_id, assignment.path[-1])))
            counter += 1
        pending = [item for item in pending if item["incident_id"] not in selected_ids]
        # Zero-duration jobs enqueue a release at this same time. The next loop
        # processes it before advancing, so another job can start immediately.

    unhandled = [item["incident_id"] for item in incidents
                 if item["incident_id"] not in assigned_ids]
    return SimulationResult(assignments, unhandled, now)
