from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterable


class PerceptualAspect(str, Enum):
    """A fact that may be opposed independently at the perceptual boundary."""

    EVENT = "event"
    IDENTITY = "identity"
    CAUSAL_LINK = "causal_link"


@dataclass(frozen=True)
class PerceptualBarrier:
    """Objective opposition to a deity's perception.

    This is deliberately separate from mundane ``secrecy``.  ``strength`` is
    only a prototype resistance parameter; the resolver may later incorporate
    wards, entity nature, artifacts, opposing gods, local metaphysics, or
    deity-specific faculties without changing the WorldEvent contract.

    Empty ``subject_actor_ids`` means the barrier applies to the whole fact.
    Empty ``affected_entity_ids`` means it applies to every observer.
    """

    kind: str
    strength: float
    aspects: tuple[PerceptualAspect, ...] = (PerceptualAspect.IDENTITY,)
    subject_actor_ids: tuple[str, ...] = ()
    affected_entity_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.kind.strip():
            raise ValueError("perceptual barrier kind cannot be empty")
        if not 0.0 <= self.strength <= 1.0:
            raise ValueError("perceptual barrier strength must be in [0, 1]")
        if not self.aspects:
            raise ValueError("perceptual barrier must oppose at least one aspect")

    def applies_to(
        self,
        entity_id: str,
        aspect: PerceptualAspect,
        *,
        actor_id: str | None = None,
    ) -> bool:
        if aspect not in self.aspects:
            return False
        if self.affected_entity_ids and entity_id not in self.affected_entity_ids:
            return False
        if self.subject_actor_ids:
            return actor_id is not None and actor_id in self.subject_actor_ids
        return True

    def as_dict(self) -> dict:
        return {
            "kind": self.kind,
            "strength": self.strength,
            "aspects": [item.value for item in self.aspects],
            "subject_actor_ids": list(self.subject_actor_ids),
            "affected_entity_ids": list(self.affected_entity_ids),
        }


def opposition_strength(
    barriers: Iterable[PerceptualBarrier],
    entity_id: str,
    aspect: PerceptualAspect,
    *,
    actor_id: str | None = None,
) -> float:
    """Return the strongest applicable opposition without exposing its cause."""

    return max(
        (
            barrier.strength
            for barrier in barriers
            if barrier.applies_to(entity_id, aspect, actor_id=actor_id)
        ),
        default=0.0,
    )


def opposition_blocks(
    barriers: Iterable[PerceptualBarrier],
    entity_id: str,
    aspect: PerceptualAspect,
    penetration: float,
    *,
    actor_id: str | None = None,
) -> bool:
    """Resolve one prototype opposition check.

    No scalar Presence bypass exists here.  ``penetration`` is a composite
    supplied by the observer layer; later mechanics can replace that composite
    while barriers and their provenance remain first-class.
    """

    resistance = opposition_strength(
        barriers,
        entity_id,
        aspect,
        actor_id=actor_id,
    )
    if resistance <= 0.0:
        return False
    return resistance >= max(0.0, min(1.0, penetration))
