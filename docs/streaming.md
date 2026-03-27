# Streaming API

The Evidence Collector SDK provides a thread-safe streaming interface for
continuous evidence collection via `EvidenceCollectorStream`.

## Buffer lifecycle

```text
push(signal) -> [buffer queue] -> read_batch() -> [transform pipeline] -> Decision Event Schema events
```

1. **Push**: `push(signal)` or `push_many(signals)` adds raw signals to an
   internal buffer (thread-safe via `threading.Lock`).
2. **Read batch**: `read_batch(batch_size=N)` dequeues up to N signals, runs
   them through the `TransformPipeline`, serializes to Decision Event Schema, and returns the
   event dicts.
3. **In-flight tracking**: During transform, signals are counted as "in-flight"
   and contribute to backpressure limits. If transform fails, signals are
   returned to the queue.
4. **Close**: `close()` marks the stream as closed. Subsequent pushes raise
   `RuntimeError`. Pending reads return empty lists.

## Backpressure

Two overflow strategies are available when the buffer exceeds `max_buffer_size`:

| Strategy | Behavior |
|----------|----------|
| `OverflowStrategy.RAISE` | Raises `BufferOverflowError` on push |
| `OverflowStrategy.DROP_OLDEST` | Drops oldest queued signals to make room |

```python
stream = EvidenceCollectorStream(
    config,
    max_buffer_size=1000,
    overflow_strategy=OverflowStrategy.DROP_OLDEST,
)
```

## Thread safety

`EvidenceCollectorStream` is fully thread-safe:

- All mutable state is protected by `threading.Lock`
- Lock is released during expensive transform computation
- Multiple producer threads can call `push()` concurrently
- A single consumer thread should call `read_batch()`

`EvidenceCollector` (the batch API) is **not** thread-safe. Use
`EvidenceCollectorStream` for concurrent access.

## StreamStats

`stream.stats` returns an immutable `StreamStats` snapshot:

- `queued_count`: signals waiting in buffer
- `in_flight_count`: signals currently being transformed
- `buffer_size`: queued + in-flight
- `processed_count`: successfully transformed signals
- `dropped_count`: signals dropped by DROP_OLDEST strategy
- `failed_batch_count`: batches where transform raised an exception

## Governance Drift Toolkit integration

`EvidenceCollectorStream` satisfies the Governance Drift Toolkit `EvidenceStreamReader` Protocol:

```python
stream = EvidenceCollectorStream(config)
# Governance Drift Toolkit consumer calls:
events = stream.read_batch(batch_size=100)
stream.close()
```

Use `StreamCapabilities` to negotiate protocol parameters:

```python
from collector import capabilities_from_config

caps = capabilities_from_config(config)
# caps.supported_signal_types, caps.schema_version, caps.batch_size
```

## StreamWriter

`StreamWriter` is a Protocol for output sinks. `JsonlStreamWriter` is the
built-in implementation:

```python
from collector import JsonlStreamWriter

with JsonlStreamWriter(Path("output.jsonl")) as writer:
    events = stream.read_batch(batch_size=100)
    writer.write_batch(events)
```

Custom writers implement `write_batch(events)` and `close()`.
