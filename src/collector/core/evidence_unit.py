"""Evidence unit data model.

An evidence unit is the structured output of the Evidence Collector SDK pipeline:
a raw signal enriched with contextualization, attribution, provenance,
confidence, and temporal grounding. It conforms to the Decision Event Schema when serialized.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from types import MappingProxyType
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Mapping
    from datetime import datetime

    from collector.core.attribution import Attribution
    from collector.core.confidence import ConfidenceScore
    from collector.core.provenance import ProvenanceChain
    from collector.core.signal import RawSignal


@dataclass(frozen=True)
class TemporalGrounding:
    """Temporal metadata for an evidence unit.

    Attributes
    ----------
    collection_timestamp : datetime
        When the evidence was collected by Evidence Collector SDK.
    event_timestamp : datetime
        When the original event occurred.
    processing_lag_ms : float
        Milliseconds between event and collection.
    """

    collection_timestamp: datetime
    event_timestamp: datetime
    processing_lag_ms: float

    def __post_init__(self) -> None:
        if not math.isfinite(self.processing_lag_ms) or self.processing_lag_ms < 0:
            msg = f"processing_lag_ms must be non-negative, got {self.processing_lag_ms}"
            raise ValueError(msg)


@dataclass(frozen=True)
class EvidenceUnit:
    """Complete evidence unit ready for Decision Event Schema serialization.

    Attributes
    ----------
    unit_id : str
        Unique identifier for this evidence unit.
    signal : RawSignal
        The raw signal that was transformed.
    provenance : ProvenanceChain
        Full transformation history.
    attribution : Attribution
        Actor attribution metadata.
    confidence : ConfidenceScore
        Evidence confidence assessment.
    context_enrichment : Mapping[str, object]
        System state, organizational context, dependency relations.
    temporal_grounding : TemporalGrounding
        Temporal metadata.
    """

    unit_id: str
    signal: RawSignal
    provenance: ProvenanceChain
    attribution: Attribution
    confidence: ConfidenceScore
    context_enrichment: Mapping[str, object]
    temporal_grounding: TemporalGrounding

    def __post_init__(self) -> None:
        if not self.unit_id:
            msg = "unit_id must be non-empty"
            raise ValueError(msg)
        object.__setattr__(
            self, "context_enrichment", MappingProxyType(dict(self.context_enrichment))
        )
