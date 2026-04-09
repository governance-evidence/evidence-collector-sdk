"""Serialize evidence units to Decision Event Schema format.

The output dict is directly consumable by Governance Drift Toolkit's
``integrations/decision_event_schema.py`` (``extract_scores``,
``extract_features``).
"""

from __future__ import annotations

import hashlib
import json
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collector.config import DecisionEventMappingConfig
    from collector.core.evidence_unit import EvidenceUnit

#: Decision Event Schema schema version emitted by this writer.
SCHEMA_VERSION = "0.3.0"


def to_decision_event(
    unit: EvidenceUnit,
    *,
    mapping: DecisionEventMappingConfig | None = None,
) -> dict[str, Any]:
    """Serialize an evidence unit to a decision event (Decision Event Schema) dict.

    The output conforms to the Decision Event Schema and includes
    top-level ``score`` and feature keys for Governance Drift Toolkit compatibility.

    Parameters
    ----------
    unit : EvidenceUnit
        Evidence unit to serialize.
    mapping : DecisionEventMappingConfig or None
        Field mapping configuration. If None, uses default mapping.

    Returns
    -------
    dict
        Decision Event Schema-compatible decision event.
    """
    from collector.config import DecisionEventMappingConfig

    if mapping is None:
        mapping = DecisionEventMappingConfig()

    payload = dict(unit.signal.payload)
    legacy_decision_type = _to_legacy_decision_type(unit.attribution.actor_type)
    decision_context = _build_decision_context(unit)
    decision_logic = _build_decision_logic(unit, payload, mapping)
    quality_indicators = _build_decision_quality_indicators(unit)
    human_override_record = _build_human_override(
        unit,
        payload,
        output=decision_logic["output"],
    )
    temporal_metadata = _build_temporal_metadata(unit)

    event: dict[str, Any] = {
        # Schema version
        "schema_version": SCHEMA_VERSION,
        # Legacy aliases kept for backward compatibility with existing consumers.
        "decision_id": unit.unit_id,
        "timestamp": unit.signal.timestamp.isoformat(),
        "decision_type": legacy_decision_type,
        # Governance Drift Toolkit compatibility: top-level score and features
        **payload,
        "decision_context": decision_context,
        "decision_logic": decision_logic,
        "decision_quality_indicators": quality_indicators,
        "human_override_record": human_override_record,
        "temporal_metadata": temporal_metadata,
        # Provenance metadata (Evidence Collector SDK extension)
        "_provenance": {
            "origin": unit.provenance.origin,
            "steps": [
                {
                    "step_name": s.step_name,
                    "transform_name": s.transform_name,
                    "input_hash": s.input_hash,
                    "output_hash": s.output_hash,
                    "timestamp": s.timestamp.isoformat(),
                }
                for s in unit.provenance.steps
            ],
            "integrity_verified": unit.provenance.integrity_verified,
        },
        # Attribution metadata (Evidence Collector SDK extension)
        "_attribution": {
            "actor_id": unit.attribution.actor_id,
            "actor_type": unit.attribution.actor_type,
            "organizational_role": unit.attribution.organizational_role,
            "delegation_chain": list(unit.attribution.delegation_chain),
            "responsibility_boundary": unit.attribution.responsibility_boundary,
        },
    }

    # Include signal metadata if configured
    if mapping.include_metadata and unit.signal.metadata:
        event["_signal_metadata"] = dict(unit.signal.metadata)

    return event


def _build_decision_context(unit: EvidenceUnit) -> dict[str, Any]:
    """Build the DES v0.3 decision context block."""
    return {
        "decision_id": unit.unit_id,
        "decision_type": unit.signal.signal_type.value,
        "available_inputs": _build_available_inputs(unit),
        "signal_type": unit.signal.signal_type.value,
        **dict(unit.context_enrichment),
    }


def _build_available_inputs(unit: EvidenceUnit) -> list[str]:
    """Build list of available inputs from signal and context.

    Parameters
    ----------
    unit : EvidenceUnit
        Evidence unit.

    Returns
    -------
    list of str
        Input source identifiers.
    """
    inputs = [unit.signal.source]
    deps = unit.context_enrichment.get("dependency_relations")
    if isinstance(deps, list):
        inputs.extend(str(d) for d in deps)
    return inputs


def _build_decision_logic(
    unit: EvidenceUnit,
    payload: dict[str, Any],
    mapping: DecisionEventMappingConfig,
) -> dict[str, Any]:
    """Extract decision_logic fields from payload using mapping config.

    Parameters
    ----------
    payload : dict
        Signal payload.
    mapping : DecisionEventMappingConfig
        Mapping configuration.

    Returns
    -------
    dict
        decision_logic (Decision Event Schema) object.
    """
    logic_type = _infer_logic_type(unit, payload, mapping)
    logic: dict[str, Any] = {
        "logic_type": logic_type,
        "output": _derive_output(payload),
    }
    if "rule_version" in payload:
        logic["rule_version"] = payload["rule_version"]
    # Extract thresholds using configurable keys
    thresholds: dict[str, Any] = {}
    for key in mapping.logic_threshold_keys:
        if key in payload:
            thresholds[key] = payload[key]
    if thresholds:
        logic["thresholds"] = thresholds
    # Extract parameters using configurable keys
    params: dict[str, Any] = {}
    for key in mapping.logic_parameter_keys:
        if key in payload:
            params[key] = payload[key]
    if params:
        logic["parameters"] = params
    return logic


