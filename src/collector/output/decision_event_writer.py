"""Serialize evidence units to Decision Event Schema format.

The output dict is directly consumable by Governance Drift Toolkit's
``integrations/decision_event_schema.py`` (``extract_scores``,
``extract_features``).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collector.config import DecisionEventMappingConfig
    from collector.core.evidence_unit import EvidenceUnit

#: Decision Event Schema schema version emitted by this writer.
SCHEMA_VERSION = "0.1.0"


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

    event: dict[str, Any] = {
        # Schema version
        "schema_version": SCHEMA_VERSION,
        # Required Decision Event Schema fields
        "decision_id": unit.unit_id,
        "timestamp": unit.signal.timestamp.isoformat(),
        "decision_type": _to_decision_event_decision_type(unit.attribution.actor_type),
        # Governance Drift Toolkit compatibility: top-level score and features
        **payload,
        # Decision Event Schema optional: decision_context
        "decision_context": {
            "available_inputs": _build_available_inputs(unit),
            "signal_type": unit.signal.signal_type.value,
            **dict(unit.context_enrichment),
        },
        # Decision Event Schema optional: decision_logic
        "decision_logic": _build_decision_logic(payload, mapping),
        # Decision Event Schema optional: decision_quality_indicators
        "decision_quality_indicators": {
            "confidence_score": unit.confidence.value,
            "signal_quality": unit.confidence.signal_quality,
            "collection_completeness": unit.confidence.collection_completeness,
            "uncertainty_flags": list(unit.confidence.known_gaps),
            "ground_truth_available": False,
        },
        # Decision Event Schema optional: temporal_metadata
        "temporal_metadata": {
            "decision_timestamp": unit.temporal_grounding.event_timestamp.isoformat(),
            "evidence_availability_timestamp": (
                unit.temporal_grounding.collection_timestamp.isoformat()
            ),
            "processing_lag_ms": unit.temporal_grounding.processing_lag_ms,
        },
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

    # Decision Event Schema optional: human_override_record (only for human actions)
    override = _build_human_override(payload, unit.attribution.actor_type)
    if override is not None:
        event["human_override_record"] = override

    return event


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
    logic: dict[str, Any] = {}
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


def _build_human_override(
    payload: dict[str, Any],
    actor_type: str,
) -> dict[str, Any] | None:
    """Build human_override_record if applicable.

    Only includes fields that are actually present in the payload.
    Does not write None values for missing fields.

    Parameters
    ----------
    payload : dict
        Signal payload.
    actor_type : str
        Actor type from attribution.

    Returns
    -------
    dict or None
        Decision Event Schema human_override_record, or None if not a human action.
    """
    if actor_type != "human":
        return None
    override: dict[str, Any] = {}
    if "override" in payload:
        override["override_decision"] = payload["override"]
    if "rationale" in payload:
        override["basis_for_deviation"] = payload["rationale"]
    if "independence_assessment" in payload:
        override["independence_assessment"] = payload["independence_assessment"]
    return override


#: Map internal actor types to decision_type (Decision Event Schema) enum values.
_ACTOR_TO_DECISION_EVENT: dict[str, str] = {
    "system": "automated",
    "human": "human",
    "hybrid": "hybrid",
}


def _to_decision_event_decision_type(actor_type: str) -> str:
    """Map internal actor_type to decision_type (Decision Event Schema) enum.

    Parameters
    ----------
    actor_type : str
        Internal actor type ("system", "human", "hybrid").

    Returns
    -------
    str
        decision_type (Decision Event Schema) ("automated", "human", "hybrid").
    """
    return _ACTOR_TO_DECISION_EVENT.get(actor_type, actor_type)
