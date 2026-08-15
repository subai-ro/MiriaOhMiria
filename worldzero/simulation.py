from __future__ import annotations

import random
from collections import Counter
from typing import Callable

from .engine import WorldEngine
from .models import Action, ActionType, Actor, ActorKind


class Simulation:
    def __init__(self, engine: WorldEngine, minutes_per_step: int = 10, seed: int | None = None) -> None:
        self.engine = engine
        self.minutes_per_step = minutes_per_step
        self.rng = random.Random(engine.world.seed + 10_000 if seed is None else seed)
        self._tick_listeners: list[Callable[[], None]] = []
        self._tick_errors: list[str] = []

    @property
    def world(self):
        return self.engine.world

    @property
    def tick_errors(self) -> tuple[str, ...]:
        return tuple(self._tick_errors)

    def subscribe_tick(self, listener: Callable[[], None]) -> None:
        self._tick_listeners.append(listener)

    def run(self, steps: int) -> None:
        if steps < 0:
            raise ValueError("steps must be non-negative")
        for _ in range(steps):
            self.world.advance(self.minutes_per_step)
            for actor_id in sorted(self.world.actors):
                actor = self.world.actors[actor_id]
                if actor.kind is not ActorKind.SIMULATED:
                    continue
                if self.rng.random() > 0.32:
                    continue
                action = self._choose_action(actor)
                if action is not None:
                    self.engine.apply(action)
            for listener in tuple(self._tick_listeners):
                try:
                    listener()
                except Exception as exc:  # divine reasoning must never stop the authoritative world clock
                    self._tick_errors.append(f"{type(exc).__name__}: {exc}")

    def _choose_action(self, actor: Actor) -> Action | None:
        choices: list[tuple[str, float]] = [("travel", 0.24), ("pray", 0.14), ("trade", 0.20)]
        if actor.location_id == "northwood":
            choices.extend((("fish", 0.24), ("wood", 0.18)))
        elif actor.location_id == "ash_valley":
            choices.extend((("necromancy", 0.05), ("pray", 0.17)))
        else:
            choices.append(("pray", 0.25))

        names, weights = zip(*choices)
        choice = self.rng.choices(names, weights=weights, k=1)[0]

        if choice == "travel":
            current = self.world.regions[actor.location_id]
            destinations = [r for r in current.neighbors if self.world.regions[r].accessible]
            if not destinations:
                return None
            return Action(actor.id, ActionType.TRAVEL, target_id=self.rng.choice(sorted(destinations)))

        if choice == "pray":
            deity = self.rng.choices(("nature", "death", "trade"), weights=(0.35, 0.30, 0.35), k=1)[0]
            return Action(actor.id, ActionType.PRAY, params={"deity": deity})

        if choice == "fish":
            lakes = sorted(
                obj.id
                for obj in self.world.objects.values()
                if obj.kind == "lake" and obj.location_id == actor.location_id
            )
            if not lakes:
                return None
            return Action(actor.id, ActionType.FISH, target_id=self.rng.choice(lakes), params={"tool": "hands"})

        if choice == "wood":
            return Action(actor.id, ActionType.HARVEST_WOOD)

        if choice == "trade":
            sellable = [item for item in ("timber", "river_fish", "silver_carp") if actor.inventory.get(item, 0) > 0]
            if sellable:
                return Action(actor.id, ActionType.TRADE, params={"item": self.rng.choice(sellable), "quantity": 1})
            return Action(actor.id, ActionType.PRAY, params={"deity": "trade"})

        if choice == "necromancy":
            if actor.traits.get("necromantic_practice", 0.0) >= 0.24 and self.rng.random() < 0.35:
                return Action(actor.id, ActionType.RAISE_DEAD, target_id=f"grave_{actor.id}")
            return Action(actor.id, ActionType.STUDY_NECROMANCY, target_id="old_ash_graveyard")

        return None

    def event_counts(self) -> Counter[str]:
        return Counter(event.event_type for event in self.engine.ledger.events)


def run_arra_demo(engine: WorldEngine, after_advance: Callable[[], None] | None = None) -> list[str]:
    """Run a small human-authored signal sequence for Archive and divine-agent tests."""
    actions = [
        Action("arra", ActionType.TRAVEL, target_id="northwood"),
        Action("arra", ActionType.FISH, target_id="lake_mirror", params={"tool": "silver_rod"}),
        Action("arra", ActionType.FISH, target_id="lake_whisper", params={"tool": "silver_rod"}),
        Action("arra", ActionType.FISH, target_id="lake_mirror", params={"tool": "silver_rod"}),
        Action("arra", ActionType.TRAVEL, target_id="ash_valley"),
        Action("arra", ActionType.STUDY_NECROMANCY, target_id="old_ash_graveyard"),
        Action("arra", ActionType.STUDY_NECROMANCY, target_id="old_ash_graveyard"),
        Action("arra", ActionType.RAISE_DEAD, target_id="grave_unnamed_01"),
        Action(
            "arra",
            ActionType.SPEAK,
            params={
                "audience": "old_ash_graveyard",
                "text": "Death is not silence. It is a door, and every door can be studied.",
            },
        ),
    ]
    results: list[str] = []
    for action in actions:
        result = engine.apply(action)
        results.append(f"{action.type.value}: {'OK' if result.ok else 'REJECTED'} — {result.message}")
        engine.world.advance(30)
        if after_advance is not None:
            after_advance()
    return results
