"""Priority-first responder allocation using plain CSP backtracking."""

from dataclasses import dataclass
from math import isfinite

from routing import uniform_cost_search


PRIORITIES = ("Critical", "High", "Medium", "Low")


@dataclass
class ResponderState:
    responder_id: str
    location: str
    capabilities: set[str]
    available_at: float


@dataclass
class Assignment:
    responder_id: str
    incident_id: str
    path: list[str]
    time: float
    arrival_time: float
    completion_time: float
    response_time: float


def initialize_responders(rows: list[dict]) -> list[ResponderState]:
    """Read the supplied locations, capabilities, and initial availability.

    At time zero, time_until_available is also the absolute availability time
    for an initially Busy responder. Later state updates belong to the simulator.
    """
    responders = []
    for row in rows:
        availability = row["availability"]
        remaining = float(row["time_until_available"])
        if availability not in ("Available", "Busy"):
            raise ValueError(f"Unknown responder availability: {availability}")
        if not isfinite(remaining) or remaining < 0:
            raise ValueError("Responder availability time must be finite and non-negative.")
        if availability == "Available" and remaining != 0:
            raise ValueError("An Available responder must have zero time_until_available.")

        capabilities = set()
        for capability in row["capabilities"].split(";"):
            if capability.strip():
                capabilities.add(capability.strip())
        responders.append(ResponderState(
            responder_id=row["responder_id"],
            location=row["start_location"],
            capabilities=capabilities,
            available_at=remaining,
        ))
    return responders


def feasible_assignments(incident: dict, responders: list[ResponderState],
                         graph: dict, now: float) -> list[Assignment]:
    """Build one incident's responder domain using the operational constraints."""
    timestamp = float(incident["timestamp"])
    if timestamp > now:
        return []  # Future incidents cannot affect the allocation.
    deadline = float(incident["deadline"])
    handling_time = float(incident["time_required"])
    if not isfinite(timestamp) or not isfinite(deadline) or not isfinite(handling_time):
        raise ValueError("Incident times must be finite.")
    if timestamp < 0 or handling_time < 0:
        raise ValueError("Incident timestamps and handling times must be non-negative.")

    choices = []
    for responder in responders:
        if responder.available_at > now:
            continue
        if incident["required_capability"] not in responder.capabilities:
            continue
        path, travel_time = uniform_cost_search(graph, responder.location, incident["location"])
        if not path:
            continue
        arrival_time = now + travel_time
        if arrival_time > deadline:
            continue
        choices.append(Assignment(
            responder_id=responder.responder_id,
            incident_id=incident["incident_id"],
            path=path,
            time=now,
            arrival_time=arrival_time,
            completion_time=arrival_time + handling_time,
            response_time=arrival_time - timestamp,
        ))
    return choices


def allocate_responders(pending_incidents: list[dict], responders: list[ResponderState],
                        graph: dict, now: float) -> list[Assignment]:
    """Find the best immediate dispatch batch without changing input state.

    Variables are known, pending incidents. Domains contain feasible responder
    assignments, plus leaving the incident unassigned for now. A responder may
    appear at most once in a batch. The caller supplies only unhandled incidents
    and current responder positions/availability; future timestamps are filtered.

    Maximize Critical count, then High, Medium, and Low, then minimize total
    response time (arrival minus incident timestamp). This optimizes this batch,
    not future dispatches or the entire simulation. No forward checking is used.
    """
    if not isfinite(now) or now < 0:
        raise ValueError("Allocation time must be finite and non-negative.")
    responder_ids = [responder.responder_id for responder in responders]
    if len(responder_ids) != len(set(responder_ids)):
        raise ValueError("Responder identifiers must be unique.")

    # Future incidents are excluded before their priorities or capabilities are read.
    known_incidents = []
    for incident in pending_incidents:
        if float(incident["timestamp"]) <= now:
            known_incidents.append(incident)
    incident_ids = [incident["incident_id"] for incident in known_incidents]
    if len(incident_ids) != len(set(incident_ids)):
        raise ValueError("Known incident identifiers must be unique.")

    domains = []
    priority_indices = []
    for incident in known_incidents:
        if incident["priority"] not in PRIORITIES:
            raise ValueError(f"Unknown incident priority: {incident['priority']}")
        priority_indices.append(PRIORITIES.index(incident["priority"]))
        domains.append(feasible_assignments(incident, responders, graph, now))

    chosen = []
    used_responders = set()
    counts = [0, 0, 0, 0]
    best_score = None
    best_assignments = []

    def backtrack(index, total_response_time):
        nonlocal best_score, best_assignments
        if index == len(domains):
            # Python compares tuples left-to-right: priorities dominate response time.
            score = tuple(counts) + (-total_response_time,)
            if best_score is None or score > best_score:
                best_score = score
                best_assignments = list(chosen)
            return

        priority_index = priority_indices[index]
        for assignment in domains[index]:
            if assignment.responder_id in used_responders:
                continue
            chosen.append(assignment)
            used_responders.add(assignment.responder_id)
            counts[priority_index] += 1
            backtrack(index + 1, total_response_time + assignment.response_time)
            # Undo this choice before trying another combination.
            counts[priority_index] -= 1
            used_responders.remove(assignment.responder_id)
            chosen.pop()

        # Unassigned is a valid domain value, not a decision to drop the incident forever.
        backtrack(index + 1, total_response_time)

    backtrack(0, 0.0)
    return best_assignments
