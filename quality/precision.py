"""Precision from reviewed occurrences, with unreviewed coverage exposed."""

from collections.abc import Sequence
from dataclasses import dataclass


@dataclass(frozen=True)
class Metric:
    total: int
    reviewed: int
    positive: int

    @property
    def rate(self) -> float | None:
        return self.positive / self.reviewed if self.reviewed else None

    @property
    def coverage(self) -> float | None:
        return self.reviewed / self.total if self.total else None


def reviewed_rate(values: Sequence[bool | None]) -> Metric:
    """Count explicit judgements. Unknown outcomes stay outside the denominator."""
    if any(value is not None and type(value) is not bool for value in values):
        raise ValueError("Judgements must be true, false, or null.")
    return Metric(
        total=len(values),
        reviewed=sum(value is not None for value in values),
        positive=sum(value is True for value in values),
    )


def score_precision(incident_confirmed: Sequence[bool | None]) -> Metric:
    """Share of reviewed occurrences confirmed to correspond to an incident."""
    return reviewed_rate(incident_confirmed)
