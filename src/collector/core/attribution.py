"""Actor attribution for evidence units.

Attribution identifies who or what produced a signal, their position
in the delegation chain, and the responsibility boundary they operate within.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Attribution:
    """Attribution metadata linking an evidence unit to its actor.

    Attributes
    ----------
    actor_id : str
        Unique identifier of the actor (system, user, service).
    actor_type : str
        Classification: "system", "human", or "hybrid".
    organizational_role : str | None
        Role of the actor in the organization (e.g., "fraud-analyst",
        "scoring-model"). None when role is unknown.
    delegation_chain : tuple[str, ...]
        Ordered list of delegation from original authority to this actor.
    responsibility_boundary : str | None
        Description of the actor's responsibility scope. None when unknown.
    """

    actor_id: str
    actor_type: str
    organizational_role: str | None = None
    delegation_chain: tuple[str, ...] = ()
    responsibility_boundary: str | None = None

    _VALID_ACTOR_TYPES: frozenset[str] = frozenset({"system", "human", "hybrid"})

    def __post_init__(self) -> None:
        if not self.actor_id:
            msg = "actor_id must be non-empty"
            raise ValueError(msg)
        if self.actor_type not in self._VALID_ACTOR_TYPES:
            msg = f"actor_type must be one of {self._VALID_ACTOR_TYPES}, got {self.actor_type!r}"
            raise ValueError(msg)
