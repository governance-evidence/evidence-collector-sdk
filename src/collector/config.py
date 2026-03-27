"""Collection configuration for evidence pipelines.

Defines what signals to collect, how to contextualize them,
signal quality heuristics, Decision Event Schema mapping rules, and governance-specific
parameters for different operational domains.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import TYPE_CHECKING

from collector.core.signal import SignalType

if TYPE_CHECKING:
    from collections.abc import Mapping


@dataclass(frozen=True)
class SignalQualityDefaults:
    """Per-signal-type quality heuristics.

    Centralizes the quality scores and gap penalties that transforms
    apply when assessing signal confidence.

    Attributes
    ----------
    base_quality : float
        Default signal quality when data is complete.
    missing_key_quality : float
        Degraded quality when an expected key is absent.
    gap_penalty_per_gap : float
        Confidence penalty per known observation gap.
    """

    base_quality: float = 1.0
    missing_key_quality: float = 0.7
    gap_penalty_per_gap: float = 0.05

    def __post_init__(self) -> None:
        for name, val in [
            ("base_quality", self.base_quality),
            ("missing_key_quality", self.missing_key_quality),
        ]:
            if not math.isfinite(val) or not 0.0 <= val <= 1.0:
                msg = f"{name} must be in [0, 1], got {val}"
                raise ValueError(msg)
        if not math.isfinite(self.gap_penalty_per_gap) or self.gap_penalty_per_gap < 0:
            msg = f"gap_penalty_per_gap must be non-negative, got {self.gap_penalty_per_gap}"
            raise ValueError(msg)


#: Default quality settings per signal type.
_DEFAULT_QUALITY: dict[SignalType, SignalQualityDefaults] = {
    SignalType.LOG: SignalQualityDefaults(base_quality=1.0, missing_key_quality=0.7),
    SignalType.METRIC: SignalQualityDefaults(base_quality=1.0, missing_key_quality=0.8),
    SignalType.EVENT: SignalQualityDefaults(base_quality=1.0, missing_key_quality=0.8),
    SignalType.CONFIG_CHANGE: SignalQualityDefaults(base_quality=1.0, missing_key_quality=1.0),
    SignalType.HUMAN_ACTION: SignalQualityDefaults(base_quality=0.9, missing_key_quality=0.7),
}


@dataclass(frozen=True)
class DecisionEventMappingConfig:
    """Configuration for Decision Event Schema serialization field mapping.

    Attributes
    ----------
    logic_parameter_keys : tuple[str, ...]
        Payload keys mapped to ``decision_logic.parameters``.
    logic_threshold_keys : tuple[str, ...]
        Payload keys mapped to ``decision_logic.thresholds``.
    include_metadata : bool
        Whether to include signal metadata in Decision Event Schema output.
    """

    logic_parameter_keys: tuple[str, ...] = (
        "model_version",
        "model_name",
        "algorithm",
        "model_id",
        "pipeline_version",
    )
    logic_threshold_keys: tuple[str, ...] = (
        "old_threshold",
        "new_threshold",
        "threshold",
    )
    include_metadata: bool = True


@dataclass(frozen=True)
class CollectionConfig:
    """Configuration for an evidence collection pipeline.

    Attributes
    ----------
    name : str
        Human-readable name for this collection configuration.
    enabled_signal_types : frozenset[SignalType]
        Which signal types this configuration collects.
    default_actor_type : str
        Default actor type when attribution cannot be determined.
    default_source : str
        Default source label for signals missing source information.
    score_key : str
        Key within signal payload containing the prediction score.
    feature_keys : tuple[str, ...]
        Keys within signal payload containing features for Governance Drift Toolkit monitoring.
    quality : Mapping[SignalType, SignalQualityDefaults]
        Per-signal-type quality heuristics.
    decision_event_mapping : DecisionEventMappingConfig
        Decision Event Schema serialization field mapping rules.
    extra : Mapping[str, object]
        Domain-specific extra configuration.
    """

    name: str
    enabled_signal_types: frozenset[SignalType] = field(
        default_factory=lambda: frozenset(SignalType)
    )
    default_actor_type: str = "system"
    default_source: str = "unknown"
    score_key: str = "score"
    feature_keys: tuple[str, ...] = ()
    quality: Mapping[SignalType, SignalQualityDefaults] = field(
        default_factory=lambda: dict(_DEFAULT_QUALITY)
    )
    decision_event_mapping: DecisionEventMappingConfig = field(
        default_factory=DecisionEventMappingConfig
    )
    extra: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.name:
            msg = "name must be non-empty"
            raise ValueError(msg)
        object.__setattr__(self, "extra", MappingProxyType(dict(self.extra)))
        object.__setattr__(self, "quality", MappingProxyType(dict(self.quality)))

    def quality_for(self, signal_type: SignalType) -> SignalQualityDefaults:
        """Return quality heuristics for a signal type.

        Parameters
        ----------
        signal_type : SignalType
            Signal type to look up.

        Returns
        -------
        SignalQualityDefaults
            Quality heuristics (falls back to defaults if not configured).
        """
        return self.quality.get(signal_type, SignalQualityDefaults())


def fraud_detection_config() -> CollectionConfig:
    """Return a configuration tuned for fraud detection pipelines.

    Returns
    -------
    CollectionConfig
        Fraud-detection-specific collection configuration.
    """
    return CollectionConfig(
        name="fraud_detection",
        enabled_signal_types=frozenset(SignalType),
        default_actor_type="system",
        default_source="fraud-pipeline",
        score_key="score",
        feature_keys=("amount", "merchant_category"),
    )


def credit_scoring_config() -> CollectionConfig:
    """Return a configuration tuned for credit scoring pipelines.

    Returns
    -------
    CollectionConfig
        Credit-scoring-specific collection configuration.
    """
    return CollectionConfig(
        name="credit_scoring",
        enabled_signal_types=frozenset({SignalType.EVENT, SignalType.METRIC}),
        default_actor_type="system",
        default_source="credit-pipeline",
        score_key="score",
        feature_keys=("income", "debt_ratio", "credit_history_months"),
    )
