"""Regression cases for independently reviewed alert quality metrics."""

import math

import pytest

from quality.actionability import score_actionability
from quality.precision import score_precision
from quality.report import build_report


@pytest.mark.parametrize("score", [score_precision, score_actionability])
@pytest.mark.parametrize("invalid", [0, 1.0, "false", math.nan])
def test_metric_api_rejects_coerced_judgements(score, invalid):
    with pytest.raises(ValueError):
        score([True, invalid])


@pytest.mark.parametrize("score", [score_precision, score_actionability])
def test_empty_review_is_unknown_instead_of_perfect_or_zero(score):
    result = score([])
    assert (result.total, result.reviewed, result.positive) == (0, 0, 0)
    assert result.rate is None
    assert result.coverage is None


def test_review_coverage_is_independent_for_each_metric():
    data = [
        {"id": "a", "rule": "queue", "incident_confirmed": True, "action_required": None},
        {"id": "b", "rule": "queue", "incident_confirmed": False, "action_required": None},
        {"id": "c", "rule": "queue", "incident_confirmed": None, "action_required": None},
    ]
    report = build_report(data)
    precision = report["overall"]["precision"]
    actionability = report["overall"]["actionability"]
    assert precision["reviewed"] == 2 and precision["rate"] == 0.5
    assert precision["coverage"] == pytest.approx(2 / 3)
    assert actionability["reviewed"] == 0 and actionability["rate"] is None
    assert actionability["coverage"] == 0
    assert actionability["unknown"] == 3


def test_rule_counts_conserve_the_global_denominators():
    data = [
        {"id": str(index), "rule": rule, "incident_confirmed": incident, "action_required": action}
        for index, (rule, incident, action) in enumerate(
            [("queue", True, None), ("queue", False, True), ("capacity", None, False)]
        )
    ]
    report = build_report(data)
    for metric in ("precision", "actionability"):
        overall = report["overall"][metric]
        for count in ("total", "reviewed", "positive", "unknown"):
            assert overall[count] == sum(rule[metric][count] for rule in report["rules"].values())
        assert overall["reviewed"] + overall["unknown"] == overall["total"]
