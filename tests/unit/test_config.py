import pytest

from collector.config import (
    CollectionConfig,
    DecisionEventMappingConfig,
    SignalQualityDefaults,
    credit_scoring_config,
    fraud_detection_config,
)
from collector.core.signal import SignalType


class TestSignalQualityDefaults:
    def test_defaults(self):
        qd = SignalQualityDefaults()
        assert qd.base_quality == 1.0
        assert qd.missing_key_quality == 0.7
        assert qd.gap_penalty_per_gap == 0.05

    def test_custom(self):
        qd = SignalQualityDefaults(
            base_quality=0.9, missing_key_quality=0.5, gap_penalty_per_gap=0.1
        )
        assert qd.base_quality == 0.9

    @pytest.mark.parametrize("field", ["base_quality", "missing_key_quality"])
    def test_out_of_range(self, field):
        kwargs = {"base_quality": 0.5, "missing_key_quality": 0.5}
        kwargs[field] = 1.5
        with pytest.raises(ValueError, match=field):
            SignalQualityDefaults(**kwargs)

    def test_negative_gap_penalty(self):
        with pytest.raises(ValueError, match="gap_penalty_per_gap"):
            SignalQualityDefaults(gap_penalty_per_gap=-0.1)


class TestDecisionEventMappingConfig:
    def test_defaults(self):
        m = DecisionEventMappingConfig()
        assert "model_version" in m.logic_parameter_keys
        assert "old_threshold" in m.logic_threshold_keys
        assert m.include_metadata is True

    def test_custom(self):
        m = DecisionEventMappingConfig(
            logic_parameter_keys=("custom_param",),
            include_metadata=False,
        )
        assert m.logic_parameter_keys == ("custom_param",)
        assert m.include_metadata is False


class TestCollectionConfig:
    def test_create_default(self):
        c = CollectionConfig(name="test")
        assert c.name == "test"
        assert c.enabled_signal_types == frozenset(SignalType)
        assert c.default_actor_type == "system"
        assert c.score_key == "score"

    def test_empty_name_rejected(self):
        with pytest.raises(ValueError, match="name"):
            CollectionConfig(name="")

    def test_extra_immutable(self):
        c = CollectionConfig(name="test", extra={"k": "v"})
        with pytest.raises(TypeError):
            c.extra["new"] = 1  # type: ignore[index]

    def test_quality_for_configured(self):
        c = fraud_detection_config()
        qd = c.quality_for(SignalType.LOG)
        assert qd.base_quality == 1.0
        assert qd.missing_key_quality == 0.7

    def test_quality_for_human_action(self):
        c = fraud_detection_config()
        qd = c.quality_for(SignalType.HUMAN_ACTION)
        assert qd.base_quality == 0.9

    def test_quality_for_unknown_falls_back(self):
        c = CollectionConfig(name="test", quality={})
        qd = c.quality_for(SignalType.LOG)
        assert qd.base_quality == 1.0  # SignalQualityDefaults default

    def test_quality_immutable(self):
        c = CollectionConfig(name="test")
        with pytest.raises(TypeError):
            c.quality[SignalType.LOG] = SignalQualityDefaults()  # type: ignore[index]


class TestFactories:
    def test_fraud_detection(self):
        c = fraud_detection_config()
        assert c.name == "fraud_detection"
        assert c.score_key == "score"
        assert "amount" in c.feature_keys

    def test_credit_scoring(self):
        c = credit_scoring_config()
        assert c.name == "credit_scoring"
        assert SignalType.EVENT in c.enabled_signal_types
        assert "income" in c.feature_keys
