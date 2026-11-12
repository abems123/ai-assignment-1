"""Export the required plan format and the approved performance statistics."""

import json
from pathlib import Path

from .allocation import Assignment


def make_plan(assignments: list[Assignment]) -> list[dict]:
    """Keep exactly the four fields required in plan.json."""
    return [{"responder_id": item.responder_id, "incident_id": item.incident_id,
             "path": list(item.path), "time": item.time} for item in assignments]


def calculate_statistics(incidents: list[dict], assignments: list[Assignment]) -> dict:
    """Use validated completed assignments; unhandled incidents are deadline misses."""
    incidents_by_id = {item["incident_id"]: item for item in incidents}
    handled_ids = {item.incident_id for item in assignments}
    on_time = sum(item.arrival_time <= float(incidents_by_id[item.incident_id]["deadline"])
                  for item in assignments)
    average = None
    if assignments:
        average = sum(item.response_time for item in assignments) / len(assignments)
    percentage = None
    if incidents:
        percentage = 100.0 * on_time / len(incidents)
    unhandled = [item["incident_id"] for item in incidents if item["incident_id"] not in handled_ids]
    return {
        "incidents_total": len(incidents), "incidents_handled": len(assignments),
        "incidents_unhandled": len(unhandled),
        "responders_used": len({item.responder_id for item in assignments}),
        "average_response_time": average, "deadlines_met": on_time,
        "deadlines_met_percentage": percentage, "unhandled_incident_ids": unhandled,
    }


def format_statistics(statistics: dict) -> str:
    average = statistics["average_response_time"]
    average_text = "N/A (no incidents handled)" if average is None else f"{average:.3f} s"
    percentage = statistics["deadlines_met_percentage"]
    deadline_text = "N/A (no incidents)" if percentage is None else (
        f"{percentage:.3f}% ({statistics['deadlines_met']}/{statistics['incidents_total']})"
    )
    unhandled_text = ", ".join(statistics["unhandled_incident_ids"]) or "none"
    return (
        "System statistics:\n"
        f"Incidents handled: {statistics['incidents_handled']} of {statistics['incidents_total']}\n"
        f"Incidents unhandled: {statistics['incidents_unhandled']}\n"
        f"Responders used: {statistics['responders_used']}\n"
        f"Average response time: {average_text}\n"
        f"Deadlines met: {deadline_text}\n"
        f"Unhandled incident IDs: {unhandled_text}\n\n"
        "Time unit: seconds. Response time includes waiting before dispatch and travel.\n"
        "The average includes handled incidents only. Unhandled incidents count as deadline misses.\n"
        "Travel times use the selected fixed road and traffic estimates.\n"
    )


def write_outputs(directory: Path, plan: list[dict], statistics: dict) -> None:
    """Write the already-validated plan and its statistics to the scenario folder."""
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "plan.json").write_text(
        json.dumps(plan, indent=2, allow_nan=False) + "\n", encoding="utf-8"
    )
    (directory / "statistics.txt").write_text(format_statistics(statistics), encoding="utf-8")
