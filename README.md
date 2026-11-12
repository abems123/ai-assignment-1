# Emergency Response System

An AI-based decision-support system for dispatching emergency responders after a severe storm. The city is represented as a **directed road graph**. The system estimates uncertain road conditions and traffic, finds routes, assigns suitable responders to incidents, and simulates their work over time.

This project implements the four AI components required by **Artificial Intelligence Practicum — Assignment 1**: search, Bayesian reasoning, constraint-based allocation, and Hidden Markov Models (HMMs).

## Requirements and libraries

- **Python 3.9 or later** (Python 3 is required).
- **No third-party packages are required.** The program uses only Python's standard library.
- Standard-library modules used include `argparse`, `csv`, `json`, `pathlib`, `dataclasses`, `collections`, `heapq`, `math`, `copy`, and `typing`.
- Tests use the standard-library `unittest` module, together with utilities such as `subprocess` and `tempfile`.

There is **no `pip install` step** and no `requirements.txt` is necessary for this version.

## How to run

Extract or clone the repository and open a terminal in the project root (the folder containing `run.py`). Then run one of the three supplied scenarios:

```bash
python3 run.py 1
python3 run.py 2
python3 run.py 3
```

On Windows, use `python run.py 1` if `python3` is not available.

Each run executes the full simulation, validates its generated plan, prints the statistics, and saves:

```text
outputs/scenario1/plan.json
outputs/scenario1/statistics.txt
outputs/scenario2/plan.json
outputs/scenario2/statistics.txt
outputs/scenario3/plan.json
outputs/scenario3/statistics.txt
```

Only the selected scenario's output files are regenerated. Paths are resolved relative to the project root, so the command can also be launched from another working directory by using the path to `run.py`.

To inspect a single route without running the full simulation:

```bash
python3 run.py 1 --route N1 N2
```

This displays the selected route and estimated travel time in **seconds**. Route-inspection mode does not regenerate `plan.json` or `statistics.txt`.

## Project structure

```text
ai-assignment-1/
├── run.py                        # Command-line entry point
├── README.md                     # Installation and execution instructions
├── ers/
│   ├── cli.py                    # Coordinates the full workflow
│   ├── scenario_loader.py        # Loads scenario CSV/JSON files
│   ├── bayesian.py               # Bayesian road-status inference
│   ├── hmm.py                    # HMM forward filtering for traffic
│   ├── travel_times.py           # Road and traffic travel-time estimates
│   ├── routing.py                # Uniform-cost search
│   ├── allocation.py             # Constraint-based responder allocation
│   ├── simulation.py             # Event-driven simulation
│   ├── validation.py             # Independent plan replay and validation
│   └── reporting.py              # JSON plan and text statistics
├── data/scenarios/
│   ├── Scenario1/
│   ├── Scenario2/
│   └── Scenario3/
├── outputs/                       # Generated plans and statistics by scenario
├── tests/                         # Automated tests
└── docs/
    ├── Assignment1.pdf
    └── development_notes.md      # LLM collaboration and design history
```

Each `ScenarioX` directory contains the seven input files: `city_graph.json`, `responders.csv`, `incidents.csv`, `road_reports.csv`, `road_probabilities.json`, `observed_traffic.csv`, and `traffic_probabilities.json`.

## How the system works

1. **Bayesian reasoning (`ers/bayesian.py`):** Estimates each directed road's probabilities of being `Open`, `Congested`, or `Blocked` from weather and noisy citizen, police, and sensor reports. Unknown weather is marginalized using the weather prior. Report errors are assumed conditionally independent given road status. The most probable status (MAP) is used for planning; exact ties prefer `Blocked`, then `Congested`, then `Open`.
2. **HMM (`ers/hmm.py`):** Performs forward filtering on each directed road's historical traffic observations. The supplied initial distribution is updated with the first observation; subsequent observations are preceded by a transition prediction. Observations are ordered by `observation_nr`, which is **not** a simulation timestamp. Roads without observations use the scenario's supplied initial traffic distribution.
3. **Travel-time estimation (`ers/travel_times.py`):** Converts road and traffic beliefs into fixed estimated road costs, as detailed below.
4. **Search (`ers/routing.py`):** Uses Uniform-Cost Search (Dijkstra-style search with a priority queue) to find the minimum-cost route on the directed graph. Roads estimated as `Blocked` are excluded.
5. **Constraint-based allocation (`ers/allocation.py`):** Uses plain backtracking to assign currently available responders to known incidents. It checks required capabilities, responder availability, reachable routes, and absolute arrival deadlines. A responder can receive only one assignment in a dispatch batch, and incidents may remain unassigned. Among feasible combinations it maximizes the numbers handled in this order: **Critical, High, Medium, Low**; ties are broken by minimizing total response time.
6. **Simulation (`ers/simulation.py`):** Advances directly to incident appearances and responder-release events. New incidents are not considered before their timestamps. Pending incidents are reconsidered when events occur. Assigned responders cannot be interrupted and remain busy for travel plus incident-handling time. After completion they become available at the incident location; initially busy responders become free at their supplied locations. There is no automatic ambulance trip to a hospital or return-to-base journey.
7. **Validation and output (`ers/validation.py`, `ers/reporting.py`):** Replays the plan, checks constraints independently, recalculates timings, and writes the required output files.

### Travel-time rules and assumptions

All distances are in **metres**, speeds in **metres/second**, and times in **seconds**. The assignment specifies these road-status rules:

| Inferred road status | Road-status travel time |
| --- | --- |
| Open | `distance / speed` |
| Congested | `1.5 * distance / speed` |
| Blocked | Unusable (infinite cost) |

