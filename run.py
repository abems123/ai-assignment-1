"""Command-line entry point for the Emergency Response System."""

import argparse
from collections import Counter
from pathlib import Path

from bayesian import ROAD_STATUSES, infer_road_beliefs, most_likely_road_status
from hmm import infer_historical_traffic, initialize_traffic_beliefs
from routing import build_routing_graph, uniform_cost_search
from scenario_loader import load_scenario
from travel_times import TRAFFIC_MULTIPLIERS


def main():
    parser = argparse.ArgumentParser(
        description="Estimate road conditions and inspect routes in a scenario."
    )
    parser.add_argument("scenario", type=int, choices=(1, 2, 3))
    parser.add_argument(
        "--route", nargs=2, metavar=("START", "GOAL"),
        help="Inspect a route between two locations without assigning a responder.",
    )
    args = parser.parse_args()

    # Resolve inputs relative to this file, independent of the working directory.
    scenario_directory = (
        Path(__file__).resolve().parent / "Scenarios" / f"Scenario{args.scenario}"
    )
    try:
        scenario = load_scenario(scenario_directory)

        # 1. Bayesian inference:
        road_beliefs = infer_road_beliefs(
            scenario.city_graph, scenario.road_reports, scenario.road_probabilities
        )

        # 2. Select MAP road statuses:
        road_statuses = {
            road: most_likely_road_status(probabilities)
            for road, probabilities in road_beliefs.items()
        }

        # 3. HMM historical forward filtering:
        historical_traffic_beliefs = infer_historical_traffic(
            scenario.city_graph, scenario.traffic_observations,
            scenario.traffic_probabilities,
        )

        # 4. Initialize traffic beliefs for every road:
        traffic_beliefs = initialize_traffic_beliefs(
            scenario.city_graph, historical_traffic_beliefs, scenario.traffic_probabilities
        )

        # 5. Build a graph with both kinds of estimates:
        routing_graph = build_routing_graph(scenario.city_graph, road_statuses, traffic_beliefs)
        route = None
        if args.route:
            # 6. Find a route using UCS:
            route = uniform_cost_search(routing_graph, args.route[0], args.route[1])
    except (OSError, ValueError, KeyError) as error:
        parser.exit(1, f"Could not process scenario {args.scenario}: {error}\n")

    print(f"Scenario {args.scenario} loaded successfully.")
    print("Selected planning model: inferred road and traffic conditions.")
    print("Selected road-status policy: most likely status (MAP).")
    print("Selected routing algorithm: uniform-cost search.")
    print("Selected historical traffic method: forward filtering.")
    print("Traffic policy: fixed beliefs and probability-weighted travel multipliers.")
    print(f"Traffic multipliers: {TRAFFIC_MULTIPLIERS}")
    print(f"Locations: {len(scenario.city_graph['nodes'])}")
    print(f"Directed roads: {len(scenario.city_graph['roads'])}")
    print(f"Responders: {len(scenario.responders)}")
    print(f"Incidents: {len(scenario.incidents)}")
    print(f"Road reports: {len(scenario.road_reports)}")
    print(f"Historical traffic observations: {len(scenario.traffic_observations)}")
    print(
        f"Historical traffic beliefs computed for {len(historical_traffic_beliefs)} "
        f"of {len(scenario.city_graph['roads'])} directed roads."
    )
    fallback_count = len(traffic_beliefs) - len(historical_traffic_beliefs)
    print(f"Initial-distribution fallback used for {fallback_count} directed roads.")
    counts = Counter(road_statuses.values())
    print("Estimated road statuses: " + ", ".join(
        f"{status}={counts[status]}" for status in ROAD_STATUSES
    ))
    usable_roads = sum(len(neighbors) for neighbors in routing_graph.values())
    print(f"Usable directed roads in the routing graph: {usable_roads}")
    print("Units: distances in metres; speeds in metres/second; times in seconds.")
    if route is not None:
        path, travel_time = route
        if path:
            print("Route: " + " -> ".join(path))
            print(f"Estimated travel time (road status and traffic): {travel_time:.3f} s")
        else:
            print(f"No usable route from {args.route[0]} to {args.route[1]}.")
    print(
        "Bayesian inference, HMM traffic estimation, and routing are ready. "
        "Allocation and simulation will follow your design choices before "
        "generating plan.json and statistics.txt."
    )


if __name__ == "__main__":
    main()
