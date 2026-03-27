import threading

import pytest

from collector.config import fraud_detection_config
from collector.stream import (
    BufferOverflowError,
    EvidenceCollectorStream,
    OverflowStrategy,
    StreamStats,
)
from tests.conftest import make_signal


class TestEvidenceCollectorStream:
    def test_push_and_read(self):
        stream = EvidenceCollectorStream(fraud_detection_config())
        stream.push(make_signal(signal_id="sig-001"))
        stream.push(make_signal(signal_id="sig-002"))
        events = stream.read_batch(batch_size=10)
        assert len(events) == 2
        assert events[0]["decision_id"].startswith("eu-")

    def test_read_batch_drains_buffer(self):
        stream = EvidenceCollectorStream(fraud_detection_config())
        for i in range(5):
            stream.push(make_signal(signal_id=f"sig-{i:03d}"))
        batch1 = stream.read_batch(batch_size=3)
        assert len(batch1) == 3
        batch2 = stream.read_batch(batch_size=10)
        assert len(batch2) == 2

    def test_read_empty(self):
        stream = EvidenceCollectorStream(fraud_detection_config())
        events = stream.read_batch()
        assert events == []

    def test_push_many(self):
        stream = EvidenceCollectorStream(fraud_detection_config())
        signals = [make_signal(signal_id=f"sig-{i}") for i in range(4)]
        stream.push_many(signals)
        events = stream.read_batch(batch_size=100)
        assert len(events) == 4

    def test_close(self):
        stream = EvidenceCollectorStream(fraud_detection_config())
        stream.push(make_signal())
        stream.close()
        assert stream.closed is True
        events = stream.read_batch()
        assert events == []

    def test_push_after_close_raises(self):
        stream = EvidenceCollectorStream(fraud_detection_config())
        stream.close()
        with pytest.raises(RuntimeError, match="closed"):
            stream.push(make_signal())

    def test_push_many_after_close_raises(self):
        stream = EvidenceCollectorStream(fraud_detection_config())
        stream.close()
        with pytest.raises(RuntimeError, match="closed"):
            stream.push_many([make_signal()])

    def test_satisfies_drift_protocol(self):
        stream = EvidenceCollectorStream(fraud_detection_config())
        assert hasattr(stream, "read_batch")
        assert hasattr(stream, "close")
        result = stream.read_batch(batch_size=100)
        assert isinstance(result, list)
        stream.close()

    def test_buffer_size_property(self):
        stream = EvidenceCollectorStream(fraud_detection_config())
        assert stream.buffer_size == 0
        assert stream.queued_count == 0
        assert stream.in_flight_count == 0
        stream.push(make_signal())
        assert stream.buffer_size == 1
        assert stream.queued_count == 1

    def test_stats_snapshot_reports_current_counts(self):
        stream = EvidenceCollectorStream(fraud_detection_config())

        stats = stream.stats

        assert stats == StreamStats(
            queued_count=0,
            in_flight_count=0,
            buffer_size=0,
            processed_count=0,
            failed_batch_count=0,
            dropped_count=0,
        )

        stream.push(make_signal(signal_id="s1"))

        stats = stream.stats
        assert stats.queued_count == 1
        assert stats.in_flight_count == 0
        assert stats.buffer_size == 1
        assert stats.processed_count == 0

    def test_stats_returns_immutable_snapshot(self):
        stream = EvidenceCollectorStream(fraud_detection_config())
        stream.push(make_signal(signal_id="s1"))

        stats_before = stream.stats
        stream.push(make_signal(signal_id="s2"))

        assert stats_before.queued_count == 1
        assert stream.stats.queued_count == 2

    def test_overflow_strategy_property_uses_enum(self):
        stream = EvidenceCollectorStream(
            fraud_detection_config(),
            overflow_strategy=OverflowStrategy.DROP_OLDEST,
        )
        assert stream.overflow_strategy is OverflowStrategy.DROP_OLDEST

    def test_string_overflow_strategy_is_normalized_to_enum(self):
        stream = EvidenceCollectorStream(
            fraud_detection_config(),
            overflow_strategy="drop_oldest",
        )
        assert stream.overflow_strategy is OverflowStrategy.DROP_OLDEST

    def test_backpressure_raise(self):
        stream = EvidenceCollectorStream(
            fraud_detection_config(),
            max_buffer_size=2,
            overflow_strategy=OverflowStrategy.RAISE,
        )
        stream.push(make_signal(signal_id="s1"))
        stream.push(make_signal(signal_id="s2"))
        with pytest.raises(BufferOverflowError, match="Buffer full"):
            stream.push(make_signal(signal_id="s3"))

    def test_backpressure_drop_oldest(self):
        stream = EvidenceCollectorStream(
            fraud_detection_config(),
            max_buffer_size=2,
            overflow_strategy=OverflowStrategy.DROP_OLDEST,
        )
        stream.push(make_signal(signal_id="s1"))
        stream.push(make_signal(signal_id="s2"))
        stream.push(make_signal(signal_id="s3"))
        assert stream.dropped_count == 1
        assert stream.buffer_size == 2

    def test_invalid_overflow_strategy(self):
        with pytest.raises(ValueError, match="overflow_strategy"):
            EvidenceCollectorStream(
                fraud_detection_config(),
                overflow_strategy="explode",
            )

    def test_thread_safety_concurrent_push(self):
        stream = EvidenceCollectorStream(fraud_detection_config())
        errors: list[Exception] = []

        def pusher(start_id):
            try:
                for i in range(50):
                    stream.push(make_signal(signal_id=f"t-{start_id}-{i}"))
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=pusher, args=(t,)) for t in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert errors == []
        assert stream.buffer_size == 200

    def test_read_batch_preserves_buffer_when_pipeline_fails(self):
        stream = EvidenceCollectorStream(fraud_detection_config())
        stream.push(make_signal(signal_id="sig-001"))

        class FailingPipeline:
            def process_to_decision_event(self, signals):
                raise RuntimeError("boom")

        stream._pipeline = FailingPipeline()

        with pytest.raises(RuntimeError, match="boom"):
            stream.read_batch()

        assert stream.buffer_size == 1

    def test_read_batch_does_not_restore_when_closed_during_failure(self):
        stream = EvidenceCollectorStream(fraud_detection_config())
        stream.push(make_signal(signal_id="sig-001"))

        class FailingPipeline:
            def process_to_decision_event(self, signals):
                stream.close()
                raise RuntimeError("boom")

        stream._pipeline = FailingPipeline()

        with pytest.raises(RuntimeError, match="boom"):
            stream.read_batch()

        assert stream.closed is True
        assert stream.buffer_size == 0

    def test_in_flight_batch_counts_toward_backpressure(self):
        stream = EvidenceCollectorStream(
            fraud_detection_config(),
            max_buffer_size=2,
            overflow_strategy=OverflowStrategy.RAISE,
        )
        stream.push(make_signal(signal_id="s1"))
        stream.push(make_signal(signal_id="s2"))

        class FailingPipeline:
            def process_to_decision_event(self, signals):
                with pytest.raises(BufferOverflowError, match="Buffer full"):
                    stream.push(make_signal(signal_id="s3"))
                raise RuntimeError("boom")

        stream._pipeline = FailingPipeline()

        with pytest.raises(RuntimeError, match="boom"):
            stream.read_batch(batch_size=1)

        assert stream.buffer_size == 2
        assert stream.in_flight_count == 0
        assert stream.failed_batch_count == 1
        assert [signal.signal_id for signal in stream._buffer] == ["s1", "s2"]

    def test_drop_oldest_only_drops_queued_items_when_batch_in_flight(self):
        stream = EvidenceCollectorStream(
            fraud_detection_config(),
            max_buffer_size=2,
            overflow_strategy=OverflowStrategy.DROP_OLDEST,
        )
        stream.push(make_signal(signal_id="s1"))
        stream.push(make_signal(signal_id="s2"))

        class SuccessfulPipeline:
            def process_to_decision_event(self, signals):
                stream.push(make_signal(signal_id="s3"))
                return [{"decision_id": "d1", "score": 0.9}]

        stream._pipeline = SuccessfulPipeline()

        events = stream.read_batch(batch_size=1)

        assert len(events) == 1
        assert stream.processed_count == 1
        assert stream.dropped_count == 1
        assert stream.buffer_size == 1
        assert [signal.signal_id for signal in stream._buffer] == ["s3"]

    def test_drop_oldest_drops_incoming_when_only_in_flight_occupies_capacity(self):
        stream = EvidenceCollectorStream(
            fraud_detection_config(),
            max_buffer_size=1,
            overflow_strategy=OverflowStrategy.DROP_OLDEST,
        )
        stream.push(make_signal(signal_id="s1"))

        class FailingPipeline:
            def process_to_decision_event(self, signals):
                stream.push(make_signal(signal_id="s2"))
                raise RuntimeError("boom")

        stream._pipeline = FailingPipeline()

        with pytest.raises(RuntimeError, match="boom"):
            stream.read_batch(batch_size=1)

        assert stream.dropped_count == 1
        assert stream.failed_batch_count == 1
        assert stream.buffer_size == 1
        assert [signal.signal_id for signal in stream._buffer] == ["s1"]

    def test_read_batch_exposes_in_flight_and_processed_counts(self):
        stream = EvidenceCollectorStream(fraud_detection_config())
        stream.push(make_signal(signal_id="s1"))
        stream.push(make_signal(signal_id="s2"))

        class ObservingPipeline:
            def process_to_decision_event(self, signals):
                assert stream.queued_count == 0
                assert stream.in_flight_count == 2
                return [{"decision_id": signal.signal_id} for signal in signals]

        stream._pipeline = ObservingPipeline()

        events = stream.read_batch(batch_size=2)

        assert len(events) == 2
        assert stream.queued_count == 0
        assert stream.in_flight_count == 0
        assert stream.processed_count == 2
        assert stream.failed_batch_count == 0
        assert stream.stats == StreamStats(
            queued_count=0,
            in_flight_count=0,
            buffer_size=0,
            processed_count=2,
            failed_batch_count=0,
            dropped_count=0,
        )