The project additionally uses **chosen**, not assignment-prescribed, HMM traffic multipliers:

| Traffic level | Multiplier |
| --- | ---: |
| Low | 1.00 |
| Medium | 1.25 |
| High | 1.50 |

The expected HMM multiplier uses the **full traffic probability distribution**:

```text
expected_multiplier = P(Low)*1.00 + P(Medium)*1.25 + P(High)*1.50
```

**The current implementation takes the larger of the two estimated delays; it does not multiply the road-status and HMM multipliers together:**

```text
base_time       = distance / speed
status_time     = base_time * (1.0 if Open else 1.5 if Congested)
traffic_time    = base_time * expected_multiplier
estimated_time  = max(status_time, traffic_time)
```

`Blocked` remains unusable regardless of HMM traffic. This `max` policy is a **modeling choice** intended to avoid stacking potentially overlapping congestion penalties. It is not explicitly required by the assignment. Both road-status and HMM traffic estimates stay **fixed during simulation**; the program does not sample actual hidden road states or predict new traffic steps as simulation seconds pass.

### Deadline and scheduling semantics

An incident's timestamp is when it becomes known. Its deadline is an **absolute latest arrival time**, not a time allowance after appearance. The handling duration starts upon arrival; completion is allowed after the arrival deadline.

```text
arrival_time     = assignment_start_time + route_travel_time
completion_time  = arrival_time + incident_handling_duration
response_time    = arrival_time - incident_timestamp
```

An assignment is feasible only if `arrival_time <= incident_deadline` and all other operational constraints hold. The CSP optimizes each immediate dispatch batch, not the entire future incident stream.

## Output formats

### `plan.json`

A JSON array with **exactly** the four fields required by the assignment for each assignment:

```json
[
  {
    "responder_id": "R1",
    "incident_id": "I2",
    "path": ["N1", "H1", "N2"],
    "time": 0.0
  }
]
```

`time` is the simulation time at which the responder **starts the assignment**, not the arrival time. Each path lists the directed road-graph locations visited.

### `statistics.txt`

The statistics file includes:

- **Incidents handled:** Number of incidents with a completed assignment.
- **Responders used:** Number of distinct responders dispatched at least once.
- **Average response time:** Mean `(arrival time - incident timestamp)` among **handled** incidents, in seconds; `N/A` when none are handled.
- **Deadlines met:** `(on-time handled incidents / all incidents) * 100%`. **Unhandled incidents count as deadline misses**; `N/A` when the scenario has no incidents.
- **Additional information:** Unhandled count and incident IDs.

The program calculates statistics from the **validated, replayed plan**, not from an unverified prediction.

## Testing and validation

Run the tests from the project root:

```bash
python3 -m unittest discover -s tests -v
```

The test suite covers Bayesian inference, HMM filtering, traffic costs, routing, CSP allocation, event-driven simulation, plan validation, reporting, and command-line execution. The plan validator checks valid road directions and endpoints, responder capabilities and availability, incident visibility, arrival deadlines, repeated assignments, and overlapping responder work.

**Current test-suite issue (verified against this upload):** 61 tests run, **60 pass and 1 fails**. `tests/test_traffic_costs.py::test_road_congestion_and_high_traffic_multiply` still expects the **previous multiplicative** travel-time policy (`45.0 s`), while the current `max` policy correctly returns `30.0 s` for that test case. The test expectation needs to be updated to match the adopted policy; this README does not modify the test code. All three scenario runs complete and their generated plans pass validation.

## Results on supplied scenarios

Results reproduced by running the uploaded code with its current `max` travel-cost policy:

| Scenario | Handled | Unhandled | Responders used | Average response time | Deadlines met |
| --- | ---: | ---: | ---: | ---: | ---: |
| 1 | 6 / 7 | 1 | 4 | 89.765 s | 85.714% |
| 2 | 9 / 12 | 3 | 7 | 36.982 s | 75.000% |
| 3 | 12 / 20 | 8 | 7 | 628.279 s | 60.000% |

These percentages include unhandled incidents in the denominator. A low average response time alone does not imply that most incidents were handled.

## Limitations and design choices

- Road accessibility and travel costs are based on **inferred** conditions, not observed ground truth. MAP can discard substantial uncertainty about blocking.
- Reports are treated as conditionally independent; correlated reports may overstate confidence.
- Historical HMM beliefs and routing costs remain fixed for the entire simulation. Observation numbers do not specify elapsed simulation seconds.
- The added traffic multipliers and `max` combination rule are assumptions. Different policies can produce very different deadline results.
- Backtracking maximizes the quality of the **current** dispatch batch, not global performance across future incidents. It can also become expensive for larger instances.
- Responder behavior omits patient transport, automatic return-to-base trips, and job interruption. Real-world emergencies may require these.
- Validation checks feasibility **under the chosen estimated costs**. It does not establish true road conditions, global optimality, or real-world success.

## Assignment submission

As required by `docs/Assignment1.pdf`, the GitHub repository should contain all source code, scenario data, this README, and the runnable `run.py` entry point. The **separate submission** is `report.pdf` (maximum three content pages, excluding the title page; one extra page for relevant LLM prompts is permitted). The report must prominently link to the GitHub repository and discuss the approach, AI concepts, LLM collaboration (including the exact first substantive prompt), testing, results, and critical reflection. Invite the two instructors specified in the assignment to the repository before submitting.

The accompanying `docs/development_notes.md` contains development decisions and the LLM interaction record to support the report and oral defence; it does not replace the required PDF report.
