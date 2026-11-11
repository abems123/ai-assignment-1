# Emergency Response System

## Current stage: Bayesian inference, HMM traffic, and traffic-adjusted routing

These are the initial components, not the completed emergency-response planner.
The command loads all seven files belonging to the selected scenario, estimates
the status of every directed road, and builds a weighted routing graph. An optional
route query lets you inspect the fastest estimated path between two locations.
The HMM filters historical traffic observations separately for each observed road.
The approved traffic policy initializes a fixed belief for every road and uses
its probability-weighted delay in routing. Simulation, allocation, plan validation,
and output generation will follow the student's choices.

The selected model uses inferred road and traffic conditions to calculate travel.
Performance results will describe behavior under those estimates. We will not
sample hidden true road states or simulate failures against a separate ground
truth. Bayesian road inference, HMM filtering, and their combined routing costs
are implemented. Historical beliefs are treated as the estimates at simulation
time zero and remain fixed under the selected policy. Roads without observations
use that scenario's supplied `initial` distribution.

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

Each command prints scenario, inferred-road, and historical-traffic summaries.
It does not yet generate
`plan.json` or `statistics.txt`. These will be produced by the same commands once
the planning components are implemented.

To inspect a route without making a responder assignment:

```bash
python3 run.py 1 --route N1 N2
```

This produces the path `N1 -> H1 -> N2` with an estimated travel time of 79.399
seconds, including road-status and traffic delays. Travel-time rounding is for
display only.

## Files

- `run.py`: validates the scenario number and starts the program.
- `scenario_loader.py`: reads the JSON and CSV files into a `Scenario` object.
- `bayesian.py`: computes road-status probabilities from local weather and noisy
  reports, and selects a status using the approved MAP policy.
- `travel_times.py`: calculates travel time for a supplied road status using the
  assignment's road-status rules and the selected expected traffic multiplier.
- `routing.py`: builds the directed weighted graph and finds minimum-time paths
  using uniform-cost search.
- `hmm.py`: filters each directed road's ordered historical traffic sequence using
  that scenario's initial, transition, and emission probabilities, then initializes
  the fixed traffic model for all roads.
- `Scenarios/`: the complete supplied inputs, unchanged.
- `development_notes.md`: development prompt, inspection findings, and choices
  to record as development proceeds.
- `tests/test_bayesian.py`: checks the inference against hand calculations and
  directed-road evidence.
- `tests/test_routing.py`: checks weighted search, blocked and congested roads,
  unreachable destinations, and optimal route costs on all three scenarios.
- `tests/test_hmm.py`: checks filtering against hand calculations and independent
  enumeration of hidden histories, plus sequence grouping and scenario models.
- `tests/test_traffic_costs.py`: checks fixed-belief initialization, missing-road
  priors, traffic multipliers, combined delays, and traffic-driven route changes.

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
cost equal to its estimated travel time in seconds, combining road-status and
traffic effects. Roads inferred as Blocked are
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

## Historical traffic filtering

The student selected forward filtering. Traffic levels are Low, Medium, and High;
they are distinct from the Open, Congested, and Blocked road statuses.

For each observed directed road, sort its observations by numeric `observation_nr`.
Use the supplied `initial` distribution as the prior for the first hidden state.
Multiply by the first observation's emission probabilities and normalize. Before
each following observation, predict the next distribution using the transition
matrix, then multiply by that observation's emission probabilities and normalize.
Transition rows are previous states and columns are next states. Emission rows
are hidden states and columns are observations.

The result is a distribution after the last historical observation. No new
transition or emission probabilities are trained from the CSV. The ordinal
observation numbers are not interpreted as seconds or simulation timestamps.
The filter uses each scenario's own probability file; Scenario 2's model differs.

Only roads with observations receive a historical belief. The pure filtering
function returns the supplied prior for an empty sequence, while the historical
inference function leaves unobserved roads absent. The separate planning
initializer then covers every road: it copies the last historical belief when
available and otherwise copies that scenario's `initial` distribution. No extra
HMM prediction is made between the end of history and simulation time zero.

