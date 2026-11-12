# Emergency Response System

A working initial implementation of the emergency-response assignment using
Bayesian road inference, HMM forward filtering, uniform-cost routing, and a
priority-first backtracking CSP. It runs an event-driven simulation, validates
the exported plan, and writes the required plan and statistics files.

## Run

Use Python 3.9 or newer. Everything uses the Python standard library; no packages
need to be installed. Extract the project, open its root folder, and run:

```bash
python3 run.py 1
python3 run.py 2
python3 run.py 3
```

Each command creates or updates `plan.json` and `statistics.txt` in its own
`outputs/scenario1/`, `outputs/scenario2/`, or `outputs/scenario3/` folder.
Outputs are organized by scenario so running another scenario does not erase the
previous result. Input and output paths are relative to the project, independent
of the terminal's working directory.

For a diagnostic route query instead of a full simulation:

```bash
python3 run.py 1 --route N1 N2
```

This prints `N1 -> H1 -> N2`, with an estimated travel time of 79.399 seconds.
Route-query mode does not generate the simulation output files.

## Folder organization

| Location | Contents |
| --- | --- |
| `run.py` | The required entry point |
| `ers/` | All Python implementation modules |
| `data/scenarios/Scenario1/`, `Scenario2/`, `Scenario3/` | The supplied scenario files, unchanged |
| `tests/` | Unit, integration, validation, and command-line checks |
| `docs/development_notes.md` | Exact development prompt, approved decisions, interactions, and findings |
| `outputs/scenario1/`, `scenario2/`, `scenario3/` | Generated plans and statistics; examples for all three are included |

## How the components work

| Module in `ers/` | Responsibility |
| --- | --- |
| `cli.py` | Load the selected scenario, connect the components, validate, and save |
| `scenario_loader.py` | Read the seven input files |
| `bayesian.py` | Infer road-status probabilities from local weather and reports |
| `hmm.py` | Filter each directed road's traffic history and initialize fixed planning beliefs |
| `travel_times.py` | Combine road-status and expected traffic delays |
| `routing.py` | Build the directed weighted graph and run uniform-cost search |
| `allocation.py` | Build feasible domains and optimize one dispatch batch with CSP backtracking |
| `simulation.py` | Process incident and responder-release events over time |
| `validation.py` | Replay the exported plan independently and check operational feasibility |
| `reporting.py` | Export the required JSON schema and calculate the approved statistics |

### Bayesian road inference

Known weather is local to a reported directed road. Its prior is the provided
road-status distribution for that weather. With unknown weather, marginalize
using the supplied weather prior. Multiply each status's prior by the likelihood
of every report and normalize. Report errors are assumed conditionally independent
given the true road status; CPT rows are true statuses and columns reported statuses.

Choose the most likely status (MAP). Exact ties prefer Blocked, then Congested,
then Open. Open uses distance/speed; Congested multiplies that time by 1.5;
Blocked roads are excluded. Opposite directions remain separate.

### HMM traffic and travel costs

Traffic levels Low/Medium/High differ from road statuses. The observation CSV
contains historical sequences available before simulation time zero.
`observation_nr` orders each directed road's sequence; it is not seconds.

Use the scenario's own initial distribution for the first hidden state, update
with the first observation, then predict and update for each later observation.
Transition rows represent previous states and columns next states. Emission rows
represent hidden states and columns observations. Normalize after every update.
The matrices are supplied inputs; they are not learned from observation frequencies.

Treat each final historical posterior as the estimate at simulation time zero.
For a road with no history, use that scenario's `initial` distribution. The
selected model keeps these beliefs fixed throughout the simulation.

```text
traffic multiplier = P(Low) * 1.0 + P(Medium) * 1.25 + P(High) * 1.5
estimated travel time = road-status travel time * traffic multiplier
```

For probabilities 0.6, 0.3, 0.1, the expected traffic multiplier is 1.125.
Congested plus certain High traffic gives 2.25 times normal time. Blocked roads
remain unusable regardless of traffic. Units are metres, metres/second, and seconds.
Fractional times retain their full precision; display rounding uses three decimals.

### Search and constraint-based allocation

Uniform-cost search expands the smallest accumulated travel-time entry and stops
when the goal is removed at minimum cost. Parent links reconstruct the route.
An unreachable destination returns an empty path and infinite time; staying at
the same location takes zero time. Equal-cost routes retain a deterministic first choice.

CSP variables are known, pending incidents. Domains are feasible available
responders plus an unassigned option. Constraints enforce listed capabilities,
availability, reachable routes, arrival deadlines, and one incident per responder
in a dispatch batch. The search uses plain backtracking without forward checking.

Complete combinations are compared left-to-right using:

