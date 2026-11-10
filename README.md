# Emergency Response System

## Current stage: Bayesian road inference

These are the initial components, not the completed emergency-response planner.
The command loads all seven files belonging to the selected scenario, estimates
the status of every directed road, and prints an input and road-status summary.
Search, HMM traffic estimation, simulation, allocation, plan validation, and output
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

## Files

- `run.py`: validates the scenario number and starts the program.
- `scenario_loader.py`: reads the JSON and CSV files into a `Scenario` object.
- `bayesian.py`: computes road-status probabilities from local weather and noisy
  reports, and selects a status using the approved MAP policy.
- `travel_times.py`: calculates travel time for a supplied road status using the
  assignment's Open, Congested, and Blocked rules. It is ready for the routing
  component; the entry point does not yet call a planner.
- `Scenarios/`: the complete supplied inputs, unchanged.
- `development_notes.md`: development prompt, inspection findings, and choices
  to record as development proceeds.
- `tests/test_bayesian.py`: checks the inference against hand calculations and
  directed-road evidence.

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

## Verification

Run the six Bayesian checks from this project directory:

```bash
python3 -m unittest discover -s tests -v
```

They cover a hand-calculated multi-report posterior, conditioning on local
weather, missing-weather marginalization, separate road directions, restrictive
ties, and impossible evidence. All six passed. All three scenario commands also
ran successfully, with normalized beliefs for every directed road and unchanged
input probability tables.

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

1. Search algorithm and how HMM traffic beliefs affect routing costs.
2. HMM inference method, historical-to-current prediction, traffic cost mapping,
   and treatment of roads without traffic observations.
3. Allocation algorithm, priority policy, and whether late arrivals are allowed.
4. Simulation clock, responder location after service, replanning/preemption,
   and stopping rules.
5. Statistics definitions and the scope of plan validation.

We will discuss alternatives and record the student's choice before implementing
each behavior.
