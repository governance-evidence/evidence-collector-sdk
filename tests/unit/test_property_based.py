"""Property-based tests using Hypothesis."""

from datetime import UTC, datetime

from hypothesis import given, settings
from hypothesis import strategies as st

from collector.config import SignalQualityDefaults, fraud_detection_config
from collector.core.attribution import Attribution
from collector.core.confidence import compute_confidence
from collector.core.provenance import ProvenanceChain, ProvenanceStep, content_hash
from collector.core.signal import RawSignal, SignalType
from collector.output.decision_event_writer import to_decision_event
from collector.pipeline import TransformPipeline
from collector.transforms.event_to_evidence import transform_event
from tests.conftest import make_signal


class TestConfidenceProperties:
    @given(
        signal_quality=st.floats(min_value=0.0, max_value=1.0),
        collection_completeness=st.floats(min_value=0.0, max_value=1.0),
        n_gaps=st.integers(min_value=0, max_value=20),
        gap_penalty=st.floats(min_value=0.0, max_value=0.2),
    )
    def test_value_always_in_bounds(
        self, signal_quality, collection_completeness, n_gaps, gap_penalty
    ):
        gaps = tuple(f"gap_{i}" for i in range(n_gaps))
        c = compute_confidence(
            signal_quality=signal_quality,
            collection_completeness=collection_completeness,
            known_gaps=gaps,
            gap_penalty=gap_penalty,
        )
        assert 0.0 <= c.value <= 1.0

    @given(
        signal_quality=st.floats(min_value=0.0, max_value=1.0),
        collection_completeness=st.floats(min_value=0.0, max_value=1.0),
    )
    def test_more_gaps_lower_confidence(self, signal_quality, collection_completeness):
        c0 = compute_confidence(
            signal_quality=signal_quality,
            collection_completeness=collection_completeness,
            known_gaps=(),
        )
        c5 = compute_confidence(
            signal_quality=signal_quality,
            collection_completeness=collection_completeness,
            known_gaps=("g1", "g2", "g3", "g4", "g5"),
        )
        assert c5.value <= c0.value


class TestContentHashProperties:
    @given(
        a=st.integers(min_value=-1000, max_value=1000),
        b=st.text(min_size=0, max_size=50),
    )
    def test_deterministic(self, a, b):
        data = {"a": a, "b": b}
        assert content_hash(data) == content_hash(data)

    @given(
        a=st.integers(min_value=0, max_value=1000),
    )
    def test_key_order_independent(self, a):
        d1 = {"x": a, "y": a + 1}
        d2 = {"y": a + 1, "x": a}
        assert content_hash(d1) == content_hash(d2)


class TestSignalQualityDefaultsProperties:
    @given(
        base=st.floats(min_value=0.0, max_value=1.0),
        missing=st.floats(min_value=0.0, max_value=1.0),
        penalty=st.floats(min_value=0.0, max_value=1.0),
    )
    def test_valid_construction(self, base, missing, penalty):
        qd = SignalQualityDefaults(
            base_quality=base,
            missing_key_quality=missing,
            gap_penalty_per_gap=penalty,
        )
        assert qd.base_quality == base


class TestAttributionProperties:
    @given(
        actor_type=st.sampled_from(["system", "human", "hybrid"]),
    )
    def test_valid_types_always_accepted(self, actor_type):
        a = Attribution(actor_id="test", actor_type=actor_type)
        assert a.actor_type == actor_type


class TestDecisionEventOutputProperties:
    @given(
        score=st.floats(min_value=0.0, max_value=1.0),
        amount=st.floats(min_value=0.0, max_value=1e6, allow_nan=False, allow_infinity=False),
    )
    @settings(max_examples=20)
    def test_required_fields_always_present(self, score, amount):
        sig = RawSignal(
            signal_id="sig-prop",
            signal_type=SignalType.EVENT,
            payload={"score": score, "amount": amount},
            source="prop-test",
            timestamp=datetime(2026, 1, 1, tzinfo=UTC),
        )
        unit = transform_event(sig, config=fraud_detection_config())
        event = to_decision_event(unit)
        assert "decision_id" in event
        assert "timestamp" in event
        assert "decision_type" in event
        assert "schema_version" in event
        assert event["score"] == score


class TestProvenanceChainProperties:
    @given(
        n_steps=st.integers(min_value=1, max_value=10),
    )
    @settings(max_examples=20)
    def test_chain_hash_is_deterministic(self, n_steps):
        chain = ProvenanceChain(origin="test")
        for i in range(n_steps):
            step = ProvenanceStep(
                step_name=f"step-{i}",
                input_hash=f"in-{i}",
                output_hash=f"out-{i}",
                transform_name=f"transform-{i}",
                timestamp=datetime(2026, 1, 1, tzinfo=UTC),
            )
            chain = chain.append(step)

        chain2 = ProvenanceChain(origin="test")
        for i in range(n_steps):
            step = ProvenanceStep(
                step_name=f"step-{i}",
                input_hash=f"in-{i}",
                output_hash=f"out-{i}",
                transform_name=f"transform-{i}",
                timestamp=datetime(2026, 1, 1, tzinfo=UTC),
            )
            chain2 = chain2.append(step)

        assert chain.steps == chain2.steps

    @given(
        n_steps=st.integers(min_value=1, max_value=5),
    )
    @settings(max_examples=20)
    def test_chain_always_verifies(self, n_steps):
        chain = ProvenanceChain(origin="test")
        for i in range(n_steps):
            step = ProvenanceStep(
                step_name=f"step-{i}",
                input_hash=content_hash({"i": i}),
                output_hash=content_hash({"i": i + 1}),
                transform_name=f"transform-{i}",
                timestamp=datetime(2026, 1, 1, tzinfo=UTC),
            )
            chain = chain.append(step)
        verified = chain.verify()
        assert verified.integrity_verified is True


class TestTransformIdempotencyProperties:
    @given(
        score=st.floats(min_value=0.0, max_value=1.0),
        amount=st.floats(min_value=0.0, max_value=1e6, allow_nan=False, allow_infinity=False),
    )
    @settings(max_examples=20)
    def test_same_signal_produces_same_provenance_hash(self, score, amount):
        pipe = TransformPipeline(fraud_detection_config())
        sig = make_signal(payload={"score": score, "amount": amount})
        u1 = pipe.transform(sig)
        u2 = pipe.transform(sig)
        assert u1.provenance.steps[0].input_hash == u2.provenance.steps[0].input_hash
        assert u1.provenance.steps[0].output_hash == u2.provenance.steps[0].output_hash
