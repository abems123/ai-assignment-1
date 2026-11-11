# Development notes

## Prompt starting this coding session

The text below records this session's implementation request exactly. If an
earlier substantive prompt was used to design the assignment, include that
earlier prompt as the first relevant prompt in the report instead.

```text
Read `Assignment1.pdf` and the provided scenarios carefully, then help me build an initial working version of the Emergency Response System.

I want to make the important design decisions myself, especially regarding the AI algorithms, simulation behavior, assumptions, and planning strategies. Whenever a decision is not explicitly specified in the assignment, explain the available options briefly, give your recommendation, and let me choose before implementing it.

Keep the implementation simple, modular, and easy to understand. Follow the assignment requirements exactly, avoid unnecessary complexity, and work with me step by step rather than implementing the entire solution at once.

I wanna be able to run the program as follows: python3 run.py X with X being 1,2 or 3 corresponding to the scenario number.
```

## Step 1: read inputs and add the entry point

The assistant (ChatGPT/Codex) read all eight assignment pages, the scenario README,
and all seven input files in each of the three scenarios. It implemented only
the requested scenario selection and data loading. At that stage, all AI and
simulation choices remained pending the student's decisions.

Inspection found:

| Scenario | Locations | Directed roads | Responders | Incidents | Road reports | Traffic observations | Observed directed roads |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 5 | 14 | 4 | 7 | 18 | 140 | 14 |
| 2 | 12 | 30 | 10 | 12 | 42 | 15 | 3 |
| 3 | 26 | 60 | 10 | 20 | 42 | 100 | 10 |

Read-only checks confirmed valid location and road references, unique graph
identifiers and directed edges, consecutive observation numbers per directed
road, and normalized probability distributions in all three scenarios.

These checks concern input consistency. They do not establish plan validity,
because allocation and routing have not yet been implemented.

The loader was then run successfully using scenario numbers 1, 2, and 3. Missing,
non-numeric, and out-of-range scenario arguments were rejected. Launching the
script from another working directory also succeeded. A byte comparison confirmed
that every copied scenario input is identical to the supplied ZIP contents.

## Decisions

### 1. Execution model: inferred conditions (approved)

The assistant offered two alternatives: calculate travel under inferred road and
traffic conditions, or sample hidden true conditions and simulate route failures.
It recommended inferred conditions for a simpler, reproducible initial version.
The student's exact reply was: `A`.

Travel and later performance statistics will therefore use the model's estimates.
There will be no separately sampled ground-truth road states in this version.
Results will demonstrate feasibility under the chosen estimates; they cannot
establish that routes would succeed under unknown real road conditions.

This choice does not yet decide how Bayesian probabilities are converted to road
statuses or costs, how HMM traffic affects travel, or which algorithms to use.

As preparation, the assistant added `travel_times.py` with only the assignment's
specified rules: distance/speed for Open, 1.5 times that for Congested, and an
infinite cost for Blocked. This helper takes a status as an explicit argument;
it does not select one from probabilities. Traffic effects are still pending.

Verification: the Scenario 1 road H1 -> N4 (340 metres at 30 metres/second)
gave 11.333333333333334 seconds for Open, 17 seconds for Congested, and infinite
cost for Blocked. All three scenario commands still ran successfully.

### 2. Road-status routing policy: most likely status (approved)

The assistant offered two alternatives: use the most likely status (MAP), or
combine a blocked-probability threshold with conditional expected travel time
among passable states. It recommended MAP for a simple initial version that is
easy to understand and defend. The student's exact reply was: `1`.

The routing policy will select the status with the highest posterior probability.
Open receives normal travel time, Congested receives 1.5 times normal travel time,
and Blocked is unusable. For example, probabilities of Open 0.6, Congested 0.3,
and Blocked 0.1 select Open. The 0.1 blockage probability remains a limitation of
the estimate; the MAP routing cost does not retain that risk.

The assistant initially added the selection helper in `bayesian.py`. At that
stage, it accepted supplied probabilities; report-based inference still awaited
the student's decisions on report independence and missing weather. A tie policy
had not been chosen, so tied maxima caused an explicit error at that stage.

Verification: supplied distributions selecting each of Open, Congested, and
Blocked were passed through the selection and road-time helpers. On a 300 metre
road at 15 metres/second they produced costs of 20 seconds, 30 seconds, and
infinity, respectively. An exact Open/Blocked tie produced the pending-policy
error instead of an arbitrary choice. All three scenario commands still ran.

### 3. Bayesian assumptions and tie policy (approved)

The assistant proposed combining all reports with conditionally independent
errors given the true road status, marginalizing over the supplied weather prior
when local weather is unknown, and choosing the most restrictive status in an
exact tie. The alternatives were using one report source, assuming a particular
weather condition, and choosing the least restrictive tied status. The student's
exact reply, including Markdown, was: `**Use all three recommendations**`.

