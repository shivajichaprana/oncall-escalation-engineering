"""Behavioural coverage for occurrence-based alert review metrics."""

import json
import subprocess
import sys
from pathlib import Path

import pytest

from quality.actionability import score_actionability
from quality.precision import score_precision
from quality.report import build_report, parse_reviews


def row(identifier, rule="queue-lag", incident=True, action=True):
    return {
        "id": identifier,
        "rule": rule,
        "incident_confirmed": incident,
        "action_required": action,
    }


def test_precision_exposes_unknowns_instead_of_counting_them_as_false():
    result = score_precision([True, False, None, None])
    assert (result.total, result.reviewed, result.positive) == (4, 2, 1)
    assert result.rate == 0.5
    assert result.coverage == 0.5


@pytest.mark.parametrize("values", [[], [None, None]])
def test_unreviewed_metrics_have_no_rate(values):
    metric = score_precision(values)
    assert metric.rate is None
    assert metric.coverage == (0.0 if values else None)


def test_negative_reviews_produce_a_measured_zero():
    assert score_actionability([False, False]).rate == 0.0
    assert score_actionability([True, True]).rate == 1.0


def test_overall_uses_counts_and_keeps_the_two_judgements_independent():
    report = build_report(
        [
            row("a", "small-rule", incident=False, action=True),
            row("b", "large-rule", incident=True, action=False),
            row("c", "large-rule", incident=True, action=False),
            row("d", "large-rule", incident=True, action=None),
        ]
    )
    assert report["overall"]["precision"]["rate"] == 0.75
    assert report["overall"]["actionability"]["rate"] == pytest.approx(1 / 3)
    assert report["overall"]["actionability"]["coverage"] == 0.75
    assert list(report["rules"]) == ["large-rule", "small-rule"]
    assert report["rules"]["small-rule"]["precision"]["rate"] == 0.0


@pytest.mark.parametrize(
    "source",
    [
        {},
        [row("same"), row("same")],
        [row(" same "), row("same")],
        [row("")],
        [row("x", rule=" ")],
        [row("x", rule="bad\nrule")],
        [row("x", incident=1)],
        [row("x", action="false")],
        [{"id": "x"}],
        [{**row("x"), "extra": True}],
        [None],
    ],
)
def test_invalid_or_duplicate_reviews_are_rejected(source):
    with pytest.raises(ValueError):
        parse_reviews(source)


def test_input_is_preserved_and_row_order_does_not_affect_report():
    source = [row("a"), row("b", incident=None)]
    before = json.dumps(source)
    assert build_report(source) == build_report(list(reversed(source)))
    assert json.dumps(source) == before


@pytest.mark.parametrize(
    "input_text",
    [
        "{broken",
        '[{"id":"a","id":"b"}]',
        '[{"id":"a","rule":"x","incident_confirmed":NaN,"action_required":true}]',
    ],
)
def test_cli_fails_without_partial_json(tmp_path, input_text):
    source = tmp_path / "reviews.json"
    source.write_text(input_text)
    run = subprocess.run(
        [sys.executable, "-m", "quality.report", str(source)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert run.returncode == 2
    assert run.stdout == ""
    assert "Cannot score reviews" in run.stderr


def test_cli_outputs_json_and_reports_missing_files(tmp_path):
    source = tmp_path / "reviews.json"
    source.write_text(json.dumps([row("a")]))
    good = subprocess.run(
        [sys.executable, "-m", "quality.report", str(source)],
        capture_output=True,
        text=True,
        check=True,
    )
    assert json.loads(good.stdout) == build_report([row("a")])
    missing = subprocess.run(
        [sys.executable, "-m", "quality.report", str(Path(tmp_path) / "missing.json")],
        capture_output=True,
        text=True,
        check=False,
    )
    assert missing.returncode == 2 and not missing.stdout
