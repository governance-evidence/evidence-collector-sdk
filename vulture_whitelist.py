"""Vulture whitelist -- false positives for dead code detection.

Protocol method parameters and __all__ exports appear unused to vulture
but are part of the public API contract. This file must define matching
names so vulture treats them as used.
"""

# Protocol parameters (structural subtyping -- used by implementors)
# output/stream_writer.py StreamWriter.write_batch / .close
# integrations/flink/ FlinkSourceReader / FlinkEvidenceOperator / FlinkEvidenceSink
batch_size: int
element: dict  # type: ignore[type-arg]

# Config factory functions (called by users, not internally)
fraud_detection_config: object
credit_scoring_config: object
capabilities_from_config: object
