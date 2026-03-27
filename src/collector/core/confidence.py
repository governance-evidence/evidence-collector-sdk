"""Evidence confidence scoring.

Confidence reflects how reliable an evidence unit is based on signal quality,
collection completeness, and known observation gaps.
"""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class ConfidenceScore:
    """Confidence assessment for an evidence unit.

    Attributes
    ----------
    value : float
        Overall confidence score in [0.0, 1.0].
    signal_quality : float
        Quality of the raw signal in [0.0, 1.0].
    collection_completeness : float
        Fraction of expected data successfully collected in [0.0, 1.0].
    known_gaps : tuple[str, ...]
        Explicit descriptions of known observation gaps.
    """

    value: float
    signal_quality: float
    collection_completeness: float
    known_gaps: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        for name, val in [
            ("value", self.value),
            ("signal_quality", self.signal_quality),
            ("collection_completeness", self.collection_completeness),
        ]:
            if not math.isfinite(val) or not 0.0 <= val <= 1.0:
                msg = f"{name} must be in [0, 1], got {val}"
                raise ValueError(msg)


def compute_confidence(
    *,
    signal_quality: float,
    collection_completeness: float,
    known_gaps: tuple[str, ...] = (),
    gap_penalty: float = 0.05,
) -> ConfidenceScore:
    """Compute confidence from components.

    Parameters
    ----------
    signal_quality : float
        Quality of the raw signal in [0.0, 1.0].
    collection_completeness : float
        Fraction collected in [0.0, 1.0].
    known_gaps : tuple of str
        Known gap descriptions.
    gap_penalty : float
        Penalty per known gap (default 0.05).

    Returns
    -------
    ConfidenceScore
        Computed confidence.
    """
    base = (signal_quality + collection_completeness) / 2.0
    penalty = len(known_gaps) * gap_penalty
    value = max(0.0, min(1.0, base - penalty))
    return ConfidenceScore(
        value=value,
        signal_quality=signal_quality,
        collection_completeness=collection_completeness,
        known_gaps=known_gaps,
    )
