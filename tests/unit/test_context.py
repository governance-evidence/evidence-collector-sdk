from datetime import UTC, datetime

from collector.core.context import contextualize
from collector.core.signal import RawSignal, SignalType


class TestContextualize:
    def _signal(self):
        return RawSignal(
            signal_id="sig-001",
            signal_type=SignalType.EVENT,
            payload={"score": 0.9},
            source="fraud-model",
            timestamp=datetime(2026, 1, 1, tzinfo=UTC),
        )

    def test_basic(self):
        result = contextualize(self._signal())
        assert result["signal_source"] == "fraud-model"
        assert result["signal_type"] == "event"

    def test_with_system_state(self):
        result = contextualize(self._signal(), system_state={"load": 0.5})
        assert result["system_state"] == {"load": 0.5}

    def test_with_org_context(self):
        result = contextualize(self._signal(), organizational_context={"team": "fraud"})
        assert result["organizational_context"] == {"team": "fraud"}

    def test_with_dependencies(self):
        result = contextualize(self._signal(), dependency_relations=["model-v2", "feature-store"])
        assert result["dependency_relations"] == ["model-v2", "feature-store"]

    def test_minimal(self):
        result = contextualize(self._signal())
        assert "system_state" not in result
        assert "organizational_context" not in result
        assert "dependency_relations" not in result
