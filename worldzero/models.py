from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable


class ActorKind(str, Enum):
    PLAYER = "player"
    SIMULATED = "simulated"


class ActionType(str, Enum):
    TRAVEL = "travel"
    VISIT_SITE = "visit_site"
    FISH = "fish"
    HARVEST_WOOD = "harvest_wood"
    TRADE = "trade"
    PRAY = "pray"
    STUDY_NECROMANCY = "study_necromancy"
    RAISE_DEAD = "raise_dead"
    SPEAK = "speak"
    DESTROY_TEMPLE = "destroy_temple"


@dataclass
class Region:
    id: str
    name: str
    neighbors: tuple[str, ...]
    accessible: bool = True
    metrics: dict[str, float] = field(default_factory=dict)


@dataclass
class Actor:
    id: str
    name: str
    kind: ActorKind
    location_id: str
    gold: int = 100
    inventory: dict[str, int] = field(default_factory=dict)
    traits: dict[str, float] = field(default_factory=dict)


@dataclass
class WorldObject:
    id: str
    name: str
    kind: str
    location_id: str
    owner_id: str | None = None
    condition: str = "intact"
    properties: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Action:
    actor_id: str
    type: ActionType
    target_id: str | None = None
    params: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ActionResult:
    ok: bool
    message: str
    event_id: int | None = None


@dataclass
class WorldState:
    seed: int
    game_minute: int = 0
    regions: dict[str, Region] = field(default_factory=dict)
    actors: dict[str, Actor] = field(default_factory=dict)
    objects: dict[str, WorldObject] = field(default_factory=dict)
    _time_advance_listeners: list[Callable[[int], None]] = field(
        default_factory=list,
        repr=False,
        compare=False,
    )

    def subscribe_time_advance(self, listener: Callable[[int], None]) -> None:
        if listener not in self._time_advance_listeners:
            self._time_advance_listeners.append(listener)

    def advance(self, minutes: int) -> None:
        if minutes <= 0:
            raise ValueError("World clock can only move forward")
        self.game_minute += minutes
        for listener in tuple(self._time_advance_listeners):
            listener(self.game_minute)

    @property
    def formatted_time(self) -> str:
        day = self.game_minute // (24 * 60) + 1
        within_day = self.game_minute % (24 * 60)
        hour, minute = divmod(within_day, 60)
        return f"Day {day}, {hour:02d}:{minute:02d}"

    def validate_invariants(self) -> None:
        for actor in self.actors.values():
            if actor.location_id not in self.regions:
                raise AssertionError(f"Actor {actor.id} is outside the world")
            if actor.gold < 0:
                raise AssertionError(f"Actor {actor.id} has negative gold")
            if any(amount < 0 for amount in actor.inventory.values()):
                raise AssertionError(f"Actor {actor.id} has negative inventory")

        for region in self.regions.values():
            for key in ("forest_health", "animal_population", "undead_activity", "public_fear"):
                if key in region.metrics and not 0.0 <= region.metrics[key] <= 1.0:
                    raise AssertionError(f"{region.id}.{key} escaped [0, 1]")
