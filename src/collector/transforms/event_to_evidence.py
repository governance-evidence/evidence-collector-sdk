"""Transform event signals into evidence units."""

from __future__ import annotations

from typing import TYPE_CHECKING

from collector.transforms.base import build_evidence_unit

if TYPE_CHECKING:
    from collector.config import CollectionConfig
    from collector.core.evidence_unit import EvidenceUnit
    from collector.core.signal import RawSignal


def transform_event(signal: RawSignal, *, config: CollectionConfig) -> EvidenceUnit:
    """Transform an event signal into an evidence unit.

    Event signals represent discrete system events (transaction scored,
    alert raised, model invoked) and typically contain full payload data.

    Parameters
    ----------
    signal : RawSignal
        Event signal.
    config : CollectionConfig
        Collection configuration.

    Returns
    -------
    EvidenceUnit
        Evidence unit derived from the event.
    """
    qd = config.quality_for(signal.signal_type)
    return build_evidence_unit(
        signal,
        config=config,
        transform_name="event_to_evidence",
        signal_quality=qd.base_quality,
    )
