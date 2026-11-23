"""Boundary, coverage and input validation tests for handoff reporting."""

import copy
import json
import subprocess
import sys

import pytest

from handoff.report import build_report


def schedules():
    return {
        "schedules": {
            "primary": [
                {
                    "responder": "engineer-a",
                    "starts_at": "2026-01-05T09:00:00Z",
                    "ends_at": "2026-01-06T09:00:00Z",
                },
                {
                    "responder": "engineer-b",
                    "starts_at": "2026-01-06T09:00:00Z",
                    "ends_at": "2026-01-07T09:00:00Z",
                },
            ]
        }
    }


def snapshot():
    return {
        "captured_at": "2026-01-06T08:55:00Z",
        "incidents": [
            {
                "id": "a",
                "summary": "Queue lag",
                "severity": "warning",
                "status": "open",
                "owner": None,
                "next_action": None,
            },
            {
                "id": "b",
                "summary": "Recovered",
                "severity": "critical",
                "status": "resolved",
                "owner": "engineer-a",
                "next_action": None,
            },
        ],
    }


AT = "2026-01-06T09:00:00Z"


def test_boundary_belongs_to_incoming_and_carries_unresolved_work():
    report = build_report(schedules(), snapshot(), AT)
    rotation = report["rotations"]["primary"]
    assert rotation["current_responder"] == "engineer-b"
    assert rotation["outgoing_responder"] == "engineer-a"
    assert report["snapshot_age_seconds"] == 300
    assert [i["id"] for i in report["unresolved_incidents"]] == ["a"]
    assert report["resolved_count"] == 1
    assert report["warnings"] == ["Incident a has no owner.", "Incident a has no next action."]


def test_offsets_represent_the_same_instant():
    assert build_report(schedules(), snapshot(), AT) == build_report(
        schedules(), snapshot(), "2026-01-06T14:30:00+05:30"
    )


def test_end_of_coverage_is_explicit():
    report = build_report(schedules(), snapshot(), "2026-01-07T09:00:00Z")
    assert report["rotations"]["primary"]["current_responder"] is None
    assert report["rotations"]["primary"]["outgoing_responder"] == "engineer-b"
    assert "no coverage" in report["warnings"][0]


def test_gap_does_not_assign_previous_responder():
    data = schedules()
    data["schedules"]["primary"][0]["ends_at"] = "2026-01-06T08:00:00Z"
    report = build_report(data, snapshot(), "2026-01-06T08:59:00Z")
    assert report["rotations"]["primary"]["current_responder"] is None
    assert report["rotations"]["primary"]["outgoing_responder"] is None


def test_overlapping_shifts_are_rejected():
    data = schedules()
    data["schedules"]["primary"][0]["ends_at"] = "2026-01-06T10:00:00Z"
    with pytest.raises(ValueError, match="overlap"):
        build_report(data, snapshot(), AT)


@pytest.mark.parametrize("at", ["2026-01-06T09:00:00", "not-a-date", "2026-01-06T08:54:00Z"])
def test_naive_invalid_or_future_snapshot_is_rejected(at):
    with pytest.raises(ValueError):
        build_report(schedules(), snapshot(), at)


def test_duplicate_incident_ids_are_rejected():
    data = snapshot()
    data["incidents"].append(copy.deepcopy(data["incidents"][0]))
    with pytest.raises(ValueError, match="unique"):
        build_report(schedules(), data, AT)


def test_unknown_status_is_rejected():
    data = snapshot()
    data["incidents"][0]["status"] = "unknown"
    with pytest.raises(ValueError, match="status"):
        build_report(schedules(), data, AT)


def test_unsorted_shifts_render_identically_and_inputs_are_preserved():
    data = schedules()
    original = copy.deepcopy(data)
    assert build_report(data, snapshot(), AT)
    assert data == original
    data["schedules"]["primary"].reverse()
    assert build_report(data, snapshot(), AT) == build_report(original, snapshot(), AT)


def test_cli_success_and_bad_snapshot(tmp_path):
    schedule_file = tmp_path / "schedule.json"
    incident_file = tmp_path / "incidents.json"
    schedule_file.write_text(json.dumps(schedules()))
    incident_file.write_text(json.dumps(snapshot()))
    command = [
        sys.executable,
        "-m",
        "handoff.report",
        str(schedule_file),
        str(incident_file),
        "--at",
        AT,
    ]
    good = subprocess.run(command, check=True, capture_output=True, text=True)
    assert json.loads(good.stdout) == build_report(schedules(), snapshot(), AT)
    incident_file.write_text('{"captured_at":"a","captured_at":"b","incidents":[]}')
    bad = subprocess.run(command, check=False, capture_output=True, text=True)
    assert bad.returncode == 2 and bad.stdout == ""
    assert "Cannot render handoff" in bad.stderr
