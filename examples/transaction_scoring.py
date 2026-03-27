"""Transaction risk scoring evidence collection example.

Demonstrates the EvidenceCollectorStream for continuous evidence
production consumable by Governance Drift Toolkit's EvidenceStreamReader Protocol.
"""

from datetime import UTC, datetime
from pathlib import Path

from collector import (
    CollectionConfig,
    EvidenceCollectorStream,
    JsonlStreamWriter,
    OverflowStrategy,
    RawSignal,
    SignalType,
)

# Custom config that includes CONFIG_CHANGE signals
config = CollectionConfig(
    name="credit_scoring_full",
    enabled_signal_types=frozenset({SignalType.EVENT, SignalType.METRIC, SignalType.CONFIG_CHANGE}),
    default_actor_type="system",
    default_source="credit-pipeline",
    score_key="score",
    feature_keys=("income", "debt_ratio", "credit_history_months"),
)

# Create a stream with backpressure (max 1000 signals buffered)
stream = EvidenceCollectorStream(
    config,
    max_buffer_size=1000,
    overflow_strategy=OverflowStrategy.DROP_OLDEST,
)

# Push signals as they arrive
signals = [
    RawSignal(
        signal_id="credit-001",
        signal_type=SignalType.EVENT,
        payload={
            "score": 0.72,
            "income": 85000.0,
            "debt_ratio": 0.35,
            "credit_history_months": 120,
        },
        source="credit-model-v2",
        timestamp=datetime(2026, 2, 1, 10, 0, 0, tzinfo=UTC),
    ),
    RawSignal(
        signal_id="config-001",
        signal_type=SignalType.CONFIG_CHANGE,
        payload={"old_threshold": 0.65, "new_threshold": 0.70, "reason": "regulatory update"},
        source="credit-model-v2",
        timestamp=datetime(2026, 2, 1, 9, 0, 0, tzinfo=UTC),
    ),
    RawSignal(
        signal_id="metric-001",
        signal_type=SignalType.METRIC,
        payload={"score": 0.88, "metric_name": "approval_rate", "value": 0.62},
        source="credit-pipeline-monitor",
        timestamp=datetime(2026, 2, 1, 10, 5, 0, tzinfo=UTC),
    ),
]

stream.push_many(signals)
print(f"Stream stats before read: {stream.stats}")

# Governance Drift Toolkit would call read_batch() to consume events
events = stream.read_batch(batch_size=100)
print(f"Stream stats after read: {stream.stats}")
stream.close()

# Write output
output = Path("credit_evidence.jsonl")
writer = JsonlStreamWriter(output)
writer.write_batch(events)
writer.close()

print(f"Wrote {len(events)} evidence events to {output}")
for e in events:
    qi = e["decision_quality_indicators"]
    print(
        f"  {e['decision_id']}: confidence={qi['confidence_score']:.2f}, gaps={qi['uncertainty_flags']}"
    )
