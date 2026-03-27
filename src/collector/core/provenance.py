"""Provenance chain tracking for evidence units.

Every evidence unit must carry its full transformation chain.
If provenance cannot be established, the evidence unit is marked
low-confidence rather than silently emitted.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from datetime import datetime


@dataclass(frozen=True)
class ProvenanceStep:
    """Single step in a provenance chain.

    Attributes
    ----------
    step_name : str
        Human-readable description of this transformation step.
    input_hash : str
        Content hash of input data before this step.
    output_hash : str
        Content hash of output data after this step.
    transform_name : str
        Name of the transform that performed this step.
    timestamp : datetime
        When this step was executed.
    """

    step_name: str
    input_hash: str
    output_hash: str
    transform_name: str
    timestamp: datetime

    def __post_init__(self) -> None:
        if not self.step_name:
            msg = "step_name must be non-empty"
            raise ValueError(msg)
        if not self.transform_name:
            msg = "transform_name must be non-empty"
            raise ValueError(msg)


@dataclass(frozen=True)
class ProvenanceChain:
    """Full provenance chain from raw signal to evidence unit.

    Attributes
    ----------
    origin : str
        Original signal source identifier.
    steps : tuple[ProvenanceStep, ...]
        Ordered transformation steps.
    integrity_verified : bool
        Whether hash chain integrity has been verified.
    """

    origin: str
    steps: tuple[ProvenanceStep, ...] = ()
    integrity_verified: bool = False

    def __post_init__(self) -> None:
        if not self.origin:
            msg = "origin must be non-empty"
            raise ValueError(msg)

    def append(self, step: ProvenanceStep) -> ProvenanceChain:
        """Return a new chain with the step appended.

        Parameters
        ----------
        step : ProvenanceStep
            Step to append to the chain.

        Returns
        -------
        ProvenanceChain
            New chain with the step added.
        """
        return ProvenanceChain(
            origin=self.origin,
            steps=(*self.steps, step),
            integrity_verified=False,
        )

    def verify(self) -> ProvenanceChain:
        """Return a copy marked as integrity-verified.

        Verification checks that consecutive steps have matching
        output_hash -> input_hash linkage.

        Returns
        -------
        ProvenanceChain
            New chain with integrity_verified set.

        Raises
        ------
        ValueError
            If hash chain is broken.
        """
        for i in range(1, len(self.steps)):
            if self.steps[i].input_hash != self.steps[i - 1].output_hash:
                msg = (
                    f"Broken hash chain at step {i}: "
                    f"expected input_hash={self.steps[i - 1].output_hash}, "
                    f"got {self.steps[i].input_hash}"
                )
                raise ValueError(msg)
        return ProvenanceChain(
            origin=self.origin,
            steps=self.steps,
            integrity_verified=True,
        )


def content_hash(data: dict[str, Any]) -> str:
    """Compute deterministic SHA-256 hash of a dictionary.

    Parameters
    ----------
    data : dict
        Data to hash.

    Returns
    -------
    str
        Hex-encoded SHA-256 digest.
    """
    canonical = json.dumps(data, sort_keys=True, default=str)
    return hashlib.sha256(canonical.encode()).hexdigest()
