from datetime import UTC, datetime

import pytest

from collector.core.attribution import Attribution
from collector.core.confidence import ConfidenceScore
from collector.core.evidence_unit import EvidenceUnit, TemporalGrounding
from collector.core.provenance import ProvenanceChain
from collector.core.signal import RawSignal, SignalType


class TestTemporalGrounding:
    def test_create(self):
        t = TemporalGrounding(
            collection_timestamp=datetime(2026, 1, 1, 0, 1, tzinfo=UTC),
            event_timestamp=datetime(2026, 1, 1, tzinfo=UTC),
            processing_lag_ms=60000.0,
        )
        assert t.processing_lag_ms == 60000.0

    def test_negative_lag_rejected(self):
        with pytest.raises(ValueError, match="processing_lag_ms"):
            TemporalGrounding(
                collection_timestamp=datetime(2026, 1, 1, tzinfo=UTC),
                event_timestamp=datetime(2026, 1, 1, tzinfo=UTC),
                processing_lag_ms=-1.0,
            )

    def test_nan_lag_rejected(self):
        with pytest.raises(ValueError, match="processing_lag_ms"):
            TemporalGrounding(
                collection_timestamp=datetime(2026, 1, 1, tzinfo=UTC),
                event_timestamp=datetime(2026, 1, 1, tzinfo=UTC),
                processing_lag_ms=float("nan"),
            )


class TestEvidenceUnit:
    def _make(self, **overrides):
        ts = datetime(2026, 1, 1, tzinfo=UTC)
        defaults = {
            "unit_id": "eu-001",
            "signal": RawSignal(
                signal_id="sig-001",
                signal_type=SignalType.EVENT,
                payload={"score": 0.9},
                source="test",
                timestamp=ts,
            ),
            "provenance": ProvenanceChain(origin="test"),
            "attribution": Attribution(actor_id="test", actor_type="system"),
            "confidence": ConfidenceScore(
                value=0.8, signal_quality=0.9, collection_completeness=0.8
            ),
            "context_enrichment": {"key": "value"},
            "temporal_grounding": TemporalGrounding(
                collection_timestamp=ts,
                event_timestamp=ts,
                processing_lag_ms=0.0,
            ),
        }
        return EvidenceUnit(**(defaults | overrides))

    def test_create(self):
        u = self._make()
        assert u.unit_id == "eu-001"

    def test_empty_unit_id(self):
        with pytest.raises(ValueError, match="unit_id"):
            self._make(unit_id="")

    def test_context_immutable(self):
        u = self._make()
        with pytest.raises(TypeError):
            u.context_enrichment["new"] = 1  # type: ignore[index]
