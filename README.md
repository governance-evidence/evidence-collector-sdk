# Evidence Collector SDK

[![CI](https://github.com/governance-evidence/evidence-collector-sdk/actions/workflows/ci.yml/badge.svg)](https://github.com/governance-evidence/evidence-collector-sdk/actions/workflows/ci.yml)
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.19245404.svg)](https://doi.org/10.5281/zenodo.19245404)
[![arXiv](https://img.shields.io/badge/arXiv-2604.17836-b31b1b.svg)](https://arxiv.org/abs/2604.17836)
[![License: Apache-2.0](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://github.com/governance-evidence/evidence-collector-sdk/blob/main/pyproject.toml)
[![pre-commit enabled](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=white)](https://pre-commit.com/)

Collect, contextualize, and structure raw system signals into governance-relevant
evidence units. Transforms operational telemetry into
[Decision Event Schema](https://github.com/governance-evidence/decision-event-schema)
events enriched with provenance, attribution, and temporal metadata.

## Academic Context

This SDK is a primary artifact of:

> Solozobov, O. (2026). *Label-Free Detection of Governance Evidence Degradation in Risk Decision Systems*.
> arXiv:2604.17836. <https://arxiv.org/abs/2604.17836>

The SDK provides the evidence-stream ingestion layer that feeds label-free governance monitoring
(see [governance-drift-toolkit](https://github.com/governance-evidence/governance-drift-toolkit)).
It operationalizes the evidence collection stage of the governance evidence chain introduced
across the paper series.

## Install

### From a Package Index

Use this when the package is published to your package index:

```bash
pip install evidence-collector-sdk
```

### From GitHub

Use this before package-index publication, or when installing directly from source control:

```bash
pip install git+https://github.com/governance-evidence/evidence-collector-sdk.git
```

Validation support is included in the base installation.

### For Contributors

Clone the repository, create a local virtual environment, and install development dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Quick start

```python
from datetime import UTC, datetime

from collector import EvidenceCollector, RawSignal, SignalType, fraud_detection_config

collector = EvidenceCollector(config=fraud_detection_config())

collector.add(RawSignal(
    signal_id="txn-001",
    signal_type=SignalType.EVENT,
    payload={"score": 0.87, "amount": 1500.0, "merchant_category": "electronics"},
    source="fraud-scoring-model-v3",
    timestamp=datetime.now(tz=UTC),
))

events = collector.flush()  # list of Decision Event Schema dicts
```

Validation state for the last collector operation is available via
`collector.validation_errors`.

### Single signal

```python
event = collector.collect_one(signal)  # transform + serialize + validation state update
```

### Validation strategy

```python
from collector import EvidenceCollector, ValidationMode

collector = EvidenceCollector(
    config=fraud_detection_config(),
    validation_mode=ValidationMode.PROVENANCE,
)
```

### Streaming (Governance Drift Toolkit compatible)

```python
from collector import EvidenceCollectorStream, OverflowStrategy

stream = EvidenceCollectorStream(
    fraud_detection_config(),
    max_buffer_size=10_000,
    overflow_strategy=OverflowStrategy.DROP_OLDEST,
)
stream.push(signal)
batch = stream.read_batch(batch_size=100)  # Decision Event Schema dicts for Governance Drift Toolkit
```

For a stable observability snapshot, use `stream.stats`.

```python
stats = stream.stats
# StreamStats(queued_count=..., in_flight_count=..., buffer_size=..., ...)
```

Scalar properties remain available via `queued_count`, `in_flight_count`,
`buffer_size`, `processed_count`, `failed_batch_count`, and `dropped_count`.

### Stream writer lifecycle

```python
from collector import JsonlStreamWriter

with JsonlStreamWriter(output_path) as writer:
    writer.write_batch(events)
```

### Validation

```python
from collector import validate_complete

errors = validate_complete(event, config=fraud_detection_config())
```

### Capabilities (Governance Drift Toolkit negotiation)

```python
caps = collector.capabilities
# StreamCapabilities(supported_signal_types=..., schema_version='0.3.0', ...)
```

## Development

```bash
make install    # install with dev deps
make check      # lint + typecheck + test
make format     # auto-fix formatting
```

## Related Projects

This SDK is part of the [governance-evidence](https://github.com/governance-evidence) toolkit:

| Repository | Role | DOI |
|------------|------|-----|
| [decision-event-schema](https://github.com/governance-evidence/decision-event-schema) | Schema that this SDK outputs events in | [10.5281/zenodo.18923177](https://doi.org/10.5281/zenodo.18923177) |
| [evidence-sufficiency-calc](https://github.com/governance-evidence/evidence-sufficiency-calc) | Scores the evidence events this SDK collects | [10.5281/zenodo.19233930](https://doi.org/10.5281/zenodo.19233930) |
| [governance-drift-toolkit](https://github.com/governance-evidence/governance-drift-toolkit) | Monitors drift using events from this SDK | [10.5281/zenodo.19236417](https://doi.org/10.5281/zenodo.19236417) |
| [governance-benchmark-dataset](https://github.com/governance-evidence/governance-benchmark-dataset) | Cross-architecture benchmark that scores event streams from this SDK | [10.5281/zenodo.19248722](https://doi.org/10.5281/zenodo.19248722) |

All DOIs above are **concept DOIs** -- each resolves to the latest Zenodo release of that artifact.

## Citation

If you use this SDK in your research, please cite both the paper and the software artifact.

**Paper (primary):**

```bibtex
@misc{solozobov2026labelfree,
  author = {Solozobov, Oleg},
  title  = {Label-Free Detection of Governance Evidence Degradation in Risk Decision Systems},
  year   = {2026},
  eprint = {2604.17836},
  archivePrefix = {arXiv},
  primaryClass  = {cs.CY},
  doi    = {10.48550/arXiv.2604.17836},
  url    = {https://arxiv.org/abs/2604.17836}
}
```

**Software (this repository):**

```bibtex
@software{solozobov2026evidencecollectorsdk,
  author  = {Solozobov, Oleg},
  title   = {Evidence Collector SDK},
  version = {0.2.0},
  year    = {2026},
  url     = {https://github.com/governance-evidence/evidence-collector-sdk},
  doi     = {10.5281/zenodo.19245404}
}
```

The software `doi` above is the **concept DOI** (always resolves to the latest Zenodo release).
The current v0.2.0 version DOI is [10.5281/zenodo.19478276](https://doi.org/10.5281/zenodo.19478276).

See [CITATION.cff](CITATION.cff) for machine-readable citation metadata.

## License

Apache-2.0
