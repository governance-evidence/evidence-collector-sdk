import json
from datetime import UTC, datetime

from collector.config import fraud_detection_config
from collector.core.signal import RawSignal, SignalType
from collector.output.decision_event_writer import to_decision_event
from collector.transforms.event_to_evidence import transform_event
from collector.validation import (
    validate_complete,
    validate_decision_event,
    validate_features,
    validate_provenance,
)


def _make_event():
    sig = RawSignal(
        signal_id="sig-001",
        signal_type=SignalType.EVENT,
        payload={"score": 0.87, "amount": 1500.0, "merchant_category": "electronics"},
        source="fraud-model",
        timestamp=datetime(2026, 1, 1, tzinfo=UTC),
    )
    unit = transform_event(sig, config=fraud_detection_config())
    return to_decision_event(unit)


class TestValidateDecisionEvent:
    def test_valid_event(self):
        event = _make_event()
        errors = validate_decision_event(event)
        assert errors == []

    def test_invalid_datetime_format(self):
        event = _make_event()
        event["timestamp"] = "not-a-datetime"
        errors = validate_decision_event(event)
        assert any("timestamp" in e for e in errors)

    def test_timestamp_without_timezone(self):
        event = _make_event()
        event["timestamp"] = "2026-01-01T00:00:00"
        errors = validate_decision_event(event)
        assert any("timezone" in e for e in errors)

    def test_non_string_timestamp_reports_type_error_only(self):
        event = _make_event()
        event["timestamp"] = 123
        errors = validate_decision_event(event)
        assert len(errors) > 0

    def test_missing_required_field(self):
        event = _make_event()
        del event["decision_context"]["decision_id"]
        errors = validate_decision_event(event)
        assert any("decision_id" in e for e in errors)

    def test_wrong_type(self):
        event = _make_event()
        event["decision_context"]["decision_id"] = 123
        errors = validate_decision_event(event)
        assert len(errors) > 0

    def test_with_external_schema(self, tmp_path):
        schema = {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "type": "object",
            "required": ["decision_id"],
            "properties": {"decision_id": {"type": "string"}},
        }
        schema_file = tmp_path / "schema.json"
        schema_file.write_text(json.dumps(schema))
        event = _make_event()
        errors = validate_decision_event(event, schema_path=schema_file)
        assert errors == []

    def test_external_schema_failure(self, tmp_path):
        schema = {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "type": "object",
            "required": ["missing_field"],
        }
        schema_file = tmp_path / "schema.json"
        schema_file.write_text(json.dumps(schema))
        event = _make_event()
        errors = validate_decision_event(event, schema_path=schema_file)
        assert len(errors) > 0


class TestValidateProvenance:
    def test_valid_provenance(self):
        event = _make_event()
        errors = validate_provenance(event)
        assert errors == []

    def test_missing_provenance(self):
        event = _make_event()
        del event["_provenance"]
        errors = validate_provenance(event)
        assert "Missing _provenance" in errors[0]

    def test_broken_chain(self):
        event = _make_event()
        event["_provenance"]["steps"] = [
            {"output_hash": "aaa", "input_hash": "x"},
            {"output_hash": "ccc", "input_hash": "WRONG"},
        ]
        errors = validate_provenance(event)
        assert any("Broken provenance" in e for e in errors)

    def test_single_step_valid(self):
        event = _make_event()
        errors = validate_provenance(event)
        assert errors == []

    def test_multi_step_valid_chain(self):
        event = _make_event()
        event["_provenance"]["steps"] = [
            {"input_hash": "a", "output_hash": "b"},
            {"input_hash": "b", "output_hash": "c"},
            {"input_hash": "c", "output_hash": "d"},
        ]
        errors = validate_provenance(event)
        assert errors == []


class TestValidateFeatures:
    def test_all_present(self):
        event = _make_event()
        cfg = fraud_detection_config()
        errors = validate_features(event, config=cfg)
        assert errors == []

    def test_missing_feature(self):
        event = _make_event()
        del event["amount"]
        cfg = fraud_detection_config()
        errors = validate_features(event, config=cfg)
        assert any("amount" in e for e in errors)

    def test_missing_score(self):
        event = _make_event()
        del event["score"]
        cfg = fraud_detection_config()
        errors = validate_features(event, config=cfg)
        assert any("score" in e for e in errors)

    def test_skip_human_action(self):
        event = _make_event()
        event["decision_context"]["signal_type"] = "human_action"
        del event["amount"]
        cfg = fraud_detection_config()
        errors = validate_features(event, config=cfg)
        assert errors == []

    def test_skip_config_change(self):
        event = _make_event()
        event["decision_context"]["signal_type"] = "config_change"
        del event["score"]
        cfg = fraud_detection_config()
        errors = validate_features(event, config=cfg)
        assert errors == []

    def test_no_skip_when_disabled(self):
        event = _make_event()
        event["decision_context"]["signal_type"] = "human_action"
        del event["amount"]
        cfg = fraud_detection_config()
        errors = validate_features(event, config=cfg, skip_non_prediction=False)
        assert any("amount" in e for e in errors)


class TestValidateComplete:
    def test_all_pass(self):
        event = _make_event()
        cfg = fraud_detection_config()
        errors = validate_complete(event, config=cfg)
        assert errors == []

    def test_without_config(self):
        event = _make_event()
        errors = validate_complete(event)
        assert errors == []