All three recommendations are now implemented in `bayesian.py`. Each directed
road has its own report group and local weather. Unknown weather uses the
weighted weather mixture, which yields Open 0.685, Congested 0.18, and Blocked
0.135 with the supplied tables. Each status's weight is multiplied by the
likelihood of each report and then the weights are normalized. The selected MAP
status uses the tie preference Blocked, Congested, Open.

`run.py` now runs Bayesian inference and prints estimated status counts. It still
does not generate a response plan or performance statistics: search, HMM traffic,
allocation, and simulation choices remain open.

Six reproducible checks in `tests/test_bayesian.py` passed. The multi-report
reference example is Scenario 1 N1 -> N2: Rain, Citizen=Blocked, Police=Blocked,
Sensor=Congested. Its unnormalized weights are 0.00012, 0.00384, and 0.00441,
so the posterior is Open 12/837, Congested 384/837, Blocked 441/837. The selected
status is Blocked. Other checks cover known local weather, weather marginalization,
independent road directions, restrictive ties, and impossible evidence.

All three command-line runs succeeded. Every posterior was normalized and within
[0, 1], and the input probability tables were not mutated. Status counts were:

| Scenario | Open | Congested | Blocked |
| --- | --- | --- | --- |
| 1 | 8 | 2 | 4 |
| 2 | 19 | 9 | 2 |
| 3 | 47 | 11 | 2 |

Limitations: copied or correlated reports can make the independence model too
confident. MAP costs discard residual risk. No ground-truth road states were
provided, so these checks establish inference consistency, not real-world road
accuracy or plan feasibility.

In preparation for discussing A* routing, the assistant checked that each supplied
road distance is at least the straight-line distance between its endpoints. This
supports a straight-line travel-time lower bound with appropriate speed and delay
scaling. At that point, no search algorithm had been selected or implemented.

### 4. Search algorithm: uniform-cost search (approved)

The assistant offered uniform-cost search and A*. It recommended uniform-cost
search for the initial version because it is simple and needs no heuristic.
The student's exact reply was: `1`.

`routing.py` now builds a directed adjacency list using the approved MAP road
statuses. Open and Congested costs follow the assignment's distance, speed, and
1.5 congestion factor. Blocked roads are excluded. HMM traffic factors have not
been chosen or applied yet.

Uniform-cost search expands the lowest accumulated travel-time entry using
Python's `heapq`. Better paths update the stored time and parent link; superseded
queue entries are skipped. The search stops when the goal is popped, not when
first discovered. It then reconstructs the path using parent links. Same-location
trips cost zero, and unreachable destinations return an empty path and infinite
time. Equal-cost alternatives keep the first discovered route; queue ties use
location identifiers for deterministic behavior.

The existing `python3 run.py X` commands still work. An optional `--route START
GOAL` argument exposes routing for inspection without selecting an incident or
responder. It reads no future incident information. The entry point still awaits
HMM, allocation, and simulation choices before producing the required plan and
performance statistics.

Verification: all fourteen tests passed (six Bayesian tests and eight routing
tests). The routing tests include weighted alternatives, better paths to frontier
nodes, blocked and congested roads, zero-length trips, unreachable destinations,
and invalid endpoints. An independent Floyd-Warshall reference agreed with UCS
for all 845 location pairs over the three supplied scenarios. Returned paths also
passed directed-edge, blocked-road, and accumulated-cost checks.

All three scenario commands succeeded, yielding 10, 28, and 58 usable directed
roads. In Scenario 1, `--route N1 N2` returned N1 -> H1 -> N2 in 78.600 seconds,
while `--route N2 N1` returned N2 -> N1 in 77.500 seconds. The asymmetry follows
the different road reports in the two directions. A same-node route returned zero
seconds, and an unknown endpoint was rejected cleanly.

The verification establishes routing optimality under the current road-cost
estimates. It does not yet cover traffic-adjusted travel times, dynamic replanning,
or responder/incident operational constraints; those components are still pending.

### 5. HMM inference method: forward filtering (approved)

The assistant offered forward filtering, which provides a traffic probability
distribution after the latest historical observation, and Viterbi, which finds
the single most likely hidden-state history. It recommended filtering because
the planner needs traffic beliefs. The student's exact reply was: `1`.

`hmm.py` now groups observations by directed road, sorts each sequence numerically
by `observation_nr`, and filters it using that scenario's own probability tables.
The standard HMM initialization uses `initial` as the prior for the first hidden
state, followed directly by its first emission update. Each later observation
first gets one transition prediction and then an emission update. Every update
is normalized. The code uses the supplied matrices; it does not learn new ones
from the observations. Observation numbers are sequence order, not seconds.

