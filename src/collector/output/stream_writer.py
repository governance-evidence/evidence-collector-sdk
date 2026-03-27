"""Stream writers for evidence output.

Provides a Protocol for writing evidence batches and a concrete
JSONL file writer for testing and examples.
"""

from __future__ import annotations

import json
from typing import IO, TYPE_CHECKING, Any, Protocol, Self, runtime_checkable

if TYPE_CHECKING:
    from pathlib import Path


@runtime_checkable
class StreamWriter(Protocol):
    """Protocol for writing batches of Decision Event Schema events to an output sink."""

    def write_batch(self, events: list[dict[str, Any]]) -> None:
        """Write a batch of serialized Decision Event Schema events.

        Parameters
        ----------
        events : list of dict
            Batch of decision event (Decision Event Schema) dicts.
        """
        ...  # pragma: no cover

    def close(self) -> None:
        """Close the writer and release resources."""
        ...  # pragma: no cover


class JsonlStreamWriter:
    """Write Decision Event Schema events to a JSONL file.

    Parameters
    ----------
    path : Path
        Output file path.
    """

    def __init__(self, path: Path) -> None:
        self._path = path
        self._file: IO[str] | None = path.open("a", encoding="utf-8")

    @property
    def closed(self) -> bool:
        """Return whether the underlying file handle has been closed."""
        return self._file is None

    def __enter__(self) -> Self:
        """Enter the writer context."""
        return self

    def __exit__(self, _exc_type: object, exc: object, _tb: object) -> None:
        """Close the writer when leaving a context manager block."""
        self.close()

    def write_batch(self, events: list[dict[str, Any]]) -> None:
        """Append events as JSON lines.

        Parameters
        ----------
        events : list of dict
            Batch of decision event (Decision Event Schema) dicts.
        """
        file_handle = self._require_open_file()
        for event in events:
            file_handle.write(json.dumps(event) + "\n")
        file_handle.flush()

    def close(self) -> None:
        """Close the output file."""
        if self._file is None:
            return
        self._file.close()
        self._file = None

    def _require_open_file(self) -> IO[str]:
        """Return the open file handle or raise if the writer is closed."""
        if self._file is None:
            msg = "Cannot write to a closed stream writer"
            raise RuntimeError(msg)
        return self._file
