from datetime import UTC, datetime

from collector.config import DecisionEventMappingConfig, fraud_detection_config
from collector.core.signal import RawSignal, SignalType
from collector.output.decision_event_writer import SCHEMA_VERSION, to_decision_event
from collector.transforms.action_to_evidence import transform_action
from collector.transforms.base import build_evidence_unit
from collector.transforms.config_to_evidence import transform_config
from collector.transforms.event_to_evidence import transform_event


class TestToDecisionEvent:
    def _make_unit(self):
        sig = RawSignal(
            signal_id="sig-001",
            signal_type=SignalType.EVENT,
            payload={"score": 0.87, "amount": 1500.0, "merchant_category": "electronics"},
            source="fraud-model-v3",
            timestamp=datetime(2026, 1, 1, tzinfo=UTC),
        )
        return transform_event(sig, config=fraud_detection_config())

    def test_required_fields(self):
        event = to_decision_event(self._make_unit())
        assert "decision_id" in event
        assert "timestamp" in event
        assert "decision_type" in event
        assert event["decision_context"]["decision_id"] == event["decision_id"]
        assert "logic_type" in event["decision_logic"]
        assert "event_timestamp" in event["temporal_metadata"]
        assert "override_occurred" in event["human_override_record"]

    def test_schema_version(self):
        event = to_decision_event(self._make_unit())
        assert event["schema_version"] == SCHEMA_VERSION

    def test_score_at_top_level(self):
        event = to_decision_event(self._make_unit())
        assert event["score"] == 0.87

    def test_features_at_top_level(self):
        event = to_decision_event(self._make_unit())
        assert event["amount"] == 1500.0
        assert event["merchant_category"] == "electronics"

    def test_decision_context(self):
        event = to_decision_event(self._make_unit())
        ctx = event["decision_context"]
        assert "available_inputs" in ctx
        assert "signal_type" in ctx
        assert ctx["decision_type"] == "event"

    def test_available_inputs_includes_deps(self):
        from collector.transforms.base import build_evidence_unit

        sig = RawSignal(
            signal_id="sig-001",
            signal_type=SignalType.EVENT,
            payload={"score": 0.9},
            source="model-v3",
            timestamp=datetime(2026, 1, 1, tzinfo=UTC),
        )
        unit = build_evidence_unit(
            sig,
            config=fraud_detection_config(),
            transform_name="test",
            dependency_relations=["feature-store", "cache"],
        )
        event = to_decision_event(unit)
        inputs = event["decision_context"]["available_inputs"]
        assert "model-v3" in inputs
        assert "feature-store" in inputs

    def test_decision_logic_empty_for_event(self):
        event = to_decision_event(self._make_unit())
        assert event["decision_logic"]["logic_type"] == "ml_inference"
        assert event["decision_logic"]["output"] == 0.87

    def test_decision_logic_for_config_change(self):
        sig = RawSignal(
            signal_id="cfg-001",
            signal_type=SignalType.CONFIG_CHANGE,
            payload={
                "old_threshold": 0.65,
                "new_threshold": 0.70,
                "rule_version": "v2.1",
                "model_version": "fraud-v3",
            },
            source="config-manager",
            timestamp=datetime(2026, 1, 1, tzinfo=UTC),
        )
        unit = transform_config(sig, config=fraud_detection_config())
        event = to_decision_event(unit)
        logic = event["decision_logic"]
        assert logic["rule_version"] == "v2.1"
        assert logic["thresholds"]["old_threshold"] == 0.65
        assert logic["parameters"]["model_version"] == "fraud-v3"

    def test_decision_logic_for_hybrid_actor(self):
        sig = RawSignal(
            signal_id="hyb-001",
            signal_type=SignalType.EVENT,
            payload={"decision": "review"},
            source="copilot-reviewer",
            timestamp=datetime(2026, 1, 1, tzinfo=UTC),
        )
        unit = build_evidence_unit(
            sig,
            config=fraud_detection_config(),
            transform_name="test",
            actor_type="hybrid",
        )
        event = to_decision_event(unit)
        assert event["decision_type"] == "hybrid"
        assert event["decision_logic"]["logic_type"] == "hybrid"

    def test_decision_logic_for_metric_signal(self):
        sig = RawSignal(
            signal_id="met-001",
            signal_type=SignalType.METRIC,
            payload={"score": 0.42, "latency_ms": 123},
            source="latency-monitor",
            timestamp=datetime(2026, 1, 1, tzinfo=UTC),
        )
        unit = build_evidence_unit(
            sig,
            config=fraud_detection_config(),
            transform_name="test",
        )
        event = to_decision_event(unit)
        assert event["decision_type"] == "automated"
        assert event["decision_logic"]["logic_type"] == "rule_based"
        assert event["decision_logic"]["output"] == 0.42

    def test_decision_logic_for_threshold_only_event(self):
        sig = RawSignal(
            signal_id="evt-threshold-001",
            signal_type=SignalType.EVENT,
            payload={"decision": "allow", "custom_thresh": 0.8},
            source="policy-engine",
            timestamp=datetime(2026, 1, 1, tzinfo=UTC),
        )
        mapping = DecisionEventMappingConfig(logic_threshold_keys=("custom_thresh",))
        unit = transform_event(sig, config=fraud_detection_config())
        event = to_decision_event(unit, mapping=mapping)
        assert event["decision_logic"]["logic_type"] == "rule_based"
        assert event["decision_logic"]["thresholds"]["custom_thresh"] == 0.8

    def test_decision_logic_defaults_to_rule_based_without_ml_or_threshold_keys(self):
        sig = RawSignal(
            signal_id="evt-rule-default-001",
            signal_type=SignalType.EVENT,
            payload={"decision": "allow"},
            source="policy-engine",
            timestamp=datetime(2026, 1, 1, tzinfo=UTC),
        )
        unit = transform_event(sig, config=fraud_detection_config())
        event = to_decision_event(unit)
        assert event["decision_logic"]["logic_type"] == "rule_based"
        assert event["decision_logic"]["output"] == "allow"

    def test_custom_mapping_config(self):
        sig = RawSignal(
            signal_id="cfg-001",
            signal_type=SignalType.CONFIG_CHANGE,
            payload={"custom_param": "v1", "custom_thresh": 0.5},
            source="config",
            timestamp=datetime(2026, 1, 1, tzinfo=UTC),
        )
        mapping = DecisionEventMappingConfig(
            logic_parameter_keys=("custom_param",),
            logic_threshold_keys=("custom_thresh",),
        )
        unit = transform_config(sig, config=fraud_detection_config())
        event = to_decision_event(unit, mapping=mapping)
        assert event["decision_logic"]["parameters"]["custom_param"] == "v1"
        assert event["decision_logic"]["thresholds"]["custom_thresh"] == 0.5

    def test_quality_indicators_include_components(self):
        event = to_decision_event(self._make_unit())
        qi = event["decision_quality_indicators"]
        assert 0.0 <= qi["confidence_score"] <= 1.0
        assert "signal_quality" in qi
        assert "collection_completeness" in qi
        assert qi["ground_truth_available"] is False

    def test_temporal_metadata_includes_lag(self):
        event = to_decision_event(self._make_unit())
        tm = event["temporal_metadata"]
        assert "event_timestamp" in tm
        assert "decision_timestamp" in tm
        assert "evidence_availability_timestamp" in tm
        assert "processing_duration_ms" in tm
        assert "hash_chain" in tm
        assert tm["evidence_tier"] == "lightweight"

    def test_temporal_metadata_coerces_boolean_sequence_number(self):
        sig = RawSignal(
            signal_id="sig-seq-bool",
            signal_type=SignalType.EVENT,
            payload={"score": 0.9},
            source="test",
            timestamp=datetime(2026, 1, 1, tzinfo=UTC),
            metadata={"sequence_number": True},
        )
        unit = transform_event(sig, config=fraud_detection_config())
        event = to_decision_event(unit)
        assert event["temporal_metadata"]["sequence_number"] == 0

    def test_temporal_metadata_preserves_non_negative_sequence_number(self):
        sig = RawSignal(
            signal_id="sig-seq-int",
            signal_type=SignalType.EVENT,
            payload={"score": 0.9},
            source="test",
            timestamp=datetime(2026, 1, 1, tzinfo=UTC),
            metadata={"sequence_number": 7},
        )
        unit = transform_event(sig, config=fraud_detection_config())
        event = to_decision_event(unit)
        assert event["temporal_metadata"]["sequence_number"] == 7

    def test_provenance_extension(self):
        prov = to_decision_event(self._make_unit())["_provenance"]
        assert prov["origin"] == "fraud-model-v3"
        assert len(prov["steps"]) == 1

    def test_provenance_marked_verified_for_valid_unit(self):
        prov = to_decision_event(self._make_unit())["_provenance"]
        assert prov["integrity_verified"] is True

    def test_attribution_extension(self):
        attr = to_decision_event(self._make_unit())["_attribution"]
        assert attr["actor_id"] == "fraud-model-v3"
        assert attr["actor_type"] == "system"

    def test_no_human_override_for_system(self):
        event = to_decision_event(self._make_unit())
        assert event["human_override_record"] == {"override_occurred": False}

    def test_human_override_for_action(self):
        sig = RawSignal(
            signal_id="act-001",
            signal_type=SignalType.HUMAN_ACTION,
            payload={"score": 0.9, "override": True, "rationale": "confirmed fraud"},
            source="analyst-jane",
            timestamp=datetime(2026, 1, 1, tzinfo=UTC),
        )
        unit = transform_action(sig, config=fraud_detection_config())
        event = to_decision_event(unit)
        assert event["decision_type"] == "human"
        assert event["decision_logic"]["logic_type"] == "human_decision"
        override = event["human_override_record"]
        assert override["override_decision"] is True
        assert override["basis_for_deviation"] == "confirmed fraud"
        assert override["override_rationale"] == "confirmed fraud"

    def test_human_override_no_none_values(self):
        sig = RawSignal(
            signal_id="act-002",
            signal_type=SignalType.HUMAN_ACTION,
            payload={"score": 0.9, "rationale": "test"},
            source="analyst",
            timestamp=datetime(2026, 1, 1, tzinfo=UTC),
        )
        unit = transform_action(sig, config=fraud_detection_config())
        event = to_decision_event(unit)
        override = event["human_override_record"]
        assert "override_decision" not in override
        assert override["basis_for_deviation"] == "test"
        assert override["override_rationale"] == "test"

    def test_metadata_included_by_default(self):
        sig = RawSignal(
            signal_id="sig-meta",
            signal_type=SignalType.EVENT,
            payload={"score": 0.9},
            source="test",
            timestamp=datetime(2026, 1, 1, tzinfo=UTC),
            metadata={"request_id": "req-123"},
        )
        unit = transform_event(sig, config=fraud_detection_config())
        event = to_decision_event(unit)
        assert event["_signal_metadata"]["request_id"] == "req-123"

    def test_metadata_excluded_when_configured(self):
        sig = RawSignal(
            signal_id="sig-meta",
            signal_type=SignalType.EVENT,
            payload={"score": 0.9},
            source="test",
            timestamp=datetime(2026, 1, 1, tzinfo=UTC),
            metadata={"request_id": "req-123"},
        )
        mapping = DecisionEventMappingConfig(include_metadata=False)
        unit = transform_event(sig, config=fraud_detection_config())
        event = to_decision_event(unit, mapping=mapping)
        assert "_signal_metadata" not in event

    def test_empty_metadata_not_included(self):
        event = to_decision_event(self._make_unit())
        assert "_signal_metadata" not in event

    def test_human_override_empty_payload(self):
        sig = RawSignal(
            signal_id="act-bare",
            signal_type=SignalType.HUMAN_ACTION,
            payload={"score": 0.5},
            source="analyst",
            timestamp=datetime(2026, 1, 1, tzinfo=UTC),
        )
        unit = transform_action(sig, config=fraud_detection_config())
        event = to_decision_event(unit)
        override = event["human_override_record"]
        assert "override_decision" not in override
        assert "basis_for_deviation" not in override
        assert "independence_assessment" not in override
        assert override["override_rationale"] == "No rationale recorded."

    def test_human_override_with_independence(self):
        sig = RawSignal(
            signal_id="act-003",
            signal_type=SignalType.HUMAN_ACTION,
            payload={
                "score": 0.9,
                "override": False,
                "rationale": "false positive",
                "independence_assessment": "independent",
            },
            source="analyst",
            timestamp=datetime(2026, 1, 1, tzinfo=UTC),
        )
        unit = transform_action(sig, config=fraud_detection_config())
        event = to_decision_event(unit)
        override = event["human_override_record"]
        assert override["independence_assessment"] == "independent"
