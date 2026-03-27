import pytest

from collector.config import fraud_detection_config
from collector.core.signal import SignalType
from collector.pipeline import TransformPipeline
from collector.transforms.action_to_evidence import transform_action
from collector.transforms.base import SignalTransform
from collector.transforms.config_to_evidence import transform_config
from collector.transforms.event_to_evidence import transform_event
from collector.transforms.log_to_evidence import transform_log
from collector.transforms.metric_to_evidence import transform_metric
from tests.conftest import make_signal

ALL_TRANSFORMS = [
    transform_event,
    transform_log,
    transform_metric,
    transform_config,
    transform_action,
]


class TestTransformProtocol:
    @pytest.mark.parametrize("transform_fn", ALL_TRANSFORMS)
    def test_satisfies_protocol(self, transform_fn):
        assert isinstance(transform_fn, SignalTransform)


class TestAllSignalTypesProduceValidOutput:
    @pytest.mark.parametrize("signal_type", list(SignalType))
    def test_pipeline_produces_valid_evidence(self, signal_type):
        pipe = TransformPipeline(fraud_detection_config())
        sig = make_signal(
            signal_type=signal_type,
            payload={"score": 0.5, "rationale": "test"},
        )
        unit = pipe.transform(sig)
        assert unit.unit_id.startswith("eu-")
        assert unit.signal.signal_type == signal_type
        assert 0.0 <= unit.confidence.value <= 1.0
        assert unit.provenance.integrity_verified is True


class TestEventTransform:
    def test_basic(self):
        cfg = fraud_detection_config()
        unit = transform_event(make_signal(), config=cfg)
        assert unit.unit_id.startswith("eu-")
        assert unit.signal.signal_id == "sig-001"
        assert unit.confidence.value == 1.0


class TestLogTransform:
    def test_with_score(self):
        cfg = fraud_detection_config()
        unit = transform_log(make_signal(signal_type=SignalType.LOG), config=cfg)
        assert unit.confidence.signal_quality == 1.0
        assert len(unit.confidence.known_gaps) == 0

    def test_without_score(self):
        cfg = fraud_detection_config()
        sig = make_signal(signal_type=SignalType.LOG, payload={"message": "something"})
        unit = transform_log(sig, config=cfg)
        assert unit.confidence.signal_quality == 0.7
        assert "missing_score_key" in unit.confidence.known_gaps


class TestMetricTransform:
    def test_basic(self):
        cfg = fraud_detection_config()
        unit = transform_metric(make_signal(signal_type=SignalType.METRIC), config=cfg)
        assert unit.confidence.signal_quality == 1.0


class TestConfigTransform:
    def test_with_score(self):
        cfg = fraud_detection_config()
        unit = transform_config(make_signal(signal_type=SignalType.CONFIG_CHANGE), config=cfg)
        assert len(unit.confidence.known_gaps) == 0

    def test_without_score(self):
        cfg = fraud_detection_config()
        sig = make_signal(signal_type=SignalType.CONFIG_CHANGE, payload={"threshold": 0.5})
        unit = transform_config(sig, config=cfg)
        assert "no_prediction_score" in unit.confidence.known_gaps


class TestActionTransform:
    def test_with_rationale(self):
        cfg = fraud_detection_config()
        sig = make_signal(
            signal_type=SignalType.HUMAN_ACTION,
            payload={"rationale": "suspicious pattern", "score": 0.9},
        )
        unit = transform_action(sig, config=cfg)
        assert unit.confidence.signal_quality == 0.9
        assert len(unit.confidence.known_gaps) == 0
        assert unit.attribution.actor_type == "human"

    def test_without_rationale(self):
        cfg = fraud_detection_config()
        sig = make_signal(signal_type=SignalType.HUMAN_ACTION, payload={"override": True})
        unit = transform_action(sig, config=cfg)
        assert unit.confidence.signal_quality == 0.7
        assert "missing_override_rationale" in unit.confidence.known_gaps
        assert unit.attribution.actor_type == "human"


class TestBuildEvidenceUnitContextPassthrough:
    def test_system_state_passed(self):
        from collector.transforms.base import build_evidence_unit

        cfg = fraud_detection_config()
        sig = make_signal()
        unit = build_evidence_unit(
            sig,
            config=cfg,
            transform_name="test",
            system_state={"load": 0.5},
        )
        assert unit.context_enrichment["system_state"] == {"load": 0.5}

    def test_organizational_context_passed(self):
        from collector.transforms.base import build_evidence_unit

        cfg = fraud_detection_config()
        sig = make_signal()
        unit = build_evidence_unit(
            sig,
            config=cfg,
            transform_name="test",
            organizational_context={"team": "fraud"},
        )
        assert unit.context_enrichment["organizational_context"] == {"team": "fraud"}

    def test_attribution_override(self):
        from collector.transforms.base import build_evidence_unit

        cfg = fraud_detection_config()
        sig = make_signal()
        unit = build_evidence_unit(
            sig,
            config=cfg,
            transform_name="test",
            actor_type="human",
            organizational_role="fraud-analyst",
            delegation_chain=("cro", "fraud-team"),
            responsibility_boundary="fraud-detection",
        )
        assert unit.attribution.actor_type == "human"
        assert unit.attribution.organizational_role == "fraud-analyst"
        assert unit.attribution.delegation_chain == ("cro", "fraud-team")
        assert unit.attribution.responsibility_boundary == "fraud-detection"
