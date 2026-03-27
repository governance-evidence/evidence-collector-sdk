"""Decision Event Schema schema validation for evidence output.

Validates serialized evidence units against the Decision Event Schema
using optional ``jsonschema`` dependency, plus semantic validators
for provenance integrity and feature key conformance.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collector.config import CollectionConfig


def validate_decision_event(
    event: dict[str, Any],
    *,
    schema_path: str | Path | None = None,
) -> list[str]:
    """Validate a Decision Event Schema event dict against the Decision Event Schema.

    Parameters
    ----------
    event : dict
        decision event (Decision Event Schema) dict (from ``to_decision_event``).
    schema_path : str, Path, or None
        Path to ``decision-event.schema.json``. If None, uses a
        bundled minimal schema covering required fields.

    Returns
    -------
    list of str
        Validation error messages (empty if valid).

    Raises
    ------
    ImportError
        If ``jsonschema`` is not installed.
    """
    try:
        import jsonschema
    except ImportError:  # pragma: no cover
        msg = (
            "jsonschema is required for Decision Event Schema validation. "
            "Reinstall evidence-collector-sdk or install jsonschema>=4.20."
        )
        raise ImportError(msg)  # noqa: B904

    if schema_path is not None:
        with Path(schema_path).open() as f:
            schema = json.load(f)
    else:
        schema = _MINIMAL_SCHEMA

    validator = jsonschema.Draft202012Validator(
        schema,
        format_checker=jsonschema.Draft202012Validator.FORMAT_CHECKER,
    )
    errors = [err.message for err in validator.iter_errors(event)]
    errors.extend(_validate_timestamp_format(event))
    return errors


def _validate_timestamp_format(event: dict[str, Any]) -> list[str]:
    """Validate the top-level Decision Event Schema timestamp string.

    Parameters
    ----------
    event : dict
        decision event (Decision Event Schema) dict.

    Returns
    -------
    list of str
        Timestamp validation errors.
    """
    timestamp = event.get("timestamp")
    if not isinstance(timestamp, str):
        return []
    try:
        parsed = datetime.fromisoformat(timestamp)
    except ValueError:
        return ["timestamp must be a valid ISO 8601 date-time string"]
    if parsed.tzinfo is None:
        return ["timestamp must include timezone information"]
    return []


def validate_provenance(event: dict[str, Any]) -> list[str]:
    """Validate provenance chain integrity in a Decision Event Schema event.

    Checks that consecutive provenance steps have matching
    output_hash -> input_hash linkage.

    Parameters
    ----------
    event : dict
        decision event (Decision Event Schema) dict.

    Returns
    -------
    list of str
        Validation error messages (empty if valid).
    """
    prov = event.get("_provenance")
    if prov is None:
        return ["Missing _provenance field"]
    steps = prov.get("steps", [])
    errors: list[str] = []
    for i in range(1, len(steps)):
        prev_out = steps[i - 1].get("output_hash", "")
        curr_in = steps[i].get("input_hash", "")
        if prev_out != curr_in:
            errors.append(
                f"Broken provenance chain at step {i}: "
                f"expected input_hash={prev_out!r}, got {curr_in!r}"
            )
    return errors


def validate_features(
    event: dict[str, Any],
    *,
    config: CollectionConfig,
    skip_non_prediction: bool = True,
) -> list[str]:
    """Validate that expected feature keys are present in the event.

    Parameters
    ----------
    event : dict
        decision event (Decision Event Schema) dict.
    config : CollectionConfig
        Collection configuration defining expected feature keys.
    skip_non_prediction : bool
        If True (default), skip feature validation for non-prediction
        signals (human actions, config changes) that are not expected
        to carry prediction features.

    Returns
    -------
    list of str
        Validation error messages (empty if valid).
    """
    if skip_non_prediction:
        ctx = event.get("decision_context", {})
        signal_type = ctx.get("signal_type", "")
        if signal_type in ("human_action", "config_change"):
            return []
    errors = [
        f"Missing feature key {key!r} in event" for key in config.feature_keys if key not in event
    ]
    if config.score_key not in event:
        errors.append(f"Missing score key {config.score_key!r} in event")
    return errors


def validate_complete(
    event: dict[str, Any],
    *,
    config: CollectionConfig | None = None,
    schema_path: str | Path | None = None,
) -> list[str]:
    """Run all validators: schema + provenance + features.

    Parameters
    ----------
    event : dict
        decision event (Decision Event Schema) dict.
    config : CollectionConfig or None
        If provided, also validates feature key conformance.
    schema_path : str, Path, or None
        Path to JSON Schema file.

    Returns
    -------
    list of str
        All validation errors combined.
    """
    errors = validate_decision_event(event, schema_path=schema_path)
    errors.extend(validate_provenance(event))
    if config is not None:
        errors.extend(validate_features(event, config=config))
    return errors


#: Minimal Decision Event Schema schema covering required fields.
_MINIMAL_SCHEMA: dict[str, Any] = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "required": ["decision_id", "timestamp", "decision_type"],
    "properties": {
        "schema_version": {"type": "string"},
        "decision_id": {"type": "string"},
        "timestamp": {"type": "string", "format": "date-time"},
        "decision_type": {
            "type": "string",
            "enum": ["human", "automated", "hybrid"],
        },
    },
}
