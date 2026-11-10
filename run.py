"""Command-line entry point for the Emergency Response System."""

import argparse
from pathlib import Path

from scenario_loader import load_scenario


def main():
    parser = argparse.ArgumentParser(
        description="Load an emergency-response scenario (input-loading stage)."
    )
    parser.add_argument("scenario", type=int, choices=(1, 2, 3))
    args = parser.parse_args()

    # Resolve inputs relative to this file, independent of the working directory.
    scenario_directory = (
        Path(__file__).resolve().parent / "Scenarios" / f"Scenario{args.scenario}"
    )
    try:
        scenario = load_scenario(scenario_directory)
    except (OSError, ValueError) as error:
        parser.exit(1, f"Could not load scenario {args.scenario}: {error}\n")

    print(f"Scenario {args.scenario} loaded successfully.")
    print(f"Locations: {len(scenario.city_graph['nodes'])}")
    print(f"Directed roads: {len(scenario.city_graph['roads'])}")
    print(f"Responders: {len(scenario.responders)}")
    print(f"Incidents: {len(scenario.incidents)}")
    print(f"Road reports: {len(scenario.road_reports)}")
    print(f"Historical traffic observations: {len(scenario.traffic_observations)}")
    print("Units: distances in metres; speeds in metres/second; times in seconds.")
    print(
        "Next stage: choose the planning behavior before adding AI and generating "
        "plan.json and statistics.txt."
    )


if __name__ == "__main__":
    main()
