"""Generate a JSON handoff from schedule context and an incident snapshot.

Run python -m handoff.report schedules.json incidents.json --at <offset timestamp>.
All input and output is local. The report describes the supplied snapshot.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

from handoff.context import parse_schedules, parse_snapshot, timestamp
from quality.report import unique_keys


def build_report(schedule_data: object, snapshot_data: object, at: str) -> dict[str, object]:
    instant = timestamp(at)
    schedules = parse_schedules(schedule_data)
    snapshot = parse_snapshot(snapshot_data)
    if snapshot.captured_at > instant:
        raise ValueError("Incident snapshot was captured after the requested handoff time.")
    rotations = {}
    warnings = []
    for name in sorted(schedules):
        shifts = schedules[name]
        current = next((s for s in shifts if s.starts_at <= instant < s.ends_at), None)
        outgoing = next((s for s in shifts if s.ends_at == instant), None)
        following = next((s for s in shifts if s.starts_at > instant), None)
        if current is None:
            warnings.append(f"Rotation {name} has no coverage at the requested time.")
        rotations[name] = {
            "current_responder": None if current is None else current.responder,
            "outgoing_responder": None if outgoing is None else outgoing.responder,
            "current_shift_ends_at": None if current is None else current.ends_at.isoformat(),
            "next_shift_starts_at": None if following is None else following.starts_at.isoformat(),
        }
    severity_order = {"critical": 0, "warning": 1, "info": 2}
    unresolved = sorted(
        (incident for incident in snapshot.incidents if incident.status != "resolved"),
        key=lambda incident: (severity_order.get(incident.severity, 3), incident.id),
    )
    for incident in unresolved:
        if incident.owner is None:
            warnings.append(f"Incident {incident.id} has no owner.")
        if incident.next_action is None:
            warnings.append(f"Incident {incident.id} has no next action.")
    return {
        "handoff_at": instant.isoformat(),
        "snapshot_captured_at": snapshot.captured_at.isoformat(),
        "snapshot_age_seconds": (instant - snapshot.captured_at).total_seconds(),
        "rotations": rotations,
        "unresolved_incidents": [asdict(incident) for incident in unresolved],
        "resolved_count": len(snapshot.incidents) - len(unresolved),
        "warnings": warnings,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("schedules", type=Path)
    parser.add_argument("incidents", type=Path)
    parser.add_argument("--at", required=True, help="Handoff timestamp including UTC offset")
    args = parser.parse_args()
    try:
        schedules = json.loads(args.schedules.read_text(), object_pairs_hook=unique_keys)
        incidents = json.loads(args.incidents.read_text(), object_pairs_hook=unique_keys)
        report = build_report(schedules, incidents, args.at)
    except (OSError, ValueError, RecursionError) as exc:
        print(f"Cannot render handoff: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(report, indent=2, sort_keys=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
