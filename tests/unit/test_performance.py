"""Performance benchmarks for hashing and batch transforms."""

import time
from datetime import UTC, datetime

from collector.config import fraud_detection_config
from collector.core.provenance import content_hash
from collector.core.signal import RawSignal, SignalType
from collector.pipeline import TransformPipeline


def _signal(i):
    return RawSignal(
        signal_id=f"sig-{i:06d}",
        signal_type=SignalType.EVENT,
        payload={"score": 0.5 + (i % 100) * 0.005, "amount": float(i * 10)},
        source="perf-test",
        timestamp=datetime(2026, 1, 1, tzinfo=UTC),
    )


class TestContentHashPerformance:
    def test_10k_hashes_under_500ms(self):
        data = {"score": 0.87, "amount": 1500.0, "merchant": "electronics"}
        start = time.perf_counter()
        for _ in range(10_000):
            content_hash(data)
        elapsed_ms = (time.perf_counter() - start) * 1000
        assert elapsed_ms < 500, f"10K hashes took {elapsed_ms:.0f}ms (target: <500ms)"


class TestBatchTransformPerformance:
    def test_1k_batch_under_2s(self):
        cfg = fraud_detection_config()
        pipe = TransformPipeline(cfg)
        signals = [_signal(i) for i in range(1000)]
        start = time.perf_counter()
        pipe.transform_batch(signals)
        elapsed_ms = (time.perf_counter() - start) * 1000
        assert elapsed_ms < 2000, f"1K batch took {elapsed_ms:.0f}ms (target: <2s)"

    def test_1k_full_pipeline_under_3s(self):
        cfg = fraud_detection_config()
        pipe = TransformPipeline(cfg)
        signals = [_signal(i) for i in range(1000)]
        start = time.perf_counter()
        pipe.process_to_decision_event(signals)
        elapsed_ms = (time.perf_counter() - start) * 1000
        assert elapsed_ms < 3000, f"1K pipeline took {elapsed_ms:.0f}ms (target: <3s)"
