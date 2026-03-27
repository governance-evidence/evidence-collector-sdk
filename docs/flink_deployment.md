# Flink Integration Guide

## Overview

Evidence Collector SDK is designed to be deployed as a Flink operator inside production
data pipelines. The `integrations/flink/` module provides Protocol
interfaces for Flink integration.

## Architecture

```text
Flink Source (FlinkSourceReader)
    |
    v
Evidence Transform (FlinkEvidenceOperator)
    |
    v
Flink Sink (FlinkEvidenceSink)
    |
    v
Governance Drift Toolkit Governance Monitoring
```

## Protocol Interfaces

### FlinkSourceReader

Reads raw signal batches from a Flink data stream.

### FlinkEvidenceOperator

Processes individual stream elements and optionally emits Decision Event Schema events.
Returns `None` for elements that should be filtered out.

### FlinkEvidenceSink

Writes Decision Event Schema events to an output that Governance Drift Toolkit can consume.

## Performance Target

Evidence Collector SDK must add < 5ms per evidence unit at p99 in the production
Flink pipeline. No network calls in the hot path.

## Implementation Notes

The current release provides Protocol stubs only. Concrete Flink
implementations depend on the Apache Flink Python API (pyflink),
which is an optional dependency not included in the base package.
