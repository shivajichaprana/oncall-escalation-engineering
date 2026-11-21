"""Actionability from observed responder decisions."""

from collections.abc import Sequence

from quality.precision import Metric, reviewed_rate


def score_actionability(action_required: Sequence[bool | None]) -> Metric:
    """Share of reviewed occurrences requiring a useful responder intervention.

    A confirmed incident may need no intervention, and preventive work may be
    useful before an incident occurs. Score this judgement independently.
    """
    return reviewed_rate(action_required)
