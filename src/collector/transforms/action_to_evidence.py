"""Transform human action signals into evidence units."""

from __future__ import annotations

from typing import TYPE_CHECKING

from collector.transforms.base import build_evidence_unit

if TYPE_CHECKING:
    from collector.config import CollectionConfig
    from collector.core.evidence_unit import EvidenceUnit
    from collector.core.signal import RawSignal


def transform_action(signal: RawSignal, *, config: CollectionConfig) -> EvidenceUnit:
    """Transform a human action signal into an evidence unit.

    Human actions (reviews, overrides, escalations) have actor_type="human"
    and may carry override rationale in the payload.

    Parameters
    ----------
    signal : RawSignal
        Human action signal.
    config : CollectionConfig
        Collection configuration.

    Returns
    -------
    EvidenceUnit
        Evidence unit derived from the human action.
    """
    qd = config.quality_for(signal.signal_type)
    gaps: tuple[str, ...] = ()
    quality = qd.base_quality
    if "rationale" not in signal.payload:
        gaps = ("missing_override_rationale",)
        quality = qd.missing_key_quality
    return build_evidence_unit(
        signal,
        config=config,
        transform_name="action_to_evidence",
        signal_quality=quality,
        known_gaps=gaps,
        actor_type="human",
    )
