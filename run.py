"""Command-line entry point for the Emergency Response System."""

import argparse
from collections import Counter
from pathlib import Path

from allocation import allocate_responders, initialize_responders
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
        road_beliefs = infer_road_beliefs(
            scenario.city_graph, scenario.road_reports, scenario.road_probabilities
        )
        road_statuses = {
            road: most_likely_road_status(probabilities)
            for road, probabilities in road_beliefs.items()
        }
        historical_traffic_beliefs = infer_historical_traffic(
            scenario.city_graph, scenario.traffic_observations,
            scenario.traffic_probabilities,
        )
        traffic_beliefs = initialize_traffic_beliefs(
            scenario.city_graph, historical_traffic_beliefs, scenario.traffic_probabilities
        )
        routing_graph = build_routing_graph(scenario.city_graph, road_statuses, traffic_beliefs)
        responders = initialize_responders(scenario.responders)
        initial_assignments = allocate_responders(
            scenario.incidents, responders, routing_graph, now=0.0
        )
        route = None
        if args.route:
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
    assignment_word = "assignment" if len(initial_assignments) == 1 else "assignments"
    print(f"Initial dispatch preview at t=0: {len(initial_assignments)} {assignment_word}.")
    for assignment in initial_assignments:
        print(
            f"  {assignment.responder_id} -> {assignment.incident_id}, "
            f"path={assignment.path}, arrival={assignment.arrival_time:.3f} s, "
            f"completion={assignment.completion_time:.3f} s"
        )
    if route is not None:
        path, travel_time = route
        if path:
            print("Route: " + " -> ".join(path))
            print(f"Estimated travel time (road status and traffic): {travel_time:.3f} s")
        else:
            print(f"No usable route from {args.route[0]} to {args.route[1]}.")
    print(
        "Bayesian inference, HMM traffic estimation, routing, and CSP allocation "
        "are ready. Simulation and statistics policies will follow your design "
        "choices before generating plan.json and statistics.txt."
    )


if __name__ == "__main__":
    main()
