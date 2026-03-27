# Signal-to-Evidence Transforms

## Transform Protocol

All transforms implement the `SignalTransform` Protocol:

```python
def __call__(self, signal: RawSignal, *, config: CollectionConfig) -> EvidenceUnit
```

## Signal Quality Model

Each signal type has configurable quality heuristics via `SignalQualityDefaults`:

| Signal Type | base_quality | missing_key_quality | Notes |
|---|---|---|---|
| LOG | 1.0 | 0.7 | Degraded when score key absent |
| METRIC | 1.0 | 0.8 | High-quality structured data |
| EVENT | 1.0 | 0.8 | Full payload expected |
| CONFIG_CHANGE | 1.0 | 1.0 | Score absence expected (policy, not prediction) |
| HUMAN_ACTION | 0.9 | 0.7 | Inherent subjectivity; degraded without rationale |

These defaults are configured in `CollectionConfig.quality` and accessed via
`config.quality_for(signal_type)`. Override per domain:

```python
CollectionConfig(
    name="my_domain",
    quality={
        SignalType.LOG: SignalQualityDefaults(base_quality=0.8, missing_key_quality=0.5),
        ...
    },
)
```

## Available Transforms

### event_to_evidence

Discrete system events (transaction scored, alert raised). Uses `base_quality`.

### log_to_evidence

Log entries. Uses `missing_key_quality` + `missing_score_key` gap when score absent.

### metric_to_evidence

Metric readings. Uses `base_quality`.

### config_to_evidence

Configuration changes (threshold updates, model swaps). Records
`no_prediction_score` gap when score key absent (expected for config signals).

### action_to_evidence

Human actions (reviews, overrides, escalations). Sets `actor_type="human"`.
Uses `missing_key_quality` + `missing_override_rationale` gap when rationale absent.

## Pipeline Orchestration

`TransformPipeline` routes signals to transforms by type:

```python
pipe = TransformPipeline(config)
units = pipe.transform_batch(signals)     # skips disabled types
events = pipe.process_to_decision_event(signals)    # transform + serialize
```

`EvidenceCollector` wraps the pipeline with validation:

```python
collector = EvidenceCollector(config)
collector.add_many(signals)
events = collector.flush()  # transform + serialize + validate provenance
```

## Shared Builder

All transforms use `build_evidence_unit()` which handles:

1. Computing content hashes for provenance
2. Creating ProvenanceChain with single transform step
3. Building Attribution (with configurable actor_type, role, delegation chain)
4. Computing ConfidenceScore from config-driven quality heuristics
5. Enriching context (system state, org context, dependencies)
6. Calculating temporal grounding (processing lag)
