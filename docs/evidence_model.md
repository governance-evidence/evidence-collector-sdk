# Evidence Unit Model

## Overview

An evidence unit is a raw system signal enriched with contextualization,
attribution, provenance, and temporal metadata. It is the atomic output
of the evidence collection (Evidence Collector SDK) pipeline.

## Evidence != Telemetry

| Property | Telemetry | Evidence |
|---|---|---|
| Purpose | Operational monitoring | Governance assessment |
| Context | Minimal | System state, org role, dependencies |
| Attribution | Source label | Actor, delegation chain, responsibility |
| Provenance | None | Full transformation chain with hashes |
| Confidence | Implicit | Explicit score with known gaps |

## Data Model

### RawSignal

Input to the pipeline. Five types: LOG, METRIC, EVENT, CONFIG_CHANGE, HUMAN_ACTION.
Timestamps must be timezone-aware (naive datetimes rejected).

### EvidenceUnit

Output of the pipeline. Contains:

- `unit_id` -- unique identifier
- `signal` -- the original RawSignal
- `provenance` -- ProvenanceChain with hash-linked steps
- `attribution` -- actor identification and delegation chain
- `confidence` -- quality score with explicit known gaps
- `context_enrichment` -- system state, org context, dependencies
- `temporal_grounding` -- collection vs event timestamp, processing lag

### Decision Event Schema Serialization

`to_decision_event(unit)` produces a dict conforming to the Decision Event Schema:

- `schema_version` -- Decision Event Schema version (currently "0.3.0")
- Required canonical blocks: `decision_context`, `decision_logic`, `human_override_record`, `temporal_metadata`
- Legacy aliases retained for compatibility: `decision_id`, `timestamp`, `decision_type`
- Payload fields (score, features) at top level for Governance Drift Toolkit compatibility
- `decision_context` -- includes canonical `decision_id` and domain `decision_type`, plus available inputs
- `decision_logic` -- includes canonical `logic_type` and `output`, plus rule_version/thresholds/parameters
- `decision_quality_indicators` -- confidence_score, signal_quality, collection_completeness, gaps
- `temporal_metadata` -- canonical event timestamp, hash chain, evidence tier, plus compatibility aliases
- `human_override_record` -- always present; human decisions include actor/rationale attribution
- Extension fields: `_provenance`, `_attribution`, `_signal_metadata`

### Signal Quality Configuration

Quality heuristics are centralized in `SignalQualityDefaults`, configured per signal type:

```python
SignalQualityDefaults(
    base_quality=1.0,          # quality when data is complete
    missing_key_quality=0.7,   # quality when expected key absent
    gap_penalty_per_gap=0.05,  # confidence penalty per known gap
)
```

Access via `config.quality_for(signal_type)`.

## Usage

### High-level (recommended)

```python
from collector import EvidenceCollector, fraud_detection_config

collector = EvidenceCollector(config=fraud_detection_config())
collector.add(signal)
events = collector.flush()  # Decision Event Schema dicts with provenance validation
```

### Low-level

```python
from collector import TransformPipeline, to_decision_event

pipe = TransformPipeline(config)
unit = pipe.transform(signal)
event = to_decision_event(unit)
```

### Streaming

For continuous collection with backpressure, see [streaming.md](streaming.md).

```python
from collector import EvidenceCollectorStream, fraud_detection_config

stream = EvidenceCollectorStream(fraud_detection_config(), max_buffer_size=1000)
stream.push(signal)
events = stream.read_batch(batch_size=100)
stream.close()
```

### Validation

```python
from collector import validate_complete

errors = validate_complete(event, config=config)
# checks Decision Event Schema schema, provenance integrity, and feature completeness
```
