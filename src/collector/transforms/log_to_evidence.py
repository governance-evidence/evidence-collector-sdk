"""Transform log signals into evidence units."""

from __future__ import annotations

from typing import TYPE_CHECKING

from collector.transforms.base import build_evidence_unit

if TYPE_CHECKING:
    from collector.config import CollectionConfig
    from collector.core.evidence_unit import EvidenceUnit
    from collector.core.signal import RawSignal


def transform_log(signal: RawSignal, *, config: CollectionConfig) -> EvidenceUnit:
    """Transform a log signal into an evidence unit.

    Log signals may have incomplete structured data, so signal quality
    is reduced and a known gap is recorded when the score key is missing.

    Parameters
    ----------
    signal : RawSignal
        Log signal.
    config : CollectionConfig
        Collection configuration.

    Returns
    -------
    EvidenceUnit
        Evidence unit derived from the log.
    """
    qd = config.quality_for(signal.signal_type)
    gaps: tuple[str, ...] = ()
    quality = qd.base_quality
    if config.score_key not in signal.payload:
        gaps = ("missing_score_key",)
        quality = qd.missing_key_quality
    return build_evidence_unit(
        signal,
        config=config,
        transform_name="log_to_evidence",
        signal_quality=quality,
        known_gaps=gaps,
    )
