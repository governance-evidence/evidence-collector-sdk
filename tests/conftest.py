"""Shared test fixtures and factories for the evidence-collector-sdk test suite."""

from __future__ import annotations

from datetime import UTC, datetime

from collector.core.signal import RawSignal, SignalType


def make_signal(
    *,
    signal_id: str = "sig-001",
    signal_type: SignalType = SignalType.EVENT,
    payload: dict | None = None,
    source: str = "test-system",
    timestamp: datetime | None = None,
) -> RawSignal:
    """Create a ``RawSignal`` with sensible test defaults.

    Parameters
    ----------
    signal_id
        Unique signal identifier.
    signal_type
        Type of signal (default: EVENT).
    payload
        Signal payload dict. Defaults to ``{"score": 0.9, "amount": 100.0}``.
    source
        Originating system name.
    timestamp
        Timezone-aware timestamp. Defaults to 2026-01-01T00:00:00 UTC.

    """
    return RawSignal(
        signal_id=signal_id,
        signal_type=signal_type,
        payload=payload if payload is not None else {"score": 0.9, "amount": 100.0},
        source=source,
        timestamp=timestamp or datetime(2026, 1, 1, tzinfo=UTC),
    )
