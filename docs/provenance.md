# Provenance Chain Documentation

## Design Principle

Every evidence unit must carry its full transformation chain.
If provenance cannot be established, the evidence unit is marked
low-confidence rather than silently emitted.

## ProvenanceChain Structure

```text
origin: str                         # original signal source
steps: tuple[ProvenanceStep, ...]   # ordered transformation steps
integrity_verified: bool            # hash chain verified?
```

## ProvenanceStep Structure

```text
step_name: str          # human-readable step description
input_hash: str         # SHA-256 of input data
output_hash: str        # SHA-256 of output data
transform_name: str     # which transform executed this step
timestamp: datetime     # when this step ran
```

## Hash Chain Integrity

Steps are linked by hash: each step's `input_hash` should match the
previous step's `output_hash`. Call `chain.verify()` to validate:

```python
chain = ProvenanceChain(origin="src", steps=(step1, step2))
verified = chain.verify()  # raises ValueError if broken
assert verified.integrity_verified is True
```

## Content Hashing

`content_hash(data)` produces a deterministic SHA-256 hex digest
of a dictionary using sorted-key JSON serialization.
