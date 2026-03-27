"""Stream capability descriptor for Governance Drift Toolkit negotiation.

Allows Governance Drift Toolkit to discover what this Evidence Collector SDK instance supports
before consuming its evidence stream.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from collector.output.decision_event_writer import SCHEMA_VERSION

if TYPE_CHECKING:
    from collector.config import CollectionConfig
    from collector.core.signal import SignalType


@dataclass(frozen=True)
class StreamCapabilities:
    """Capability descriptor for Governance Drift Toolkit handshake.

    Attributes
    ----------
    supported_signal_types : frozenset[SignalType]
        Signal types this stream can produce evidence for.
    schema_version : str
        Decision Event Schema schema version emitted by the writer.
    max_batch_size : int
        Maximum recommended batch size for read_batch().
    sdk_version : str
        Evidence Collector SDK version.
    """

    supported_signal_types: frozenset[SignalType]
    schema_version: str
    max_batch_size: int
    sdk_version: str = "0.1.0"


def capabilities_from_config(
    config: CollectionConfig,
    *,
    max_batch_size: int = 1000,
) -> StreamCapabilities:
    """Build capabilities from a collection config.

    Parameters
    ----------
    config : CollectionConfig
        Collection configuration.
    max_batch_size : int
        Maximum recommended batch size.

    Returns
    -------
    StreamCapabilities
        Capability descriptor.
    """
    return StreamCapabilities(
        supported_signal_types=config.enabled_signal_types,
        schema_version=SCHEMA_VERSION,
        max_batch_size=max_batch_size,
    )
