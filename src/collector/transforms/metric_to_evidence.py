"""Transform metric signals into evidence units."""

from __future__ import annotations

from typing import TYPE_CHECKING

from collector.transforms.base import build_evidence_unit

if TYPE_CHECKING:
    from collector.config import CollectionConfig
    from collector.core.evidence_unit import EvidenceUnit
    from collector.core.signal import RawSignal


def transform_metric(signal: RawSignal, *, config: CollectionConfig) -> EvidenceUnit:
    """Transform a metric signal into an evidence unit.

    Metric signals are typically high-quality structured data with
    full collection completeness.

    Parameters
    ----------
    signal : RawSignal
        Metric signal.
    config : CollectionConfig
        Collection configuration.

    Returns
    -------
    EvidenceUnit
        Evidence unit derived from the metric.
    """
    qd = config.quality_for(signal.signal_type)
    return build_evidence_unit(
        signal,
        config=config,
        transform_name="metric_to_evidence",
        signal_quality=qd.base_quality,
    )
