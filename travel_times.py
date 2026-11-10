"""Travel-time rules stated in the assignment; traffic effects come later."""

from math import inf


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
