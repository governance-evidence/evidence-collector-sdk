"""Transform pipeline orchestrating signal-to-evidence conversion.

Routes signals to the appropriate transform based on signal type,
and provides batch processing with Decision Event Schema serialization.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from collector.core.signal import SignalType
from collector.output.decision_event_writer import to_decision_event
from collector.transforms.action_to_evidence import transform_action
from collector.transforms.config_to_evidence import transform_config
from collector.transforms.event_to_evidence import transform_event
from collector.transforms.log_to_evidence import transform_log
from collector.transforms.metric_to_evidence import transform_metric

if TYPE_CHECKING:
    from collector.config import CollectionConfig
    from collector.core.evidence_unit import EvidenceUnit
    from collector.core.signal import RawSignal
    from collector.transforms.base import SignalTransform

#: Default routing from signal type to transform function.
_DEFAULT_ROUTES: dict[SignalType, SignalTransform] = {
    SignalType.LOG: transform_log,
    SignalType.METRIC: transform_metric,
    SignalType.EVENT: transform_event,
    SignalType.CONFIG_CHANGE: transform_config,
    SignalType.HUMAN_ACTION: transform_action,
}


class TransformPipeline:
    """Orchestrate signal-to-evidence conversion with type-based routing.

    Parameters
    ----------
    config : CollectionConfig
        Collection configuration applied to all transforms.
    routes : dict or None
        Custom routing overrides. Defaults to built-in routes for
        all five signal types.
    """

    def __init__(
        self,
        config: CollectionConfig,
        routes: dict[SignalType, SignalTransform] | None = None,
    ) -> None:
        self._config = config
        self._routes: dict[SignalType, SignalTransform] = dict(
            routes if routes is not None else _DEFAULT_ROUTES
        )

    @property
    def config(self) -> CollectionConfig:
        """Return the pipeline configuration."""
        return self._config

    def transform(self, signal: RawSignal) -> EvidenceUnit:
        """Transform a single signal into an evidence unit.

        Parameters
        ----------
        signal : RawSignal
            Input signal.

        Returns
        -------
        EvidenceUnit
            Transformed evidence unit.

        Raises
        ------
        ValueError
            If signal type is not in enabled types or has no route.
        """
        if signal.signal_type not in self._config.enabled_signal_types:
            msg = (
                f"Signal type {signal.signal_type.value} not enabled "
                f"in config {self._config.name!r}"
            )
            raise ValueError(msg)
        route = self._routes.get(signal.signal_type)
        if route is None:
            msg = f"No transform route for signal type {signal.signal_type.value}"
            raise ValueError(msg)
        return route(signal, config=self._config)

    def transform_batch(self, signals: list[RawSignal]) -> list[EvidenceUnit]:
        """Transform a batch of signals into evidence units.

        Skips signals whose type is not enabled (does not raise).

        Parameters
        ----------
        signals : list of RawSignal
            Input signals.

        Returns
        -------
        list of EvidenceUnit
            Transformed evidence units (may be shorter than input).
        """
        units: list[EvidenceUnit] = []
        for signal in signals:
            if signal.signal_type not in self._config.enabled_signal_types:
                continue
            route = self._routes.get(signal.signal_type)
            if route is None:
                continue
            units.append(route(signal, config=self._config))
        return units

    def process_to_decision_event(self, signals: list[RawSignal]) -> list[dict[str, Any]]:
        """Transform signals and serialize to Decision Event Schema format in one step.

        Parameters
        ----------
        signals : list of RawSignal
            Input signals.

        Returns
        -------
        list of dict
            Decision Event Schema-compatible decision event dicts.
        """
        units = self.transform_batch(signals)
        mapping = self._config.decision_event_mapping
        return [to_decision_event(u, mapping=mapping) for u in units]
