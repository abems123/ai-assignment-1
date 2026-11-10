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
scaling. No search algorithm has been selected or implemented yet.
