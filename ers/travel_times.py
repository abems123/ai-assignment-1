"""Travel times from inferred road status and the approved traffic-cost policy."""

from math import inf, isclose


TRAFFIC_MULTIPLIERS = {"Low": 1.0, "Medium": 1.25, "High": 1.5}


def road_travel_time_seconds(road: dict, status: str) -> float:
    """Return this road's travel time for an explicitly supplied road status.

    Distance is in metres and speed is in metres/second. A blocked road has
    infinite cost and must be excluded from usable routes. This function does
    not choose a status from probabilities or apply any traffic multiplier.
    """
    distance = road["distance"]
    speed = road["speed"]
    if distance < 0 or speed <= 0:
        raise ValueError("Road distance must be non-negative and speed positive.")

    if status == "Open":
        return distance / speed
    if status == "Congested":
        return 1.5 * distance / speed
    if status == "Blocked":
        return inf
    raise ValueError(f"Unknown road status: {status}")


def expected_traffic_multiplier(belief: dict[str, float]) -> float:
    """Average the chosen traffic multipliers using the full belief distribution."""
    if set(belief) != set(TRAFFIC_MULTIPLIERS):
        raise ValueError("Expected traffic probabilities for Low, Medium, and High.")
    if any(not 0 <= probability <= 1 for probability in belief.values()):
        raise ValueError("Traffic probabilities must be between 0 and 1.")
    if not isclose(sum(belief.values()), 1.0):
        raise ValueError("Traffic probabilities must sum to 1.")

    multiplier = 0.0
    for level, factor in TRAFFIC_MULTIPLIERS.items():
        multiplier += belief[level] * factor
    return multiplier


def estimated_travel_time_seconds(road: dict, status: str, traffic_belief: dict) -> float:
    """Combine road-status delay and the probability-weighted traffic delay.

    A blocked road remains unusable regardless of its traffic belief.
    """
    road_time = road_travel_time_seconds(road, status)

    if road_time == inf:
        return inf

    base_time = road_travel_time_seconds(road, "Open")
    traffic_time = base_time * expected_traffic_multiplier(traffic_belief)

    return max(road_time, traffic_time)