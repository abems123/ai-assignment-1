"""Load one scenario, run the complete system, validate, and save its outputs."""

import argparse
from pathlib import Path

from .allocation import initialize_responders
from .bayesian import infer_road_beliefs, most_likely_road_status
from .hmm import infer_historical_traffic, initialize_traffic_beliefs
from .reporting import make_plan, calculate_statistics, format_statistics, write_outputs
from .routing import build_routing_graph, uniform_cost_search
from .scenario_loader import load_scenario
from .simulation import run_simulation
from .validation import validate_plan


def main():
    parser = argparse.ArgumentParser(description="Run the Emergency Response System for a scenario.")
    parser.add_argument("scenario", type=int, choices=(1, 2, 3))
    parser.add_argument("--route", nargs=2, metavar=("START", "GOAL"),
                        help="Inspect a route instead of running the full simulation.")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]

    try:
        scenario = load_scenario(root / "data" / "scenarios" / f"Scenario{args.scenario}")
        road_beliefs = infer_road_beliefs(
            scenario.city_graph, scenario.road_reports, scenario.road_probabilities
        )
        road_statuses = {road: most_likely_road_status(belief)
                         for road, belief in road_beliefs.items()}
        history = infer_historical_traffic(
            scenario.city_graph, scenario.traffic_observations, scenario.traffic_probabilities
        )
        traffic = initialize_traffic_beliefs(scenario.city_graph, history, scenario.traffic_probabilities)
        graph = build_routing_graph(scenario.city_graph, road_statuses, traffic)
        if args.route:
            path, travel = uniform_cost_search(graph, args.route[0], args.route[1])
            if path:
                print("Route: " + " -> ".join(path))
                print(f"Estimated travel time (road status and traffic): {travel:.3f} s")
            else:
                print(f"No usable route from {args.route[0]} to {args.route[1]}.")
            return

        result = run_simulation(scenario.incidents, initialize_responders(scenario.responders), graph)
        plan = make_plan(result.assignments)
        checked_assignments = validate_plan(plan, scenario, graph)
        statistics = calculate_statistics(scenario.incidents, checked_assignments)
        output_directory = root / "outputs" / f"scenario{args.scenario}"
        write_outputs(output_directory, plan, statistics)
    except (OSError, ValueError, KeyError) as error:
        parser.exit(1, f"Could not run scenario {args.scenario}: {error}\n")

    print(f"Scenario {args.scenario}: simulation completed; plan validation passed.")
    print(format_statistics(statistics))
    print(f"Saved plan and statistics in {output_directory}")
