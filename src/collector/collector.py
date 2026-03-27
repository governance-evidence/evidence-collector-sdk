"""High-level orchestrator for evidence collection.

Provides a single entry point that handles the full pipeline:
signal ingestion, transformation, serialization, and optional validation.
"""

from __future__ import annotations

from enum import StrEnum
from typing import TYPE_CHECKING, Any

from collector.capabilities import StreamCapabilities, capabilities_from_config
from collector.output.decision_event_writer import to_decision_event
from collector.pipeline import TransformPipeline
from collector.validation import validate_provenance

if TYPE_CHECKING:
    from collector.config import CollectionConfig
    from collector.core.evidence_unit import EvidenceUnit
    from collector.core.signal import RawSignal


class ValidationMode(StrEnum):
    """Validation strategies supported by the high-level collector API."""

    NONE = "none"
    PROVENANCE = "provenance"


class EvidenceCollector:
    """High-level entry point for evidence collection.

    Wraps pipeline, serialization, and validation into a single API.

    .. warning::

        This class is **not** thread-safe. For concurrent access from
        multiple threads, use :class:`~collector.stream.EvidenceCollectorStream`
        instead.

    Parameters
    ----------
    config : CollectionConfig
        Collection configuration.
    validate : bool or None
        Backward-compatible shortcut for setting ``validation_mode``.
        If provided, ``False`` maps to ``ValidationMode.NONE`` and ``True``
        maps to ``ValidationMode.PROVENANCE``.
    validation_mode : ValidationMode or str
        Validation strategy for produced events. Defaults to provenance-only
        validation.

    Examples
    --------
    >>> collector = EvidenceCollector(config=fraud_detection_config())
    >>> collector.add(signal)
    >>> events = collector.flush()  # Decision Event Schema dicts
    """

    def __init__(
        self,
        config: CollectionConfig,
        *,
        validate: bool | None = None,
        validation_mode: ValidationMode | str | None = None,
    ) -> None:
        self._config = config
        self._pipeline = TransformPipeline(config)
        self._validation_mode = self._resolve_validation_mode(
            validate=validate,
            validation_mode=validation_mode,
        )
        self._buffer: list[RawSignal] = []
        self._validation_errors: list[str] = []

    @property
    def config(self) -> CollectionConfig:
        """Return the collection configuration."""
        return self._config

    @property
    def capabilities(self) -> StreamCapabilities:
        """Return stream capabilities for Governance Drift Toolkit negotiation."""
        return capabilities_from_config(self._config)

    @property
    def pending_count(self) -> int:
        """Return number of signals awaiting processing."""
        return len(self._buffer)

    @property
    def validation_errors(self) -> list[str]:
        """Return validation errors from the last flush."""
        return list(self._validation_errors)

    @property
    def validation_mode(self) -> ValidationMode:
        """Return the configured validation strategy."""
        return self._validation_mode

    def add(self, signal: RawSignal) -> None:
        """Add a signal to the processing buffer.

        Parameters
        ----------
        signal : RawSignal
            Signal to collect.
        """
        self._buffer.append(signal)

    def add_many(self, signals: list[RawSignal]) -> None:
        """Add multiple signals to the processing buffer.

        Parameters
        ----------
        signals : list of RawSignal
            Signals to collect.
        """
        self._buffer.extend(signals)

    def transform(self) -> list[EvidenceUnit]:
        """Transform buffered signals into evidence units, draining the buffer.

        Returns
        -------
        list of EvidenceUnit
            Evidence units.
        """
        signals = list(self._buffer)
        units = self._pipeline.transform_batch(signals)
        self._buffer = self._buffer[len(signals) :]
        return units

    def flush(self) -> list[dict[str, Any]]:
        """Transform, serialize, and optionally validate. Drains the buffer.

        Returns
        -------
        list of dict
            Decision Event Schema-compatible decision event dicts.
        """
        units = self.transform()
        mapping = self._config.decision_event_mapping
        events = [to_decision_event(u, mapping=mapping) for u in units]
        self._update_validation_errors(events)
        return events

    def collect_one(self, signal: RawSignal) -> dict[str, Any]:
        """Transform and serialize a single signal in one call.

        Parameters
        ----------
        signal : RawSignal
            Signal to process.

        Returns
        -------
        dict
            Decision Event Schema-compatible decision event.
        """
        unit = self._pipeline.transform(signal)
        event = to_decision_event(unit, mapping=self._config.decision_event_mapping)
        self._update_validation_errors([event])
        return event

    def _update_validation_errors(self, events: list[dict[str, Any]]) -> None:
        """Update validation state for the most recent collector operation."""
        self._validation_errors.clear()
        if self._validation_mode is ValidationMode.NONE:
            return
        for event in events:
            errs = validate_provenance(event)
            self._validation_errors.extend(errs)

    def _resolve_validation_mode(
        self,
        *,
        validate: bool | None,
        validation_mode: ValidationMode | str | None,
    ) -> ValidationMode:
        """Resolve the effective validation mode for this collector."""
        if validation_mode is None:
            resolved_mode = ValidationMode.PROVENANCE
            mode_was_explicit = False
        else:
            mode_was_explicit = True
            try:
                resolved_mode = ValidationMode(validation_mode)
            except ValueError as exc:
                msg = f"validation_mode must be one of {[mode.value for mode in ValidationMode]}"
                raise ValueError(msg) from exc

        if validate is None:
            return resolved_mode

        validate_mode = ValidationMode.PROVENANCE if validate else ValidationMode.NONE
        if mode_was_explicit and resolved_mode is not validate_mode:
            msg = "validation_mode conflicts with validate"
            raise ValueError(msg)
        return validate_mode
