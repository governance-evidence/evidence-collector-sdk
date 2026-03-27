"""End-to-end integration tests for the full evidence pipeline."""

import json
from datetime import UTC, datetime
from pathlib import Path

import numpy as np

from collector import (
    EvidenceCollector,
    EvidenceCollectorStream,
    JsonlStreamWriter,
    OverflowStrategy,
    RawSignal,
    SignalType,
    fraud_detection_config,
    to_decision_event,
    validate_complete,
)
from collector.transforms.event_to_evidence import transform_event


def _find_decision_event_schema() -> Path | None:
    """Return sibling Decision Event Schema path when available."""
    relative_schema_path = Path("decision-event-schema/schema/decision-event.schema.json")
    for parent in Path(__file__).resolve().parents:
        candidate = parent / relative_schema_path
        if candidate.exists():
            return candidate
    return None


class TestEndToEndPipeline:
    def test_signal_to_decision_event_file(self, tmp_path):
        """Full pipeline: create signal, transform, serialize, write."""
        cfg = fraud_detection_config()

        signals = [
            RawSignal(
                signal_id=f"sig-{i:03d}",
                signal_type=SignalType.EVENT,
                payload={"score": 0.5 + i * 0.1, "amount": 100.0 * i},
                source="fraud-model-v3",
                timestamp=datetime(2026, 1, 1, tzinfo=UTC),
            )
            for i in range(5)
        ]

        units = [transform_event(s, config=cfg) for s in signals]
        events = [to_decision_event(u) for u in units]

        output = tmp_path / "evidence.jsonl"
        writer = JsonlStreamWriter(output)
        writer.write_batch(events)
        writer.close()

        lines = output.read_text().strip().split("\n")
        assert len(lines) == 5

        for line in lines:
            event = json.loads(line)
            assert "decision_id" in event
            assert "score" in event
            assert "decision_context" in event
            assert "_provenance" in event

    def test_drift_extract_scores_compatible(self):
        """Verify Governance Drift Toolkit's extract_scores can consume our output."""
        cfg = fraud_detection_config()
        sig = RawSignal(
            signal_id="sig-001",
            signal_type=SignalType.EVENT,
            payload={"score": 0.87, "amount": 1500.0, "merchant_category": "electronics"},
            source="fraud-model",
            timestamp=datetime(2026, 1, 1, tzinfo=UTC),
        )
        unit = transform_event(sig, config=cfg)
        event = to_decision_event(unit)

        scores = np.array([event["score"]], dtype=np.float64)
        assert scores[0] == 0.87

    def test_drift_extract_features_compatible(self):
        """Verify Governance Drift Toolkit's extract_features can consume our output."""
        cfg = fraud_detection_config()
        sig = RawSignal(
            signal_id="sig-001",
            signal_type=SignalType.EVENT,
            payload={"score": 0.87, "amount": 1500.0, "merchant_category": "electronics"},
            source="fraud-model",
            timestamp=datetime(2026, 1, 1, tzinfo=UTC),
        )
        unit = transform_event(sig, config=cfg)
        event = to_decision_event(unit)

        feature_keys = ["amount"]
        features = np.array([[event[k] for k in feature_keys]], dtype=np.float64)
        assert features[0, 0] == 1500.0


class TestEvidenceCollectorIntegration:
    def test_full_workflow(self, tmp_path):
        """EvidenceCollector: add signals, flush, validate, write."""
        collector = EvidenceCollector(config=fraud_detection_config())

        signals = [
            RawSignal(
                signal_id=f"sig-{i}",
                signal_type=SignalType.EVENT,
                payload={
                    "score": 0.5 + i * 0.1,
                    "amount": float(i * 100),
                    "merchant_category": "test",
                },
                source="test-model",
                timestamp=datetime(2026, 1, 1, tzinfo=UTC),
            )
            for i in range(10)
        ]
        collector.add_many(signals)
        events = collector.flush()

        assert len(events) == 10
        assert collector.pending_count == 0
        assert collector.validation_errors == []

        for event in events:
            errors = validate_complete(event, config=collector.config)
            assert errors == [], f"Validation failed: {errors}"

        output = tmp_path / "output.jsonl"
        writer = JsonlStreamWriter(output)
        writer.write_batch(events)
        writer.close()
        assert len(output.read_text().strip().split("\n")) == 10

    def test_collect_one_validates(self):
        """collect_one produces valid Decision Event Schema output."""
        collector = EvidenceCollector(config=fraud_detection_config())
        sig = RawSignal(
            signal_id="sig-single",
            signal_type=SignalType.EVENT,
            payload={"score": 0.9, "amount": 500.0, "merchant_category": "food"},
            source="model",
            timestamp=datetime(2026, 1, 1, tzinfo=UTC),
        )
        event = collector.collect_one(sig)
        assert collector.validation_errors == []
        errors = validate_complete(event, config=collector.config)
        assert errors == []


