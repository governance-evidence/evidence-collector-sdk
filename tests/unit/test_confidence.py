import pytest

from collector.core.confidence import ConfidenceScore, compute_confidence


class TestConfidenceScore:
    def test_create(self):
        c = ConfidenceScore(value=0.8, signal_quality=0.9, collection_completeness=0.7)
        assert c.value == 0.8
        assert c.known_gaps == ()

    def test_with_gaps(self):
        c = ConfidenceScore(
            value=0.5,
            signal_quality=0.6,
            collection_completeness=0.7,
            known_gaps=("missing_field",),
        )
        assert len(c.known_gaps) == 1

    @pytest.mark.parametrize("field", ["value", "signal_quality", "collection_completeness"])
    def test_negative_rejected(self, field):
        kwargs = {"value": 0.5, "signal_quality": 0.5, "collection_completeness": 0.5}
        kwargs[field] = -0.1
        with pytest.raises(ValueError, match=field):
            ConfidenceScore(**kwargs)

    @pytest.mark.parametrize("field", ["value", "signal_quality", "collection_completeness"])
    def test_above_one_rejected(self, field):
        kwargs = {"value": 0.5, "signal_quality": 0.5, "collection_completeness": 0.5}
        kwargs[field] = 1.1
        with pytest.raises(ValueError, match=field):
            ConfidenceScore(**kwargs)

    def test_nan_rejected(self):
        with pytest.raises(ValueError, match="value"):
            ConfidenceScore(value=float("nan"), signal_quality=0.5, collection_completeness=0.5)


class TestComputeConfidence:
    def test_basic(self):
        c = compute_confidence(signal_quality=0.8, collection_completeness=1.0)
        assert c.value == 0.9
        assert c.signal_quality == 0.8
        assert c.collection_completeness == 1.0

    def test_with_gaps(self):
        c = compute_confidence(
            signal_quality=1.0,
            collection_completeness=1.0,
            known_gaps=("gap1", "gap2"),
            gap_penalty=0.1,
        )
        assert c.value == pytest.approx(0.8)
        assert len(c.known_gaps) == 2

    def test_floor_at_zero(self):
        c = compute_confidence(
            signal_quality=0.1,
            collection_completeness=0.1,
            known_gaps=("g1", "g2", "g3", "g4"),
            gap_penalty=0.1,
        )
        assert c.value == 0.0

    def test_cap_at_one(self):
        c = compute_confidence(signal_quality=1.0, collection_completeness=1.0)
        assert c.value == 1.0
