"""Validate schedule exports and incident snapshots before rendering a handoff."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from itertools import pairwise
from typing import cast


def timestamp(value: object) -> datetime:
    if not isinstance(value, str) or "T" not in value:
        raise ValueError("Timestamps must include a date, time and UTC offset.")
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("Invalid timestamp.") from exc
    if result.tzinfo is None:
        raise ValueError("Timestamps must include a UTC offset.")
    return result.astimezone(timezone.utc)


def text(value: object) -> str:
    if not isinstance(value, str) or not value.strip() or not value.isprintable():
        raise ValueError("Identifiers and text must be nonempty printable strings.")
    return value.strip()


def record(value: object, fields: set[str]) -> dict[str, object]:
    if not isinstance(value, dict) or value.keys() != fields:
        raise ValueError("Object must contain exactly: " + ", ".join(sorted(fields)))
    return cast(dict[str, object], value)


@dataclass(frozen=True)
class Shift:
    responder: str
    starts_at: datetime
    ends_at: datetime


@dataclass(frozen=True)
class Incident:
    id: str
    summary: str
    severity: str
    status: str
    owner: str | None
    next_action: str | None


@dataclass(frozen=True)
class Snapshot:
    captured_at: datetime
    incidents: tuple[Incident, ...]


def parse_schedules(source: object) -> dict[str, list[Shift]]:
    raw = record(source, {"schedules"})["schedules"]
    if not isinstance(raw, dict):
        raise ValueError("Schedules must be keyed by rotation name.")
    schedules = {}
    for name, rows in raw.items():
        name = text(name)
        if name in schedules:
            raise ValueError("Rotation names must be unique after trimming whitespace.")
        if not isinstance(rows, list):
            raise ValueError("Each rotation must contain a list of shifts.")
        shifts = []
        for row in rows:
            data = record(row, {"responder", "starts_at", "ends_at"})
            shift = Shift(
                text(data["responder"]), timestamp(data["starts_at"]), timestamp(data["ends_at"])
            )
            if shift.starts_at >= shift.ends_at:
                raise ValueError("Shift end must be later than its start.")
            shifts.append(shift)
        shifts.sort(key=lambda shift: shift.starts_at)
        if any(a.ends_at > b.starts_at for a, b in pairwise(shifts)):
            raise ValueError("Shifts in a rotation must not overlap.")
        schedules[name] = shifts
    return schedules


def parse_snapshot(source: object) -> Snapshot:
    data = record(source, {"captured_at", "incidents"})
    captured_at = timestamp(data["captured_at"])
    if not isinstance(data["incidents"], list):
        raise ValueError("Incidents must be a list.")
    incidents = []
    ids = set()
    for row in data["incidents"]:
        item = record(row, {"id", "summary", "severity", "status", "owner", "next_action"})
        incident = Incident(
            id=text(item["id"]),
            summary=text(item["summary"]),
            severity=text(item["severity"]),
            status=text(item["status"]),
            owner=None if item["owner"] is None else text(item["owner"]),
            next_action=None if item["next_action"] is None else text(item["next_action"]),
        )
        if incident.id in ids:
            raise ValueError("Incident IDs must be unique.")
        if incident.status not in {"open", "acknowledged", "resolved"}:
            raise ValueError("Incident status must be open, acknowledged or resolved.")
        ids.add(incident.id)
        incidents.append(incident)
    return Snapshot(captured_at, tuple(incidents))
