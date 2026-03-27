"""Contextualization engine for evidence collection.

Enriches raw signals with system state, organizational role,
and dependency information needed for governance interpretation.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collector.core.signal import RawSignal


def contextualize(
    signal: RawSignal,
    *,
    system_state: dict[str, Any] | None = None,
    organizational_context: dict[str, Any] | None = None,
    dependency_relations: list[str] | None = None,
) -> dict[str, object]:
    """Build context enrichment for an evidence unit.

    Parameters
    ----------
    signal : RawSignal
        The raw signal being contextualized.
    system_state : dict or None
        Current system state at collection time.
    organizational_context : dict or None
        Team ownership, responsibility boundaries, policies.
    dependency_relations : list of str or None
        Relations to other signals or systems.

    Returns
    -------
    dict
        Context enrichment mapping for the evidence unit.
    """
    enrichment: dict[str, object] = {
        "signal_source": signal.source,
        "signal_type": signal.signal_type.value,
    }
    if system_state is not None:
        enrichment["system_state"] = system_state
    if organizational_context is not None:
        enrichment["organizational_context"] = organizational_context
    if dependency_relations is not None:
        enrichment["dependency_relations"] = dependency_relations
    return enrichment
