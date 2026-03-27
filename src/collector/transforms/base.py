"""Base transform protocol and shared helpers.

All signal-to-evidence transforms implement the ``SignalTransform`` Protocol.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

from collector.core.attribution import Attribution
from collector.core.confidence import compute_confidence
from collector.core.context import contextualize
from collector.core.evidence_unit import EvidenceUnit, TemporalGrounding
from collector.core.provenance import ProvenanceChain, ProvenanceStep, content_hash

if TYPE_CHECKING:
    from collector.config import CollectionConfig
    from collector.core.signal import RawSignal


@runtime_checkable
class SignalTransform(Protocol):
    """Protocol for signal-to-evidence transforms."""

    def __call__(self, signal: RawSignal, *, config: CollectionConfig) -> EvidenceUnit:
        """Transform a raw signal into an evidence unit.

        Parameters
        ----------
        signal : RawSignal
            Input signal.
        config : CollectionConfig
            Collection configuration.

        Returns
        -------
        EvidenceUnit
            Transformed evidence unit.
        """
        ...  # pragma: no cover


def build_evidence_unit(
    signal: RawSignal,
    *,
    config: CollectionConfig,
    transform_name: str,
    signal_quality: float = 1.0,
    known_gaps: tuple[str, ...] = (),
    actor_type: str | None = None,
    organizational_role: str | None = None,
    delegation_chain: tuple[str, ...] = (),
    responsibility_boundary: str | None = None,
    system_state: dict[str, Any] | None = None,
    organizational_context: dict[str, Any] | None = None,
    dependency_relations: list[str] | None = None,
) -> EvidenceUnit:
    """Shared builder for all transforms.

    Parameters
    ----------
    signal : RawSignal
        Input signal.
    config : CollectionConfig
        Collection configuration.
    transform_name : str
        Name of the calling transform.
    signal_quality : float
        Signal quality score.
    known_gaps : tuple of str
        Known observation gaps.
    actor_type : str or None
        Override actor type (defaults to config.default_actor_type).
    organizational_role : str or None
        Actor's organizational role.
    delegation_chain : tuple of str
        Delegation chain from original authority.
    responsibility_boundary : str or None
        Actor's responsibility scope.
    system_state : dict or None
        System state at collection time.
    organizational_context : dict or None
        Team ownership, responsibility boundaries, policies.
    dependency_relations : list of str or None
        Relations to other signals or systems.

    Returns
    -------
    EvidenceUnit
        Fully constructed evidence unit.
    """
    now = datetime.now(tz=UTC)
    input_data = dict(signal.payload)
    input_h = content_hash(input_data)

    enrichment = contextualize(
        signal,
        system_state=system_state,
        organizational_context=organizational_context,
        dependency_relations=dependency_relations,
    )
    output_data = {**input_data, **enrichment}
    output_h = content_hash(output_data)

    step = ProvenanceStep(
        step_name=f"{transform_name}_transform",
        input_hash=input_h,
        output_hash=output_h,
        transform_name=transform_name,
        timestamp=now,
    )
    provenance = ProvenanceChain(origin=signal.source).append(step).verify()

    attribution = Attribution(
        actor_id=signal.source,
        actor_type=actor_type if actor_type is not None else config.default_actor_type,
        organizational_role=organizational_role,
        delegation_chain=delegation_chain,
        responsibility_boundary=responsibility_boundary,
    )

    confidence = compute_confidence(
        signal_quality=signal_quality,
        collection_completeness=1.0,
        known_gaps=known_gaps,
    )

    lag_ms = (now - signal.timestamp).total_seconds() * 1000.0
    temporal = TemporalGrounding(
        collection_timestamp=now,
        event_timestamp=signal.timestamp,
        processing_lag_ms=max(0.0, lag_ms),
    )

    return EvidenceUnit(
        unit_id=f"eu-{uuid.uuid4().hex[:12]}",
        signal=signal,
        provenance=provenance,
        attribution=attribution,
        confidence=confidence,
        context_enrichment=enrichment,
        temporal_grounding=temporal,
    )