```text
(Critical count, High count, Medium count, Low count, -total response time)
```

Response time is arrival minus incident timestamp, including waiting before
assignment. Equal scores retain input-order choices. This optimizes the current
batch; it does not optimize a whole sequence of future jobs.

### Simulation rules

The clock jumps to incident timestamps and responder releases. All simultaneous
arrivals and releases are processed before a joint allocation. Waiting incidents
are reconsidered at each event. Future incidents are not passed to the allocator
before their timestamps.

A responder stays busy for travel plus the incident's handling duration. Jobs are
not interrupted. After completion, the responder stays at the incident location.
Initially Busy units become available at their supplied locations after the
provided remaining time. No return-to-base or patient-transport trip is modeled.

Zero-duration jobs can complete and release a responder at the same time, allowing
another immediate assignment. The simulation stops when no future events remain,
including all dispatched-job completions. Remaining incidents are unhandled.
Arrival deadlines are hard constraints; handling may finish after the deadline.

## Output files and statistics

`plan.json` is a JSON list with exactly these fields per assignment:

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

The example shows one entry; the generated files contain the full scenario plans.
`time` is assignment start time, not arrival or completion.

`statistics.txt` reports:

- Incidents handled: assigned incidents, all completed before the simulation stops.
- Incidents unhandled: total incidents minus handled incidents, with their IDs.
- Responders used: distinct responders assigned to the supplied incidents.
- Average response time: appearance-to-arrival time over handled incidents only.
- Deadlines met: on-time handled incidents divided by **all** incidents; unhandled
  incidents count as deadline misses.

Times are seconds. With no handled incidents, the average is N/A. With no incidents,
the deadline percentage is N/A. Statistics use timings recomputed by plan replay.

## Validation and tests

Plans are validated before output files are written. Validation checks the four-field
schema, finite non-negative start times, identifiers, incident visibility, capability,
initial availability, duplicate incidents, path endpoints and directed edges,
arrival deadlines, and responder overlap through travel and handling. It also
replays positions after service and recomputes arrival and completion times.

Run the complete suite from the project root:

```bash
python3 -m unittest discover -s tests -v
```

All **61 tests passed**. Evidence includes:

- Hand-calculated Bayesian and HMM posteriors, plus exhaustive hidden-history enumeration.
- UCS costs compared with an independent Floyd-Warshall reference for all 845
  source/destination pairs in the three scenarios.
- A scarce-capability case requiring backtracking, priority ordering, and future-incident exclusion.
- Simultaneous events, initial busy units, no preemption, reuse after handling,
  unchanged input state, and zero-duration job chains.
- Deliberately invalid plans rejected for overlap, lateness, visibility, capability,
  malformed fields, invalid locations, and missing or blocked roads.
- All three documented commands executed in a clean project copy, with output
  files read back and validated; execution from another working directory also checked.

All 22 supplied scenario files, including their README, were verified unchanged
after relocation.

## Results for the supplied scenarios

| Scenario | Handled | Unhandled | Responders used | Average response (s) | Deadlines met |
| --- | --- | --- | --- | --- | --- |
| 1 | 6 / 7 | 1 | 4 | 90.256 | 85.714% |
| 2 | 3 / 12 | 9 | 2 | 15.419 | 25.000% |
| 3 | 12 / 20 | 8 | 7 | 654.405 | 60.000% |

All three plans passed replay validation. Read the averages together with coverage:
Scenario 2's low average describes only 3 of its 12 incidents. Its blocked bridge
roads disconnect parts of the city under the MAP estimates, and the chosen traffic
factors make several tight deadlines infeasible. For example, H1 to N1 takes
61.806 seconds under this model, exceeding I1's deadline of 55 from time zero.

## Limitations and development record

Validity is conditional on the selected estimates. No true road-state timeline was
provided, so validation cannot establish real-world road accessibility or estimation
accuracy. MAP status selection discards remaining uncertainty, correlated reports
can overstate confidence, and fixed traffic ignores later changes. The traffic
multipliers are chosen assumptions; multiplying traffic and road delays can count
the same congestion twice.

The CSP optimizes immediate batches, not global simulation outcomes, and does not
strategically wait for a busy responder or reserve units for unrevealed incidents.
Plain exhaustive backtracking can become expensive on larger instances. Validation
checks feasibility rather than global optimality; plan replay alone cannot prove
that an arbitrary planner avoided hidden lookahead. Dedicated visibility tests and
the simulator's data flow provide separate evidence for this implementation.

The development record in `docs/development_notes.md` retains the exact initial
coding prompt, subsequent choices, testing evidence, and limitations for the report
and oral defence. The submitted report and repository administration are separate
assignment deliverables.
