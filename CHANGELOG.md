# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] - 2026-04-09

Zenodo release: [10.5281/zenodo.19478276](https://doi.org/10.5281/zenodo.19478276).

Detailed change notes pending; see GitHub release notes for the interim summary.

## [0.1.1] - 2026-03-28

Zenodo release: [10.5281/zenodo.19270691](https://doi.org/10.5281/zenodo.19270691).

Detailed change notes pending; see GitHub release notes for the interim summary.

## [0.1.0] - 2026-03-27

Initial public release. Zenodo: [10.5281/zenodo.19245405](https://doi.org/10.5281/zenodo.19245405).

### Added

- Core domain models: `RawSignal`, `SignalType`, `EvidenceUnit`, `TemporalGrounding`
- Attribution tracking: `Attribution` with actor type, delegation chain, responsibility boundary
- Confidence scoring: `ConfidenceScore` with signal quality and collection completeness components
- Provenance chains: `ProvenanceChain` with SHA-256 hash verification and integrity checks
- Context enrichment: system state, organizational context, dependency relations
- Five signal transforms: LOG, METRIC, EVENT, CONFIG_CHANGE, HUMAN_ACTION
- `TransformPipeline` with configurable routing and Decision Event Schema serialization
- `EvidenceCollector` for batch evidence collection with validation
- `EvidenceCollectorStream` for thread-safe streaming with backpressure (RAISE/DROP_OLDEST)
- `JsonlStreamWriter` for JSONL file output
- Decision Event Schema schema-compliant serialization via `to_decision_event()` with configurable field mapping
- Validation suite: `validate_decision_event`, `validate_provenance`, `validate_features`, `validate_complete`
- `StreamCapabilities` for Governance Drift Toolkit protocol negotiation
- Domain-specific config factories: `fraud_detection_config()`, `credit_scoring_config()`
- Flink integration protocol stubs (source, transform, sink)
- Strict type safety: mypy strict mode, py.typed marker (PEP 561)
- 100% test coverage with branch coverage (174 tests)
- Property-based testing via Hypothesis
- Pre-commit hooks (19 checks) with pre-push coverage enforcement
