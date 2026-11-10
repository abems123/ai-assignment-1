"""Read scenario files without making planning or simulation assumptions."""

import csv
import json
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Scenario:
    city_graph: dict
    responders: list[dict[str, str]]
    incidents: list[dict[str, str]]
    road_reports: list[dict[str, str]]
    road_probabilities: dict
    traffic_observations: list[dict[str, str]]
    traffic_probabilities: dict


def read_json(path: Path) -> dict:
    with path.open(encoding="utf-8-sig") as stream:
        return json.load(stream)


def read_csv(path: Path) -> list[dict[str, str]]:
    # DictReader handles the blank lines in the supplied CSV files.
    # Keep CSV values as strings here; the components that use them will parse
    # their numeric fields explicitly when those components are added.
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def load_scenario(directory: Path) -> Scenario:
    """Load this scenario's own seven input files, including its probability tables.

    Reading the incident stream here is only input loading. The future simulation
    must reveal incidents to the allocator only when their timestamps are reached.
    Road directions and all supplied values are preserved.
    """
    return Scenario(
        city_graph=read_json(directory / "city_graph.json"),
        responders=read_csv(directory / "responders.csv"),
        incidents=read_csv(directory / "incidents.csv"),
        road_reports=read_csv(directory / "road_reports.csv"),
        road_probabilities=read_json(directory / "road_probabilities.json"),
        traffic_observations=read_csv(directory / "observed_traffic.csv"),
        traffic_probabilities=read_json(directory / "traffic_probabilities.json"),
    )
