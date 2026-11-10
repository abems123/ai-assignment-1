"""Command-line entry point for the Emergency Response System."""

import argparse
from collections import Counter
from pathlib import Path

from bayesian import ROAD_STATUSES, infer_road_beliefs, most_likely_road_status
from scenario_loader import load_scenario


def main():
    parser = argparse.ArgumentParser(
        description="Load an emergency-response scenario and estimate road conditions."
    )
    parser.add_argument("scenario", type=int, choices=(1, 2, 3))
    args = parser.parse_args()

    # Resolve inputs relative to this file, independent of the working directory.
    scenario_directory = (
        Path(__file__).resolve().parent / "Scenarios" / f"Scenario{args.scenario}"
    )
    try:
        scenario = load_scenario(scenario_directory)
        road_beliefs = infer_road_beliefs(
            scenario.city_graph, scenario.road_reports, scenario.road_probabilities
        )
        road_statuses = {
            road: most_likely_road_status(probabilities)
            for road, probabilities in road_beliefs.items()
        }
    except (OSError, ValueError, KeyError) as error:
        parser.exit(1, f"Could not process scenario {args.scenario}: {error}\n")

    print(f"Scenario {args.scenario} loaded successfully.")
    print("Selected planning model: inferred road and traffic conditions.")
    print("Selected road-status policy: most likely status (MAP).")
    print(f"Locations: {len(scenario.city_graph['nodes'])}")
    print(f"Directed roads: {len(scenario.city_graph['roads'])}")
    print(f"Responders: {len(scenario.responders)}")
    print(f"Incidents: {len(scenario.incidents)}")
    print(f"Road reports: {len(scenario.road_reports)}")
    print(f"Historical traffic observations: {len(scenario.traffic_observations)}")
    counts = Counter(road_statuses.values())
    print("Estimated road statuses: " + ", ".join(
        f"{status}={counts[status]}" for status in ROAD_STATUSES
    ))
    print("Units: distances in metres; speeds in metres/second; times in seconds.")
    print(
        "Bayesian road inference is ready. Routing, HMM traffic estimation, and "
        "allocation will follow your design choices before generating plan.json "
        "and statistics.txt."
    )


if __name__ == "__main__":
    main()