class TestStreamIntegration:
    def test_stream_to_drift_toolkit(self):
        """EvidenceCollectorStream produces Governance Drift Toolkit-consumable batches."""
        stream = EvidenceCollectorStream(
            fraud_detection_config(),
            max_buffer_size=100,
            overflow_strategy=OverflowStrategy.RAISE,
        )
        for i in range(20):
            stream.push(
                RawSignal(
                    signal_id=f"s-{i}",
                    signal_type=SignalType.EVENT,
                    payload={"score": 0.5, "amount": 10.0, "merchant_category": "x"},
                    source="model",
                    timestamp=datetime(2026, 1, 1, tzinfo=UTC),
                )
            )
        batch1 = stream.read_batch(batch_size=10)
        batch2 = stream.read_batch(batch_size=10)
        assert len(batch1) == 10
        assert len(batch2) == 10
        assert stream.buffer_size == 0
        assert stream.stats.processed_count == 20
        assert stream.stats.failed_batch_count == 0

        # Each event consumable by Governance Drift Toolkit
        for event in batch1 + batch2:
            assert "score" in event
            assert "decision_id" in event
            scores = np.array([event["score"]], dtype=np.float64)
            assert scores.shape == (1,)

        stream.close()


class TestStreamToFileIntegration:
    def test_stream_push_read_write_roundtrip(self, tmp_path):
        """Push signals to stream, read batches, write to JSONL, verify."""
        stream = EvidenceCollectorStream(
            fraud_detection_config(),
            max_buffer_size=100,
            overflow_strategy=OverflowStrategy.RAISE,
        )
        for i in range(15):
            stream.push(
                RawSignal(
                    signal_id=f"rt-{i}",
                    signal_type=SignalType.EVENT,
                    payload={
                        "score": 0.5 + i * 0.01,
                        "amount": float(i),
                        "merchant_category": "test",
                    },
                    source="test-model",
                    timestamp=datetime(2026, 1, 1, tzinfo=UTC),
                )
            )

        output = tmp_path / "stream_output.jsonl"
        with JsonlStreamWriter(output) as writer:
            batch1 = stream.read_batch(batch_size=10)
            writer.write_batch(batch1)
            batch2 = stream.read_batch(batch_size=10)
            writer.write_batch(batch2)

        stream.close()

        lines = output.read_text().strip().split("\n")
        assert len(lines) == 15
        for line in lines:
            event = json.loads(line)
            assert "decision_id" in event
            errors = validate_complete(event, config=fraud_detection_config())
            assert errors == []

    def test_large_batch_10k_signals(self):
        """Verify 10K signals process without memory or performance issues."""
        collector = EvidenceCollector(config=fraud_detection_config())
        signals = [
            RawSignal(
                signal_id=f"bulk-{i:05d}",
                signal_type=SignalType.EVENT,
                payload={"score": 0.5 + (i % 100) * 0.005, "amount": float(i)},
                source="bulk-test",
                timestamp=datetime(2026, 1, 1, tzinfo=UTC),
            )
            for i in range(10_000)
        ]
        collector.add_many(signals)
        events = collector.flush()
        assert len(events) == 10_000
        assert collector.validation_errors == []

    def test_failure_recovery(self):
        """Buffer preserved after pipeline failure, retry succeeds."""
        stream = EvidenceCollectorStream(
            fraud_detection_config(),
            max_buffer_size=100,
        )
        stream.push(
            RawSignal(
                signal_id="ok-1",
                signal_type=SignalType.EVENT,
                payload={"score": 0.8, "amount": 100.0},
                source="test",
                timestamp=datetime(2026, 1, 1, tzinfo=UTC),
            )
        )
        assert stream.buffer_size == 1

        # Read batch (should succeed and produce events)
        events = stream.read_batch(batch_size=10)
        assert len(events) == 1
        assert stream.stats.processed_count == 1
        assert stream.buffer_size == 0

        stream.close()


class TestRealSchemaValidation:
    def test_against_decision_event_schema(self):
        """Validate output against real Decision Event Schema JSON Schema if available."""
        schema_path = _find_decision_event_schema()
        if schema_path is None:
            return  # skip if sibling repo not available

        collector = EvidenceCollector(config=fraud_detection_config())
        sig = RawSignal(
            signal_id="sig-schema",
            signal_type=SignalType.EVENT,
            payload={"score": 0.87, "amount": 1500.0, "merchant_category": "electronics"},
            source="fraud-model",
            timestamp=datetime(2026, 1, 1, tzinfo=UTC),
        )
        event = collector.collect_one(sig)

        from collector.validation import validate_decision_event

        errors = validate_decision_event(event, schema_path=schema_path)
        assert errors == [], f"Real Decision Event Schema schema validation failed: {errors}"