The module returns historical beliefs only for observed roads. It does not fill
unobserved roads, map history to simulation time zero, advance beliefs during a
simulation, or convert traffic probabilities to road costs. These planning
choices remain with the student. The standalone empty-sequence filter returns
a copy of `initial`, the mathematical prior before any observations; no missing-road
planning fallback has been adopted by doing so.

`run.py` computes and reports the number of historical road beliefs. The existing
route query continues to use road-status costs only until the traffic policy is
selected. Allocation and simulation are still pending.

Verification: seven HMM tests were added, and all twenty-one project tests passed.
For Scenario 1's model and a first observation Low, the hand-calculated weights
are 0.51, 0.03, and 0.002. The posterior is Low 255/271, Medium 15/271, High 1/271.
For observations Low then High, the second posterior is Low 2063/14203,
Medium 5660/14203, High 6480/14203. An independent reference enumerates all 81
possible hidden histories for a four-observation sequence and agrees with the
filter using each scenario's model.

Other checks cover shuffled observations, separate directions, unobserved-road
omission, empty history, impossible evidence, normalized beliefs, and unchanged
input tables and rows. All three scenario commands succeeded, producing beliefs
for 14 of 14, 3 of 30, and 10 of 60 directed roads, respectively. The Scenario 1
N1-to-N2 route remained 78.600 seconds because traffic-cost integration is pending.

Example historical beliefs, rounded to six decimal places:

| Scenario | Road | Low | Medium | High |
| --- | --- | --- | --- | --- |
| 1 | H1 to N1 | 0.871452 | 0.123028 | 0.005520 |
| 2 | H2 to N8 | 0.010113 | 0.282220 | 0.707666 |
| 3 | N16 to N17 | 0.001865 | 0.074845 | 0.923290 |

These values concern the end of historical sequences; applying them to current
or future simulation conditions requires the next modeling decisions.

### 6. Traffic timing, multipliers, and missing-road fallback (approved)

The assistant proposed treating each final historical belief as the estimate at
simulation time zero and keeping it fixed, using expected multipliers Low 1.0,
Medium 1.25, High 1.5 multiplied by road-status time, and using the supplied
initial distribution for roads without observations. Alternatives were evolving
beliefs with a chosen time-step mapping, most-likely-level or different traffic
factors, and a stationary fallback distribution. The student's exact reply,
including Markdown, was: `**Use all three recommendations**`.

All three recommendations are implemented. `initialize_traffic_beliefs` copies
each observed road's final posterior with no extra prediction and copies the
scenario's initial distribution for every unobserved road. The routing graph is
built once from these beliefs; the selected policy will reuse them as simulation
time advances. No seconds-per-HMM-step parameter or stationary calculation is used.

`expected_traffic_multiplier` uses the full three-state distribution. For example,
Low 0.6, Medium 0.3, High 0.1 yields a multiplier of 1.125. The resulting travel
time multiplies the road-status time by this traffic factor. Congested plus
certain High traffic gives 2.25 times normal time. Blocked roads stay unusable.
The graph builder requires traffic beliefs explicitly, so production routing
cannot accidentally omit the approved traffic policy.

The existing entry point now integrates Bayesian road inference, historical HMM
filtering, complete traffic initialization, and traffic-adjusted UCS. Responder
allocation and simulation are still pending the student's decisions, so the
required plan and performance files are not generated at this stage.

Verification: all twenty-seven tests passed. Six new checks cover the probability
weighted factor, multiplicative delays, inability of Low traffic to reopen a
Blocked road, historical initialization without prediction or aliasing, the
scenario-specific initial fallback, and a route change caused by traffic. The
independent all-pairs reference now checks traffic-adjusted graph costs and
still agrees with UCS for all 845 pairs across the supplied scenarios.

All three normal scenario commands succeeded. Fallback counts are 0, 27, and 50
directed roads in scenarios 1, 2, and 3. Scenario 2's fallback factor is 1.1625.
Scenario 1 route inspection returns N1 -> H1 -> N2 in 79.399 seconds and N2 -> N1
in 78.973 seconds; the same-node route remains zero. Calculations retain full
precision, with three decimal places used only for CLI display.

Limitations: fixed beliefs do not respond to later traffic changes; the selected
traffic factors are assumptions rather than calibrated measurements. Multiplying
road and traffic factors can count congestion twice if they describe the same
cause. The report should distinguish these model-based times from true outcomes.

The pending-decisions list was also clarified: the assignment defines the deadline
as the latest time a responder must arrive, so allocation must respect arrival
deadlines. Allocation objectives, simulation policies, and the handling of
unassigned incidents in statistics still need student choices.
