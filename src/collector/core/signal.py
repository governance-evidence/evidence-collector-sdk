"""Raw signal abstraction for evidence collection.

A raw signal is the unprocessed input to the evidence pipeline --
a log entry, metric reading, system event, configuration change,
or human action that may become governance evidence once contextualized.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from types import MappingProxyType
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Mapping
    from datetime import datetime


class SignalType(Enum):
    """Classification of raw signal sources."""

    LOG = "log"
    METRIC = "metric"
    EVENT = "event"
    CONFIG_CHANGE = "config_change"
    HUMAN_ACTION = "human_action"


@dataclass(frozen=True)
class RawSignal:
    """Immutable raw signal awaiting transformation into evidence.

    Attributes
    ----------
    signal_id : str
        Unique identifier for this signal instance.
    signal_type : SignalType
        Classification of the signal source.
    payload : Mapping[str, object]
        Signal-specific data (scores, features, metrics, etc.).
    source : str
        Originating system or component name.
    timestamp : datetime
        When the signal was produced.
    metadata : Mapping[str, object]
        Arbitrary extra context attached at collection time.
    """

    signal_id: str
    signal_type: SignalType
    payload: Mapping[str, object]
    source: str
    timestamp: datetime
    metadata: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.signal_id:
            msg = "signal_id must be non-empty"
            raise ValueError(msg)
        if not self.source:
            msg = "source must be non-empty"
            raise ValueError(msg)
        if self.timestamp.tzinfo is None:
            msg = "timestamp must be timezone-aware (use datetime with tzinfo)"
            raise ValueError(msg)
        object.__setattr__(self, "payload", MappingProxyType(dict(self.payload)))
        object.__setattr__(self, "metadata", MappingProxyType(dict(self.metadata)))
