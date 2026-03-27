"""Evidence stream reader implementing Governance Drift Toolkit's EvidenceStreamReader Protocol.

Provides a concrete class that satisfies the ``EvidenceStreamReader``
Protocol defined in ``governance-drift-toolkit/src/integrations/evidence_collector.py``.
Thread-safe with configurable backpressure.
"""

from __future__ import annotations

import logging
import threading
from collections import deque
from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collector.config import CollectionConfig
    from collector.core.signal import RawSignal

from collector.pipeline import TransformPipeline

logger = logging.getLogger(__name__)

#: Default maximum buffer size (0 = unlimited).
DEFAULT_MAX_BUFFER_SIZE = 0


class OverflowStrategy(StrEnum):
    """Backpressure behaviors supported by ``EvidenceCollectorStream``."""

    RAISE = "raise"
    DROP_OLDEST = "drop_oldest"


@dataclass(frozen=True)
class StreamStats:
    """Snapshot of current stream occupancy and processing counters."""

    queued_count: int
    in_flight_count: int
    buffer_size: int
    processed_count: int
    failed_batch_count: int
    dropped_count: int


class BufferOverflowError(Exception):
    """Raised when the stream buffer exceeds its capacity."""


class EvidenceCollectorStream:
    """Evidence stream that Governance Drift Toolkit can consume via EvidenceStreamReader Protocol.

    Thread-safe. Buffers raw signals and yields Decision Event Schema event batches on
    ``read_batch()``. Satisfies the Governance Drift Toolkit ``EvidenceStreamReader`` Protocol.

    Parameters
    ----------
    config : CollectionConfig
        Collection configuration.
    max_buffer_size : int
        Maximum number of signals to buffer. 0 = unlimited.
        When exceeded, behavior depends on ``overflow_strategy``.
    overflow_strategy : OverflowStrategy or str
        What to do when buffer is full: ``OverflowStrategy.RAISE``
        (default) or ``OverflowStrategy.DROP_OLDEST``.
    """

    def __init__(
        self,
        config: CollectionConfig,
        *,
        max_buffer_size: int = DEFAULT_MAX_BUFFER_SIZE,
        overflow_strategy: OverflowStrategy | str = OverflowStrategy.RAISE,
    ) -> None:
        self._pipeline = TransformPipeline(config)
        self._max_buffer_size = max_buffer_size
        self._overflow_strategy = self._resolve_overflow_strategy(overflow_strategy)
        self._buffer: deque[RawSignal] = (
            deque(maxlen=max_buffer_size) if max_buffer_size > 0 else deque()
        )
        self._in_flight_batches: dict[int, tuple[RawSignal, ...]] = {}
        self._in_flight_count = 0
        self._next_batch_id = 0
        self._lock = threading.Lock()
        self._closed = False
        self._dropped_count = 0
        self._processed_count = 0
        self._failed_batch_count = 0

    @property
    def closed(self) -> bool:
        """Return whether the stream has been closed."""
        return self._closed

    @property
    def buffer_size(self) -> int:
        """Return the current number of queued and in-flight signals."""
        with self._lock:
            return self._queued_count_locked() + self._in_flight_count

    @property
    def stats(self) -> StreamStats:
        """Return a consistent snapshot of stream occupancy and counters."""
        with self._lock:
            queued_count = self._queued_count_locked()
            in_flight_count = self._in_flight_count
            return StreamStats(
                queued_count=queued_count,
                in_flight_count=in_flight_count,
                buffer_size=queued_count + in_flight_count,
                processed_count=self._processed_count,
                failed_batch_count=self._failed_batch_count,
                dropped_count=self._dropped_count,
            )

    @property
    def queued_count(self) -> int:
        """Return the number of signals waiting in the queue."""
        with self._lock:
            return self._queued_count_locked()

    @property
    def in_flight_count(self) -> int:
        """Return the number of signals reserved by active batch reads."""
        with self._lock:
            return self._in_flight_count

    @property
    def dropped_count(self) -> int:
        """Return the total number of signals dropped due to overflow."""
        return self._dropped_count

    @property
    def processed_count(self) -> int:
        """Return the total number of signals successfully transformed."""
        with self._lock:
            return self._processed_count

    @property
    def failed_batch_count(self) -> int:
        """Return the number of batch reads that failed during processing."""
        with self._lock:
            return self._failed_batch_count

    @property
    def overflow_strategy(self) -> OverflowStrategy:
        """Return the configured overflow behavior."""
        return self._overflow_strategy

    def push(self, signal: RawSignal) -> None:
        """Add a signal to the internal buffer (thread-safe).

        Parameters
        ----------
        signal : RawSignal
            Signal to buffer for the next ``read_batch`` call.

        Raises
        ------
        RuntimeError
            If the stream has been closed.
        BufferOverflowError
            If buffer is full and overflow_strategy is "raise".
        """
        with self._lock:
            self._push_locked(signal)

    def push_many(self, signals: list[RawSignal]) -> None:
        """Add multiple signals to the internal buffer (thread-safe).

        Parameters
        ----------
        signals : list of RawSignal
            Signals to buffer.

        Raises
        ------
        RuntimeError
            If the stream has been closed.
        BufferOverflowError
            If buffer would overflow and overflow_strategy is "raise".
        """
        with self._lock:
            for signal in signals:
                self._push_locked(signal)

    def read_batch(self, *, batch_size: int = 100) -> list[dict[str, Any]]:
        """Read a batch of Decision Event Schema events from buffered signals (thread-safe).

        Drains up to ``batch_size`` signals from the buffer, transforms
        them, and returns Decision Event Schema dicts.

        Parameters
        ----------
        batch_size : int
            Maximum events to return per call.

        Returns
        -------
        list of dict
            Batch of decision event (Decision Event Schema) dicts.
        """
        with self._lock:
            count = min(batch_size, len(self._buffer))
            batch = [self._buffer.popleft() for _ in range(count)]
            if not batch:
                return []
            batch_id = self._reserve_in_flight_locked(batch)
        # Transform outside the lock to avoid holding it during computation
        try:
            events = self._pipeline.process_to_decision_event(batch)
        except Exception:
            with self._lock:
                self._failed_batch_count += 1
                self._restore_in_flight_locked(batch_id)
            raise
        with self._lock:
            self._complete_in_flight_locked(batch_id)
            self._processed_count += len(batch)
        return events

    def close(self) -> None:
        """Close the stream and discard remaining buffer (thread-safe)."""
        with self._lock:
            self._buffer.clear()
            self._closed = True

    def _push_locked(self, signal: RawSignal) -> None:
        """Push a signal while holding the lock.

        Parameters
        ----------
        signal : RawSignal
            Signal to buffer.
        """
        if self._closed:
            msg = "Cannot push to a closed stream"
            raise RuntimeError(msg)
        total_occupancy = len(self._buffer) + self._in_flight_count
        if self._max_buffer_size > 0 and total_occupancy >= self._max_buffer_size:
            if self._overflow_strategy is OverflowStrategy.RAISE:
                msg = (
                    f"Buffer full ({self._max_buffer_size} signals). "
                    f"Increase max_buffer_size or consume faster."
                )
                raise BufferOverflowError(msg)
            if not self._drop_oldest_locked():
                return
        self._buffer.append(signal)

    def _drop_oldest_locked(self) -> bool:
        """Drop one signal according to overflow policy while holding the lock."""
        if self._buffer:
            self._dropped_count += 1
            self._buffer.popleft()
            logger.warning(
                "Buffer overflow: dropping oldest queued signal (total dropped: %d)",
                self._dropped_count,
            )
            return True
        self._dropped_count += 1
        logger.warning(
            "Buffer overflow: dropping incoming signal while %d signals are in flight "
            "(total dropped: %d)",
            self._in_flight_count,
            self._dropped_count,
        )
        return False

    def _queued_count_locked(self) -> int:
        """Return queued signal count while holding the lock."""
        return len(self._buffer)

    def _resolve_overflow_strategy(
        self,
        overflow_strategy: OverflowStrategy | str,
    ) -> OverflowStrategy:
        """Validate and normalize the configured overflow strategy."""
        try:
            return OverflowStrategy(overflow_strategy)
        except ValueError as exc:
            msg = f"overflow_strategy must be one of {[mode.value for mode in OverflowStrategy]}"
            raise ValueError(msg) from exc

    def _reserve_in_flight_locked(self, batch: list[RawSignal]) -> int:
        """Record a batch as in flight while holding the lock."""
        batch_id = self._next_batch_id
        self._next_batch_id += 1
        self._in_flight_batches[batch_id] = tuple(batch)
        self._in_flight_count += len(batch)
        return batch_id

    def _complete_in_flight_locked(self, batch_id: int) -> None:
        """Mark an in-flight batch as processed while holding the lock."""
        batch = self._in_flight_batches.pop(batch_id, ())
        self._in_flight_count -= len(batch)

    def _restore_in_flight_locked(self, batch_id: int) -> None:
        """Restore a failed in-flight batch to the head of the queue."""
        batch = self._in_flight_batches.pop(batch_id, ())
        self._in_flight_count -= len(batch)
        if not self._closed:
            self._buffer.extendleft(reversed(batch))
