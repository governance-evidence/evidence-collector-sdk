"""Flink source connector for evidence collection.

STUB: Defines the Protocol interface for reading raw signals
from a Flink data stream. Actual Flink dependency is not required.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class FlinkSourceReader(Protocol):
    """Protocol for reading raw signals from a Flink source."""

    def read_batch(self, *, batch_size: int = 100) -> list[dict[str, Any]]:
        """Read a batch of raw signal dicts from Flink.

        Parameters
        ----------
        batch_size : int
            Maximum signals to return per call.

        Returns
        -------
        list of dict
            Batch of raw signal data.
        """
        ...  # pragma: no cover

    def close(self) -> None:
        """Close the Flink source connection."""
        ...  # pragma: no cover