The selected model keeps these initialized beliefs fixed for the simulation.
It does not assign a duration in seconds to historical HMM steps or advance
traffic beliefs as simulation time passes. The routing graph is built once from
these fixed beliefs. Allocation and the simulation clock are still pending.

Examples below are beliefs after each road's last historical observation,
rounded to six decimal places. Internal computations retain full precision.

| Scenario | Directed road | Low | Medium | High |
| --- | --- | --- | --- | --- |
| 1 | H1 to N1 | 0.871452 | 0.123028 | 0.005520 |
| 2 | H2 to N8 | 0.010113 | 0.282220 | 0.707666 |
| 3 | N16 to N17 | 0.001865 | 0.074845 | 0.923290 |

## Traffic cost policy

The student approved these multipliers:

| Hidden traffic level | Travel multiplier |
| --- | --- |
| Low | 1.0 |
| Medium | 1.25 |
| High | 1.5 |

For each road, average the multipliers using its full traffic belief:

```text
traffic multiplier = P(Low) * 1.0 + P(Medium) * 1.25 + P(High) * 1.5
estimated travel time = road-status travel time * traffic multiplier
```

The road-status time is distance/speed for Open, multiplied by 1.5 for Congested.
Blocked roads remain excluded regardless of traffic. With probabilities 0.6,
0.3, and 0.1, the traffic multiplier is 1.125. A Congested road with certain High
traffic takes 2.25 times normal travel time under this selected model.

All 14 roads in Scenario 1 have observations. Scenario 2 uses the initial prior
for 27 roads; Scenario 3 uses it for 50 roads. Scenario 2's fallback multiplier
is 1.1625, using its own initial distribution rather than another scenario's model.

The numerical traffic factors are chosen assumptions rather than calibrated
measurements. Fixed beliefs ignore later traffic changes. Multiplying road and
traffic delays can count congestion twice if both estimates describe the same
underlying delay; this is a limitation of the selected initial model.

## Verification

Run the twenty-seven Bayesian, routing, HMM, and traffic-cost checks from this project directory:

```bash
python3 -m unittest discover -s tests -v
```

They cover a hand-calculated multi-report posterior, conditioning on local
weather, missing-weather marginalization, separate road directions, restrictive
ties, and impossible evidence. Routing checks cover weighted alternatives,
improved frontier entries, road congestion and blockage, same-location trips,
unreachable destinations, and unknown endpoints.

All twenty-seven checks passed. Traffic-adjusted route costs were compared against an independent
Floyd-Warshall reference for all 845 source/destination pairs across the three
scenarios. Returned paths were checked for contiguous directed roads, exclusion
of Blocked roads, and agreement between summed road costs and reported travel time.
All three scenario commands also ran successfully. Their routing graphs contain
10, 28, and 58 usable directed roads, respectively.

The seven HMM checks cover the first observation, a two-observation hand
calculation, comparison with exhaustive hidden-history enumeration, sequence
ordering and direction, each scenario's own model, empty history, and impossible
evidence. Filtering produced normalized historical beliefs for 14, 3, and 10
directed roads in the three scenarios, without changing input tables or rows.

Six traffic-cost checks verify use of the full probability distribution, combined
road/traffic delays, Blocked-road exclusion, direct copying of historical beliefs
without another prediction, scenario-specific fallback priors, and a case where
traffic changes the fastest route. All three scenario commands also run with the
integrated traffic model. Scenario 1 route queries return 79.399 seconds for
N1 to N2, 78.973 seconds for N2 to N1, and zero for N1 to N1.

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

1. Allocation algorithm and priority policy, respecting the required arrival deadlines.
2. Simulation clock, responder location after service, replanning/preemption,
   and stopping rules.
3. Statistics definitions and the scope of plan validation.

We will discuss alternatives and record the student's choice before implementing
each behavior.
