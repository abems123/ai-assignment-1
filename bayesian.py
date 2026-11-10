"""Bayesian road-status inference from local weather and noisy reports."""

from collections import defaultdict
from math import isclose
from typing import Optional


ROAD_STATUSES = ("Open", "Congested", "Blocked")
REPORT_TABLES = {
    "Citizen": "citizen_report",
    "Police": "police_report",
    "Sensor": "sensor_report",
}


def road_status_prior(tables: dict, weather: Optional[str] = None) -> dict[str, float]:
    """Condition on known local weather, or sum over unknown weather."""
    conditional = tables["road_status_given_weather"]
    if weather is not None:
        if weather not in conditional:
            raise ValueError(f"Unknown weather: {weather}")
        return dict(conditional[weather])

    return {
        status: sum(
            probability * conditional[weather_name][status]
            for weather_name, probability in tables["weather_prior"].items()
        )
        for status in ROAD_STATUSES
    }


def infer_road_probabilities(reports: list[dict], tables: dict) -> dict[str, float]:
    """Return P(road status | local weather, all reports for this directed road).

    Report errors are assumed conditionally independent given the true status.
    Each weight is the weather-based prior times the report likelihoods.
    Normalizing the three weights gives the posterior distribution.
    """
    weather_values = {report["weather"] for report in reports if report["weather"]}
    if len(weather_values) > 1:
        raise ValueError("Reports for one directed road have conflicting weather.")
    weather = next(iter(weather_values), None)
    weights = road_status_prior(tables, weather)

    for report in reports:
        source = report["source"]
        observed = report["reported_status"]
        if source not in REPORT_TABLES:
            raise ValueError(f"Unknown report source: {source}")
        if observed not in ROAD_STATUSES:
            raise ValueError(f"Unknown reported road status: {observed}")
        likelihoods = tables[REPORT_TABLES[source]]
        for status in ROAD_STATUSES:
            # CPT rows are true statuses; columns are reported statuses.
            weights[status] *= likelihoods[status][observed]

    normalizer = sum(weights.values())
    if normalizer <= 0:
        raise ValueError("The road reports have zero probability under the model.")
    return {status: weight / normalizer for status, weight in weights.items()}


def infer_road_beliefs(city_graph: dict, reports: list[dict], tables: dict) -> dict:
    """Estimate every directed road, including roads with no reports.

    Reports never cross road directions and known weather is not copied to other
    roads. These inputs are available at simulation time zero.
    """
    road_keys = {(road["from"], road["to"]) for road in city_graph["roads"]}
    reports_by_road = defaultdict(list)
    for report in reports:
        key = (report["from"], report["to"])
        if key not in road_keys:
            raise ValueError(f"Report refers to an unknown directed road: {key}")
        reports_by_road[key].append(report)

    return {
        (road["from"], road["to"]): infer_road_probabilities(
            reports_by_road[(road["from"], road["to"])], tables
        )
        for road in city_graph["roads"]
    }


def most_likely_road_status(probabilities: dict[str, float]) -> str:
    """Select the most probable status (maximum a posteriori, or MAP).

    Input must be a normalized distribution over the three road statuses.
    Exact ties choose the most restrictive tied status: Blocked, Congested, Open.
    """
    if set(probabilities) != set(ROAD_STATUSES):
        raise ValueError("Expected probabilities for Open, Congested, and Blocked.")
    if any(not 0 <= value <= 1 for value in probabilities.values()):
        raise ValueError("Probabilities must be between 0 and 1.")
    if not isclose(sum(probabilities.values()), 1.0):
        raise ValueError("Road-status probabilities must sum to 1.")

    highest_probability = max(probabilities.values())
    return next(
        status for status in ("Blocked", "Congested", "Open")
        if probabilities[status] == highest_probability
    )
