"""Fraud detection evidence collection example.

Demonstrates end-to-end evidence pipeline using the EvidenceCollector
orchestrator: create signals, collect, flush to Decision Event Schema, validate, write.
"""

from datetime import UTC, datetime
from pathlib import Path

from collector import (
    EvidenceCollector,
    JsonlStreamWriter,
    RawSignal,
    SignalType,
    fraud_detection_config,
    validate_complete,
)

collector = EvidenceCollector(config=fraud_detection_config())

# Simulate signals from a fraud scoring pipeline
signals = [
    RawSignal(
        signal_id="txn-001",
        signal_type=SignalType.EVENT,
        payload={"score": 0.92, "amount": 4500.0, "merchant_category": "jewelry"},
        source="fraud-scoring-model-v3",
        timestamp=datetime(2026, 1, 15, 14, 30, 0, tzinfo=UTC),
    ),
    RawSignal(
        signal_id="txn-002",
        signal_type=SignalType.EVENT,
        payload={"score": 0.15, "amount": 42.50, "merchant_category": "grocery"},
        source="fraud-scoring-model-v3",
        timestamp=datetime(2026, 1, 15, 14, 30, 1, tzinfo=UTC),
    ),
    RawSignal(
        signal_id="review-001",
        signal_type=SignalType.HUMAN_ACTION,
        payload={"score": 0.92, "rationale": "Confirmed fraudulent pattern", "override": True},
        source="analyst-jane-doe",
        timestamp=datetime(2026, 1, 15, 15, 0, 0, tzinfo=UTC),
    ),
]

# Collect all signals and flush to Decision Event Schema
collector.add_many(signals)
events = collector.flush()

# Validate output
for event in events:
    errors = validate_complete(event, config=collector.config)
    if errors:
        print(f"  VALIDATION ERRORS: {errors}")

# Write to file
output = Path("fraud_evidence.jsonl")
writer = JsonlStreamWriter(output)
writer.write_batch(events)
writer.close()

# Show capabilities for Governance Drift Toolkit negotiation
caps = collector.capabilities
print(f"SDK capabilities: schema={caps.schema_version}, types={len(caps.supported_signal_types)}")

print(f"\nWrote {len(events)} evidence events to {output}")
for e in events:
    print(f"  {e['decision_id']}: score={e.get('score', 'N/A')}, type={e['decision_type']}")
