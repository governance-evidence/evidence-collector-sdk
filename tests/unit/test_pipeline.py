import pytest

from collector.config import CollectionConfig, DecisionEventMappingConfig, fraud_detection_config
from collector.core.signal import SignalType
from collector.pipeline import TransformPipeline
from tests.conftest import make_signal


class TestTransformPipeline:
    def test_transform_event(self):
        pipe = TransformPipeline(fraud_detection_config())
        unit = pipe.transform(make_signal())
        assert unit.unit_id.startswith("eu-")

    def test_transform_all_types(self):
        pipe = TransformPipeline(fraud_detection_config())
        for st in SignalType:
            sig = make_signal(signal_type=st, payload={"score": 0.5, "rationale": "test"})
            unit = pipe.transform(sig)
            assert unit.signal.signal_type == st

    def test_disabled_type_raises(self):
        cfg = CollectionConfig(
            name="limited",
            enabled_signal_types=frozenset({SignalType.EVENT}),
        )
        pipe = TransformPipeline(cfg)
        with pytest.raises(ValueError, match="not enabled"):
            pipe.transform(make_signal(signal_type=SignalType.LOG))

    def test_transform_batch(self):
        pipe = TransformPipeline(fraud_detection_config())
        signals = [make_signal(signal_type=SignalType.EVENT) for _ in range(5)]
        units = pipe.transform_batch(signals)
        assert len(units) == 5

    def test_transform_batch_skips_disabled(self):
        cfg = CollectionConfig(
            name="limited",
            enabled_signal_types=frozenset({SignalType.EVENT}),
        )
        pipe = TransformPipeline(cfg)
        signals = [
            make_signal(signal_type=SignalType.EVENT),
            make_signal(signal_type=SignalType.LOG),
        ]
        units = pipe.transform_batch(signals)
        assert len(units) == 1

    def test_process_to_decision_event(self):
        pipe = TransformPipeline(fraud_detection_config())
        signals = [make_signal() for _ in range(3)]
        events = pipe.process_to_decision_event(signals)
        assert len(events) == 3
        for e in events:
            assert "decision_id" in e
            assert "schema_version" in e

    def test_process_to_decision_event_uses_config_mapping(self):
        cfg = CollectionConfig(
            name="custom-mapping",
            enabled_signal_types=frozenset({SignalType.EVENT}),
            decision_event_mapping=DecisionEventMappingConfig(
                logic_parameter_keys=("custom_param",),
                logic_threshold_keys=("custom_threshold",),
            ),
        )
        pipe = TransformPipeline(cfg)
        signal = make_signal(
            signal_type=SignalType.EVENT,
            payload={
                "score": 0.9,
                "custom_param": "model-x",
                "custom_threshold": 0.42,
            },
        )

        event = pipe.process_to_decision_event([signal])[0]

        assert event["decision_logic"] == {
            "logic_type": "ml_inference",
            "output": 0.9,
            "thresholds": {"custom_threshold": 0.42},
            "parameters": {"custom_param": "model-x"},
        }

    def test_config_property(self):
        cfg = fraud_detection_config()
        pipe = TransformPipeline(cfg)
        assert pipe.config is cfg

    def test_no_route_in_batch_skips(self):
        cfg = CollectionConfig(
            name="all-types",
            enabled_signal_types=frozenset(SignalType),
        )
        pipe = TransformPipeline(cfg, routes={})
        signals = [make_signal(signal_type=SignalType.EVENT)]
        units = pipe.transform_batch(signals)
        assert len(units) == 0

    def test_no_route_transform_raises(self):
        cfg = CollectionConfig(
            name="all-types",
            enabled_signal_types=frozenset(SignalType),
        )
        pipe = TransformPipeline(cfg, routes={})
        with pytest.raises(ValueError, match="No transform route"):
            pipe.transform(make_signal(signal_type=SignalType.EVENT))
