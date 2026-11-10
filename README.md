# Emergency Response System

## Current stage: Bayesian road inference and uniform-cost routing

These are the initial components, not the completed emergency-response planner.
The command loads all seven files belonging to the selected scenario, estimates
the status of every directed road, and builds a weighted routing graph. An optional
route query lets you inspect the fastest estimated path between two locations.
HMM traffic estimation, simulation, allocation, plan validation, and output
generation will be added after the student chooses their behavior.

The selected model uses inferred road and traffic conditions to calculate travel.
Performance results will describe behavior under those estimates. We will not
sample hidden true road states or simulate failures against a separate ground
truth. Bayesian report-based inference is implemented; the HMM is still pending.

For road routing, the student selected the most likely road status (MAP): use the
status with the largest posterior probability, then apply its travel-time rule.
This discards the other probabilities when assigning the road's routing cost.
Exact ties choose the most restrictive tied status: Blocked, then Congested,
then Open.

Use Python 3.9 or newer. There are no external dependencies.

Extract the project, open a terminal in this directory, and run:

```bash
python3 run.py 1
python3 run.py 2
python3 run.py 3
```

Each command currently prints a scenario and inferred-road summary. It does not yet generate
`plan.json` or `statistics.txt`. These will be produced by the same commands once
the planning components are implemented.

To inspect a route without making a responder assignment:

```bash
python3 run.py 1 --route N1 N2
```

This produces the path `N1 -> H1 -> N2` with an estimated travel time of 78.600
seconds. These costs currently include road status only; HMM traffic adjustments
are still pending. Travel-time rounding is for display only.

## Files

- `run.py`: validates the scenario number and starts the program.
- `scenario_loader.py`: reads the JSON and CSV files into a `Scenario` object.
- `bayesian.py`: computes road-status probabilities from local weather and noisy
  reports, and selects a status using the approved MAP policy.
- `travel_times.py`: calculates travel time for a supplied road status using the
  assignment's Open, Congested, and Blocked rules.
- `routing.py`: builds the directed weighted graph and finds minimum-time paths
  using uniform-cost search.
- `Scenarios/`: the complete supplied inputs, unchanged.
- `development_notes.md`: development prompt, inspection findings, and choices
  to record as development proceeds.
- `tests/test_bayesian.py`: checks the inference against hand calculations and
  directed-road evidence.
- `tests/test_routing.py`: checks weighted search, blocked and congested roads,
  unreachable destinations, and optimal route costs on all three scenarios.

CSV field values remain strings at this stage. Numeric conversion will happen
explicitly in the components that use them. JSON numbers retain their supplied
numeric types. Both road directions remain separate; observations and reports
are not merged across directions.

## Bayesian reasoning

For known local weather, start with the supplied road-status distribution for
that weather. For unknown weather, average those distributions using
`weather_prior`. Reports from other roads do not supply a road's missing weather.

Multiply each status's prior probability by the likelihood of every report under
that true status. Reports are assumed conditionally independent given the true
status. The report tables are indexed as `[true_status][reported_status]`.
Divide the three resulting weights by their sum to obtain the posterior.
Choose the most likely status, with restrictive tie handling as described above.

All road reports are available at time zero. Conflicting weather within one
directed road's reports and impossible evidence are reported as input errors.

The independence assumption can overstate confidence if reports copy one another.
MAP routing also discards the remaining uncertainty when selecting a road cost.
Without ground-truth road states, these results cannot measure estimation accuracy.

## Routing

The student selected uniform-cost search. Each usable directed road receives a
cost equal to its estimated travel time in seconds. Roads inferred as Blocked are
excluded. The search uses a priority queue to expand the location with the lowest
accumulated travel time, keeping a better route whenever one is found. It finishes
when the goal is removed from that queue at minimum cost. Parent links reconstruct
the selected path. No heuristic is needed.

The routing function returns a path and travel time. Staying at the same location
returns a one-node path and zero seconds. An unreachable destination returns an
empty path and infinite time. Unknown endpoints are rejected.

Equal-cost routes retain the first route discovered; priority-queue ties use
location identifiers. This is deterministic and does not change the minimum cost.
The optional route query uses endpoints supplied by the user; it does not select a
responder or look ahead at future incidents.

## Verification

Run the fourteen Bayesian and routing checks from this project directory:

```bash
python3 -m unittest discover -s tests -v
```

They cover a hand-calculated multi-report posterior, conditioning on local
weather, missing-weather marginalization, separate road directions, restrictive
ties, and impossible evidence. Routing checks cover weighted alternatives,
improved frontier entries, road congestion and blockage, same-location trips,
unreachable destinations, and unknown endpoints.

All fourteen checks passed. Route costs were compared against an independent
Floyd-Warshall reference for all 845 source/destination pairs across the three
scenarios. Returned paths were checked for contiguous directed roads, exclusion
of Blocked roads, and agreement between summed road costs and reported travel time.
All three scenario commands also ran successfully. Their routing graphs contain
10, 28, and 58 usable directed roads, respectively.

| Scenario | Estimated Open | Estimated Congested | Estimated Blocked |
| --- | --- | --- | --- |
| 1 | 8 | 2 | 4 |
| 2 | 19 | 9 | 2 |
| 3 | 47 | 11 | 2 |

These counts concern inferred directed-road statuses. Incident performance
statistics will follow after allocation and simulation are implemented.

## Requirements already specified by the sources

- Distances and coordinates are metres; road speeds are metres/second. All
  simulation times and durations are seconds, including fractional seconds.
- Incidents become known at their timestamps. Deadlines are absolute times for
  **arrival**, not completion. Handling starts after arrival and occupies the
  responder for `time_required` seconds.
- Use each responder's listed capabilities and availability.
- Road statuses are Open (normal travel time), Congested (1.5 times normal),
  and Blocked (unusable).
- Road reports are available at time 0. Reported weather is local to that road.
- Traffic observations are historical and available before time 0.
  `observation_nr` orders a separate sequence for each directed road; it is not
  a simulation timestamp.
- Traffic levels Low/Medium/High are distinct from road statuses. The scenario
  README explicitly leaves their influence on planning to the student.
- Each scenario's own probability tables must be read. Scenario 2's traffic
  model differs from the models in scenarios 1 and 3.
- The complete system must use course methods for search, Bayesian reasoning,
  constraint-based allocation, and Hidden Markov Models.
- The final `plan.json` must be a JSON list of objects with `responder_id`,
  `incident_id`, `path`, and assignment start `time`.
- The final `statistics.txt` must include incidents handled, responders used,
  average response time, and percentage of deadlines met. Definitions and the
  treatment of unhandled incidents must be documented.

## Design decisions still open

The following are not implemented or silently chosen:

1. HMM inference method, historical-to-current prediction, traffic cost mapping,
   and treatment of roads without traffic observations.
2. Allocation algorithm, priority policy, and whether late arrivals are allowed.
3. Simulation clock, responder location after service, replanning/preemption,
   and stopping rules.
4. Statistics definitions and the scope of plan validation.

We will discuss alternatives and record the student's choice before implementing
each behavior.
