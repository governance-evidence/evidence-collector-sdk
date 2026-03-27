"""Flink sink for Governance Drift Toolkit consumption.

STUB: Defines the Protocol interface for writing Decision Event Schema evidence events
to a Flink sink that feeds Governance Drift Toolkit governance monitoring.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class FlinkEvidenceSink(Protocol):
    """Protocol for sinking Decision Event Schema events into a Flink output."""

    def write(self, event: dict[str, Any]) -> None:
        """Write a single Decision Event Schema event to the sink.

        Parameters
        ----------
        event : dict
            decision event (Decision Event Schema) dict.
        """
        ...  # pragma: no cover

    def flush(self) -> None:
        """Flush any buffered events."""
        ...  # pragma: no cover

    def close(self) -> None:
        """Close the sink connection."""
        ...  # pragma: no cover
