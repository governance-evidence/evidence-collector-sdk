# Contributing

Thank you for your interest in contributing to the Evidence Collector SDK.

## Prerequisites

- Python 3.11 or later
- GNU Make

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
make install
```

This installs the package in editable mode with dev dependencies and configures
pre-commit hooks.

## Development workflow

1. Create a working branch
1. Make your changes
1. Run the full check suite:

```bash
make check    # ruff lint + mypy strict + pytest 100% coverage + header check
```

Individual targets are also available:

```bash
make lint       # ruff check + format verification
make format     # auto-fix lint + formatting
make typecheck  # mypy --strict
make test       # pytest with 100% coverage requirement
make headers    # verify source file headers
```

1. Commit (pre-commit hooks will run automatically)
1. Push (pre-push hook enforces 100% test coverage)

## Code conventions

- **Frozen dataclasses** for all value types (immutability is a governance requirement)
- **Protocol-based extensibility** for transforms (`SignalTransform`) and writers (`StreamWriter`)
- **Timezone-aware datetimes** everywhere (`datetime.now(tz=UTC)`, never naive)
- **`from __future__ import annotations`** in every module
- **NumPy-style docstrings** for all public classes and functions
- **No `print()` in library code** (enforced by ruff T20 rule; allowed in examples and scripts)
- **Type annotations on all public API** (enforced by mypy strict + ruff ANN rules)
- **`MappingProxyType`** for dict fields in frozen dataclasses (prevents mutation after construction)

## Testing expectations

- **100% line and branch coverage** is enforced (`--cov-fail-under=100`)
- **Property-based tests** (Hypothesis) for invariants: confidence bounds, hash determinism, etc.
- **Negative tests** for all validation paths: invalid inputs, empty strings, out-of-range values
- **Integration tests** for end-to-end pipeline: signal -> evidence unit -> Decision Event Schema -> file
- Test names should be descriptive: `test_naive_datetime_rejected`, not `test_1`

## Architecture

See [CLAUDE.md](CLAUDE.md) for module responsibilities and dependency graph.

## Pre-commit hooks

The project uses pre-commit hooks covering:

- Code quality: ruff (28 rule categories), mypy strict, vulture (dead code)
- Security: detect-secrets, detect-private-key, bandit (via ruff S rules)
- Formatting: ruff-format, markdownlint, yamllint, toml-sort
- Git hygiene: check-merge-conflict, check-added-large-files
- Spelling: typos source-code spell checker
- Coverage: pytest with 100% enforcement (pre-push stage)
