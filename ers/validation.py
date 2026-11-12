"""Replay exported plans independently of the allocator and event scheduler."""

from math import isfinite

from .allocation import Assignment, initialize_responders
from .scenario_loader import Scenario


PLAN_FIELDS = {"responder_id", "incident_id", "path", "time"}


def validate_plan(plan: list[dict], scenario: Scenario, graph: dict) -> list[Assignment]:
    """Check schema and operational feasibility, returning recomputed timings.

    Validation uses the selected fixed road/traffic costs. It does not certify
    real-world road states, global optimality, or absence of hidden lookahead.
    """
    if not isinstance(plan, list):
        raise ValueError("A plan must be a list of assignments.")
    for entry in plan:
        if not isinstance(entry, dict) or set(entry) != PLAN_FIELDS:
            raise ValueError("Each plan entry must contain responder_id, incident_id, path, and time.")
        start = entry["time"]
        if isinstance(start, bool) or not isinstance(start, (int, float)):
            raise ValueError("Assignment start times must be numbers.")
        if not isfinite(start) or start < 0:
            raise ValueError("Assignment start times must be finite and non-negative.")

    units = {unit.responder_id: unit for unit in initialize_responders(scenario.responders)}
    incidents = {item["incident_id"]: item for item in scenario.incidents}
    if len(units) != len(scenario.responders) or len(incidents) != len(scenario.incidents):
        raise ValueError("Responder and incident identifiers must be unique.")
    road_costs = {}
    for source, neighbors in graph.items():
        for destination, cost in neighbors:
            if not isfinite(cost) or cost < 0:
                raise ValueError("Usable road costs must be finite and non-negative.")
            key = (source, destination)
            if key not in road_costs or cost < road_costs[key]:
                road_costs[key] = cost

    seen_incidents = set()
    checked = []
    # Equal-time entries retain their list order, including zero-duration chains.
    for entry in sorted(plan, key=lambda item: item["time"]):
        responder_id = entry["responder_id"]
        incident_id = entry["incident_id"]
        if not isinstance(responder_id, str) or responder_id not in units:
            raise ValueError("Plan contains an unknown responder.")
        if not isinstance(incident_id, str) or incident_id not in incidents:
            raise ValueError("Plan contains an unknown incident.")
        if incident_id in seen_incidents:
            raise ValueError("An incident is assigned more than once.")
        unit = units[responder_id]
        incident = incidents[incident_id]
        start = float(entry["time"])
        timestamp = float(incident["timestamp"])
        deadline = float(incident["deadline"])
        handling = float(incident["time_required"])
        if not all(isfinite(value) for value in (timestamp, deadline, handling)):
            raise ValueError("Incident times must be finite.")
        if timestamp < 0 or handling < 0:
            raise ValueError("Incident timestamps and handling times must be non-negative.")
        if start < timestamp:
            raise ValueError("An assignment starts before the incident becomes known.")
        if start < unit.available_at:
            raise ValueError("A responder is assigned while still busy.")
        if incident["required_capability"] not in unit.capabilities:
            raise ValueError("A responder lacks the required capability.")

        path = entry["path"]
        if not isinstance(path, list) or not path:
            raise ValueError("Every assignment needs a non-empty route.")
        if any(not isinstance(node, str) or node not in graph for node in path):
            raise ValueError("A route contains an unknown location.")
        if path[0] != unit.location or path[-1] != incident["location"]:
            raise ValueError("A route has an incorrect start or destination.")
        travel = 0.0
        for source, destination in zip(path, path[1:]):
            if (source, destination) not in road_costs:
                raise ValueError("A route uses a missing, blocked, or wrong-direction road.")
            travel += road_costs[(source, destination)]
        arrival = start + travel
        completion = arrival + handling
        if not isfinite(arrival) or not isfinite(completion):
            raise ValueError("Assignment timings must be finite.")
        if arrival > deadline:
            raise ValueError("A responder arrives after the incident deadline.")

        checked.append(Assignment(responder_id, incident_id, list(path), start,
                                  arrival, completion, arrival - timestamp))
        seen_incidents.add(incident_id)
        unit.available_at = completion
        unit.location = incident["location"]
    return checked
