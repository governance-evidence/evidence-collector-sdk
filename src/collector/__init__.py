"""Evidence Collector SDK (Evidence Collector SDK).

Public API re-exports for convenient access.
"""

from collector.capabilities import StreamCapabilities, capabilities_from_config
from collector.collector import EvidenceCollector, ValidationMode
from collector.config import (
    CollectionConfig,
    DecisionEventMappingConfig,
    SignalQualityDefaults,
    credit_scoring_config,
    fraud_detection_config,
)
from collector.core.attribution import Attribution
from collector.core.confidence import ConfidenceScore, compute_confidence
from collector.core.evidence_unit import EvidenceUnit, TemporalGrounding
from collector.core.provenance import ProvenanceChain, ProvenanceStep, content_hash
from collector.core.signal import RawSignal, SignalType
from collector.output.decision_event_writer import SCHEMA_VERSION, to_decision_event
from collector.output.stream_writer import JsonlStreamWriter, StreamWriter
from collector.pipeline import TransformPipeline
from collector.stream import (
    BufferOverflowError,
    EvidenceCollectorStream,
    OverflowStrategy,
    StreamStats,
)
from collector.validation import (
    validate_complete,
    validate_decision_event,
    validate_features,
    validate_provenance,
)

__all__ = [
    "SCHEMA_VERSION",
    "Attribution",
    "BufferOverflowError",
    "CollectionConfig",
    "ConfidenceScore",
    "DecisionEventMappingConfig",
    "EvidenceCollector",
    "EvidenceCollectorStream",
    "EvidenceUnit",
    "JsonlStreamWriter",
    "OverflowStrategy",
    "ProvenanceChain",
    "ProvenanceStep",
    "RawSignal",
    "SignalQualityDefaults",
    "SignalType",
    "StreamCapabilities",
    "StreamStats",
    "StreamWriter",
    "TemporalGrounding",
    "TransformPipeline",
    "ValidationMode",
    "capabilities_from_config",
    "compute_confidence",
    "content_hash",
    "credit_scoring_config",
    "fraud_detection_config",
    "to_decision_event",
    "validate_complete",
    "validate_decision_event",
    "validate_features",
    "validate_provenance",
]
