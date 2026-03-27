from datetime import UTC, datetime

import pytest

from collector.core.signal import RawSignal, SignalType


class TestSignalType:
    def test_all_values(self):
        assert len(SignalType) == 5
        assert SignalType.LOG.value == "log"
        assert SignalType.METRIC.value == "metric"
        assert SignalType.EVENT.value == "event"
        assert SignalType.CONFIG_CHANGE.value == "config_change"
        assert SignalType.HUMAN_ACTION.value == "human_action"


class TestRawSignal:
    def _make(self, **overrides):
        defaults = {
            "signal_id": "sig-001",
            "signal_type": SignalType.EVENT,
            "payload": {"score": 0.9},
            "source": "test-system",
            "timestamp": datetime(2026, 1, 1, tzinfo=UTC),
        }
        return RawSignal(**(defaults | overrides))

    def test_create(self):
        s = self._make()
        assert s.signal_id == "sig-001"
        assert s.signal_type == SignalType.EVENT
        assert s.payload["score"] == 0.9
        assert s.source == "test-system"

    def test_frozen(self):
        s = self._make()
        with pytest.raises(AttributeError):
            s.signal_id = "new"  # type: ignore[misc]

    def test_payload_immutable(self):
        s = self._make()
        with pytest.raises(TypeError):
            s.payload["new_key"] = 1  # type: ignore[index]

    def test_metadata_immutable(self):
        s = self._make(metadata={"k": "v"})
        with pytest.raises(TypeError):
            s.metadata["new"] = 1  # type: ignore[index]

    def test_empty_signal_id_rejected(self):
        with pytest.raises(ValueError, match="signal_id"):
            self._make(signal_id="")

    def test_empty_source_rejected(self):
        with pytest.raises(ValueError, match="source"):
            self._make(source="")

    def test_default_metadata(self):
        s = self._make()
        assert len(s.metadata) == 0

    def test_naive_datetime_rejected(self):
        with pytest.raises(ValueError, match="timezone-aware"):
            self._make(timestamp=datetime(2026, 1, 1))
