"""Uniform-cost search on directed roads weighted by estimated travel time."""

from heapq import heappop, heappush
from math import inf

from travel_times import estimated_travel_time_seconds


def build_routing_graph(city_graph: dict, road_statuses: dict, traffic_beliefs: dict) -> dict:
    """Build an adjacency list, excluding roads inferred as Blocked.

    Each entry is (next_location, travel_seconds). Costs combine the inferred road
    status and the expected traffic multiplier. The graph is fixed for this run.
    """
    graph = {}
    for node in city_graph["nodes"]:
        graph[node["id"]] = []

    for road in city_graph["roads"]:
        start = road["from"]
        goal = road["to"]
        if start not in graph or goal not in graph:
            raise ValueError(f"Road has an unknown endpoint: {start} to {goal}")
        status = road_statuses[(start, goal)]
        cost = estimated_travel_time_seconds(road, status, traffic_beliefs[(start, goal)])
        if cost != inf:
            graph[start].append((goal, cost))
    return graph


def uniform_cost_search(graph: dict, start: str, goal: str) -> tuple[list[str], float]:
    """Return the fastest path and its travel time for non-negative road costs.

    If no route exists, return an empty path and infinite time. The graph must
    contain both endpoints. All calculations keep their full floating precision.
    """
    if start not in graph or goal not in graph:
        raise ValueError("Route endpoints must be locations in the city graph.")

    # A heap removes the entry with the smallest accumulated travel time first.
    frontier = [(0.0, start)]
    best_times = {start: 0.0}
    previous = {}

    while frontier:
        elapsed, current = heappop(frontier)
        if elapsed > best_times[current]:
            continue  # This queue entry was superseded by a faster route.

        # Finish when the goal is removed at minimum cost, not when first seen.
        if current == goal:
            path = [goal]
            while path[-1] != start:
                path.append(previous[path[-1]])
            path.reverse()
            return path, elapsed

        for neighbor, road_time in graph[current]:
            candidate_time = elapsed + road_time
            if candidate_time < best_times.get(neighbor, inf):
                best_times[neighbor] = candidate_time
                previous[neighbor] = current
                heappush(frontier, (candidate_time, neighbor))

    return [], inf