def _infer_logic_type(
    unit: EvidenceUnit,
    payload: dict[str, Any],
    mapping: DecisionEventMappingConfig,
) -> str:
    """Infer a DES logic_type from the signal category and payload shape."""
    logic_type = "rule_based"
    if unit.attribution.actor_type == "human":
        return "human_decision"
    if unit.attribution.actor_type == "hybrid":
        return "hybrid"
    if unit.signal.signal_type.value == "config_change":
        return "policy_evaluation"
    if unit.signal.signal_type.value == "metric":
        return "rule_based"

    ml_keys = {"score", *mapping.logic_parameter_keys}
    if any(key in payload for key in ml_keys):
        logic_type = "ml_inference"
    elif "rule_version" in payload or any(key in payload for key in mapping.logic_threshold_keys):
        logic_type = "rule_based"
    return logic_type


def _derive_output(payload: dict[str, Any]) -> object:
    """Derive the final decision output from a payload."""
    preferred_keys = (
        "output",
        "decision",
        "result",
        "action",
        "status",
        "score",
        "new_threshold",
        "override",
    )
    for key in preferred_keys:
        if key in payload:
            return payload[key]
    return {"observed_payload_keys": sorted(payload)}


def _build_decision_quality_indicators(unit: EvidenceUnit) -> dict[str, Any]:
    """Build the decision_quality_indicators block."""
    return {
        "confidence_score": unit.confidence.value,
        "signal_quality": unit.confidence.signal_quality,
        "collection_completeness": unit.confidence.collection_completeness,
        "uncertainty_flags": list(unit.confidence.known_gaps),
        "ground_truth_available": False,
    }


def _build_human_override(
    unit: EvidenceUnit,
    payload: dict[str, Any],
    *,
    output: object,
) -> dict[str, Any]:
    """Build a DES v0.3 human_override_record block.

    Parameters
    ----------
    unit : EvidenceUnit
        Evidence unit being serialized.
    payload : dict
        Signal payload.
    output : Any
        Final decision output recorded in decision_logic.output.

    Returns
    -------
    dict
        Decision Event Schema human_override_record.
    """
    override_occurred = bool(payload.get("override", False))
    override_actor = {
        "actor_id": unit.attribution.actor_id,
        "actor_role": unit.attribution.organizational_role or unit.attribution.actor_type,
        "authorization_level": (
            "human_operator" if unit.attribution.actor_type == "human" else "system_managed"
        ),
    }
    override: dict[str, Any] = {
        "override_occurred": override_occurred,
    }
    if "override" in payload:
        override["override_decision"] = payload["override"]
    if "independence_assessment" in payload:
        override["independence_assessment"] = payload["independence_assessment"]
    if "rationale" in payload:
        override["basis_for_deviation"] = payload["rationale"]

    if unit.attribution.actor_type == "human":
        override["override_actor"] = override_actor
        override["override_rationale"] = str(payload.get("rationale", "No rationale recorded."))

    if override_occurred:
        override["original_output"] = payload.get(
            "original_output",
            payload.get("recommended_output"),
        )
        override["overridden_output"] = payload.get("overridden_output", output)
        override["override_timestamp"] = unit.signal.timestamp.isoformat()
        override["override_actor"] = override_actor
        override["override_rationale"] = str(
            payload.get("rationale", "Manual override recorded without rationale.")
        )

    return override


def _build_temporal_metadata(unit: EvidenceUnit) -> dict[str, Any]:
    """Build the DES v0.3 temporal metadata block."""
    event_timestamp = unit.temporal_grounding.event_timestamp.isoformat()
    collection_timestamp = unit.temporal_grounding.collection_timestamp.isoformat()
    sequence_number = _coerce_non_negative_int(unit.signal.metadata.get("sequence_number"), 0)
    previous_hash = unit.signal.metadata.get("previous_hash")
    chain_payload = {
        "unit_id": unit.unit_id,
        "signal_id": unit.signal.signal_id,
        "event_timestamp": event_timestamp,
        "collection_timestamp": collection_timestamp,
        "provenance_tail": (
            unit.provenance.steps[-1].output_hash
            if unit.provenance.steps
            else unit.signal.signal_id
        ),
        "sequence_number": sequence_number,
    }
    current_hash = hashlib.sha256(
        json.dumps(chain_payload, sort_keys=True).encode("utf-8")
    ).hexdigest()

    return {
        "event_timestamp": event_timestamp,
        "decision_timestamp": event_timestamp,
        "evidence_availability_timestamp": collection_timestamp,
        "processing_duration_ms": unit.temporal_grounding.processing_lag_ms,
        "processing_lag_ms": unit.temporal_grounding.processing_lag_ms,
        "sequence_number": sequence_number,
        "hash_chain": {
            "previous_hash": previous_hash if isinstance(previous_hash, str) else None,
            "current_hash": current_hash,
            "algorithm": "SHA-256",
        },
        "evidence_tier": "lightweight",
    }


def _coerce_non_negative_int(value: object, default: int) -> int:
    """Return a non-negative integer or a default value."""
    if isinstance(value, bool):
        return default
    if isinstance(value, int) and value >= 0:
        return value
    return default


#: Map internal actor types to decision_type (Decision Event Schema) enum values.
_ACTOR_TO_LEGACY_DECISION_EVENT: dict[str, str] = {
    "system": "automated",
    "human": "human",
    "hybrid": "hybrid",
}


def _to_legacy_decision_type(actor_type: str) -> str:
    """Map internal actor_type to the legacy top-level decision_type alias.

    Parameters
    ----------
    actor_type : str
        Internal actor type ("system", "human", "hybrid").

    Returns
    -------
    str
        decision_type (Decision Event Schema) ("automated", "human", "hybrid").
    """
    return _ACTOR_TO_LEGACY_DECISION_EVENT.get(actor_type, actor_type)
