"""Transform configuration change signals into evidence units."""

from __future__ import annotations

from typing import TYPE_CHECKING

from collector.transforms.base import build_evidence_unit

if TYPE_CHECKING:
    from collector.config import CollectionConfig
    from collector.core.evidence_unit import EvidenceUnit
    from collector.core.signal import RawSignal


def transform_config(signal: RawSignal, *, config: CollectionConfig) -> EvidenceUnit:
    """Transform a configuration change signal into an evidence unit.

    Configuration changes (threshold updates, model swaps, policy changes)
    are high-quality evidence with full provenance but may lack
    the score key since they describe state changes, not predictions.

    Parameters
    ----------
    signal : RawSignal
        Config change signal.
    config : CollectionConfig
        Collection configuration.

    Returns
    -------
    EvidenceUnit
        Evidence unit derived from the config change.
    """
    qd = config.quality_for(signal.signal_type)
    gaps: tuple[str, ...] = ()
    if config.score_key not in signal.payload:
        gaps = ("no_prediction_score",)
    return build_evidence_unit(
        signal,
        config=config,
        transform_name="config_to_evidence",
        signal_quality=qd.base_quality,
        known_gaps=gaps,
    )
