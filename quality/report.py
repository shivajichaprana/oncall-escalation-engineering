"""Report alert precision and actionability from a local JSON review export.

Usage: python -m quality.report reviews.json

Input is a JSON array. Each row has exactly id, rule, incident_confirmed and
action_required. Each judgement is true, false or null (not yet reviewed).
IDs identify distinct occurrences after grouping repeat firings upstream.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from quality.actionability import score_actionability
from quality.precision import Metric, score_precision


@dataclass(frozen=True)
class Review:
    id: str
    rule: str
    incident_confirmed: bool | None
    action_required: bool | None


def parse_reviews(source: object) -> list[Review]:
    if not isinstance(source, list):
        raise ValueError("Input must be a JSON array of occurrence reviews.")
    result = []
    seen = set()
    for index, row in enumerate(source, start=1):
        if not isinstance(row, dict) or row.keys() != {
            "id",
            "rule",
            "incident_confirmed",
            "action_required",
        }:
            raise ValueError(f"Row {index} has missing or unexpected fields.")
        for key in ("id", "rule"):
            value = row[key]
            if not isinstance(value, str) or not value.strip() or not value.isprintable():
                raise ValueError(f"Row {index} requires printable, nonempty identifiers.")
        for key in ("incident_confirmed", "action_required"):
            if row[key] is not None and type(row[key]) is not bool:
                raise ValueError(f"Row {index} judgements must be true, false or null.")
        identifier = row["id"].strip()
        if identifier in seen:
            raise ValueError(f"Row {index} repeats an occurrence ID.")
        seen.add(identifier)
        result.append(
            Review(
                id=identifier,
                rule=row["rule"].strip(),
                incident_confirmed=row["incident_confirmed"],
                action_required=row["action_required"],
            )
        )
    return result


def metric_payload(metric: Metric) -> dict[str, int | float | None]:
    return {
        "total": metric.total,
        "reviewed": metric.reviewed,
        "positive": metric.positive,
        "unknown": metric.total - metric.reviewed,
        "rate": metric.rate,
        "coverage": metric.coverage,
    }


def summarize(reviews: Sequence[Review]) -> dict[str, object]:
    return {
        "precision": metric_payload(score_precision([r.incident_confirmed for r in reviews])),
        "actionability": metric_payload(score_actionability([r.action_required for r in reviews])),
    }


def build_report(source: object) -> dict[str, object]:
    reviews = parse_reviews(source)
    grouped: dict[str, list[Review]] = defaultdict(list)
    for review in reviews:
        grouped[review.rule].append(review)
    return {
        "overall": summarize(reviews),
        "rules": {rule: summarize(grouped[rule]) for rule in sorted(grouped)},
    }


def unique_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON object field.")
        result[key] = value
    return result


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("reviews", type=Path)
    args = parser.parse_args(argv)
    try:
        source = cast(object, json.loads(args.reviews.read_text(), object_pairs_hook=unique_keys))
        report = build_report(source)
    except (OSError, ValueError, RecursionError) as exc:
        print(f"Cannot score reviews: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(report, indent=2, sort_keys=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
