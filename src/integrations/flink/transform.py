"""Flink transformation operator for evidence collection.

STUB: Defines the Protocol interface for a Flink operator that
transforms raw signals into evidence units within the pipeline.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class FlinkEvidenceOperator(Protocol):
    """Protocol for a Flink operator producing evidence events."""

    def process_element(self, _element: dict[str, Any]) -> dict[str, Any] | None:
        """Process a single element and optionally emit a Decision Event Schema event.

        Parameters
        ----------
        element : dict
            Raw signal data from the Flink stream.

        Returns
        -------
        dict or None
            Decision Event Schema event dict, or None if the element should be filtered.
        """
        ...  # pragma: no cover
