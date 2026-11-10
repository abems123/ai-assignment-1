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
the requested scenario selection and data loading. All AI and simulation choices
remain pending the student's decisions.

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

No AI, planning, or simulation choice has been approved yet.

Record the selected option, its justification, relevant follow-up interactions,
and observed limitations here as each component is added.
