import pytest

from collector.collector import EvidenceCollector, ValidationMode
from collector.config import fraud_detection_config
from collector.core.signal import SignalType
from tests.conftest import make_signal


class TestEvidenceCollector:
    def test_add_and_flush(self):
        col = EvidenceCollector(config=fraud_detection_config())
        col.add(make_signal(signal_id="s1"))
        col.add(make_signal(signal_id="s2"))
        assert col.pending_count == 2
        events = col.flush()
        assert len(events) == 2
        assert col.pending_count == 0

    def test_add_many(self):
        col = EvidenceCollector(config=fraud_detection_config())
        col.add_many([make_signal(signal_id=f"s{i}") for i in range(5)])
        assert col.pending_count == 5

    def test_transform(self):
        col = EvidenceCollector(config=fraud_detection_config())
        col.add(make_signal())
        units = col.transform()
        assert len(units) == 1
        assert units[0].unit_id.startswith("eu-")

    def test_collect_one(self):
        col = EvidenceCollector(config=fraud_detection_config())
        event = col.collect_one(make_signal())
        assert "decision_id" in event
        assert "schema_version" in event

    def test_collect_one_updates_validation_errors(self, monkeypatch):
        col = EvidenceCollector(config=fraud_detection_config())
        monkeypatch.setattr(
            "collector.collector.validate_provenance",
            lambda event: ["broken provenance"],
        )

        col.collect_one(make_signal())

        assert col.validation_errors == ["broken provenance"]

    def test_collect_one_skips_validation_when_disabled(self, monkeypatch):
        col = EvidenceCollector(config=fraud_detection_config(), validate=False)
        monkeypatch.setattr(
            "collector.collector.validate_provenance",
            lambda event: ["broken provenance"],
        )

        col.collect_one(make_signal())

        assert col.validation_errors == []

    def test_validation_mode_property(self):
        col = EvidenceCollector(
            config=fraud_detection_config(),
            validation_mode=ValidationMode.PROVENANCE,
        )

        assert col.validation_mode is ValidationMode.PROVENANCE

    def test_validation_mode_none_skips_validation(self, monkeypatch):
        col = EvidenceCollector(
            config=fraud_detection_config(),
            validation_mode=ValidationMode.NONE,
        )
        monkeypatch.setattr(
            "collector.collector.validate_provenance",
            lambda event: ["broken provenance"],
        )

        col.collect_one(make_signal())

        assert col.validation_errors == []

    def test_validate_false_maps_to_none_mode(self):
        col = EvidenceCollector(config=fraud_detection_config(), validate=False)
        assert col.validation_mode is ValidationMode.NONE

    def test_invalid_validation_mode_rejected(self):
        with pytest.raises(ValueError, match="validation_mode"):
            EvidenceCollector(
                config=fraud_detection_config(),
                validation_mode="invalid",
            )

    def test_conflicting_validate_and_validation_mode_rejected(self):
        with pytest.raises(ValueError, match="validation_mode"):
            EvidenceCollector(
                config=fraud_detection_config(),
                validate=False,
                validation_mode=ValidationMode.PROVENANCE,
            )

    def test_validation_errors_empty_on_valid(self):
        col = EvidenceCollector(config=fraud_detection_config())
        col.add(make_signal())
        col.flush()
        assert col.validation_errors == []

    def test_no_validation(self):
        col = EvidenceCollector(config=fraud_detection_config(), validate=False)
        col.add(make_signal())
        events = col.flush()
        assert len(events) == 1
        assert col.validation_errors == []

    def test_capabilities(self):
        col = EvidenceCollector(config=fraud_detection_config())
        caps = col.capabilities
        assert SignalType.EVENT in caps.supported_signal_types
        assert caps.schema_version == "0.1.0"

    def test_config_property(self):
        cfg = fraud_detection_config()
        col = EvidenceCollector(config=cfg)
        assert col.config is cfg

    def test_transform_preserves_buffer_when_pipeline_fails(self):
        col = EvidenceCollector(config=fraud_detection_config())
        col.add(make_signal(signal_id="s1"))

        class FailingPipeline:
            def transform_batch(self, signals):
                raise RuntimeError("boom")

        col._pipeline = FailingPipeline()

        with pytest.raises(RuntimeError, match="boom"):
            col.transform()

        assert col.pending_count == 1
