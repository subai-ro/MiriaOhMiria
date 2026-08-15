from __future__ import annotations

from dataclasses import dataclass

from .ledger import WorldEvent
from .models import WorldState


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, value))


@dataclass(frozen=True)
class PresenceProfile:
    entity_id: str
    base_by_region: dict[str, float]
    anchor_by_kind: dict[str, float]
    owned_anchor_bonus: float = 0.0
    # 1.0 is 100% of the deity's voluntarily allocatable conscious attention.
    # Diffuse/base Presence is a separate passive sensing layer and therefore
    # does not consume this active budget.
    consciousness_budget: float = 1.0


@dataclass(frozen=True)
class TemporalObservance:
    observance_id: str
    name: str
    entity_id: str
    period_days: int
    phase_day: int
    target_kinds: frozenset[str]
    presence_bonus: float
    salience_by_tag: dict[str, float]

    def active(self, game_minute: int) -> bool:
        day = game_minute // (24 * 60) + 1
        return (day - self.phase_day) % self.period_days == 0


@dataclass(frozen=True)
class PresenceSnapshot:
    entity_id: str
    region_id: str
    target_id: str | None
    game_minute: int
    base: float
    anchor: float
    focus: float
    temporal: float
    total: float
    active_observances: tuple[str, ...]


DEFAULT_PRESENCE_PROFILES: tuple[PresenceProfile, ...] = (
    PresenceProfile(
        entity_id="god_nature",
        base_by_region={"northwood": 0.60, "ash_valley": 0.12, "red_march": 0.08, "underpeak": 0.25},
        anchor_by_kind={"lake": 0.18, "river_gate": 0.12},
        owned_anchor_bonus=0.12,
    ),
    PresenceProfile(
        entity_id="god_death",
        base_by_region={"northwood": 0.08, "ash_valley": 0.22, "red_march": 0.15, "underpeak": 0.30},
        anchor_by_kind={"graveyard": 0.16, "temple": 0.18},
        owned_anchor_bonus=0.18,
    ),
    PresenceProfile(
        entity_id="god_trade",
        base_by_region={"northwood": 0.14, "ash_valley": 0.50, "red_march": 0.42, "underpeak": 0.04},
        anchor_by_kind={"market": 0.20, "temple": 0.10},
        owned_anchor_bonus=0.12,
    ),
)


# Prototype calendar only. Day 10, 20, 30... are used so the temporal effect is
# easy to test before the final calendar/lore exists.
DEFAULT_OBSERVANCES: tuple[TemporalObservance, ...] = (
    TemporalObservance(
        observance_id="day_of_the_dead",
        name="Day of the Dead",
        entity_id="god_death",
        period_days=10,
        phase_day=10,
        target_kinds=frozenset({"graveyard"}),
        presence_bonus=0.48,
        salience_by_tag={"visit": 0.62, "graveyard": 0.72, "prayer": 0.55, "death": 0.45},
    ),
)


class DivinePresenceField:
    """Spatial-temporal concentration of divine consciousness."""

    def __init__(
        self,
        world: WorldState,
        profiles: tuple[PresenceProfile, ...] = DEFAULT_PRESENCE_PROFILES,
        observances: tuple[TemporalObservance, ...] = DEFAULT_OBSERVANCES,
    ) -> None:
        self.world = world
        self.profiles = {profile.entity_id: profile for profile in profiles}
        self.observances = observances
        self._focus: dict[str, dict[str, float]] = {entity_id: {} for entity_id in self.profiles}

    def set_focus(self, entity_id: str, location_id: str, intensity: float) -> None:
        if entity_id not in self.profiles:
            raise KeyError(entity_id)
        if location_id not in self.world.regions and location_id not in self.world.objects:
            raise ValueError(f"Unknown focus location: {location_id}")
        if not 0.0 <= intensity <= 1.0:
            raise ValueError("Focus intensity must be in [0, 1]")

        allocations = self._focus[entity_id]
        previous = allocations.get(location_id, 0.0)
        proposed_total = sum(allocations.values()) - previous + intensity
        budget = self.profiles[entity_id].consciousness_budget
        if proposed_total > budget + 1e-9:
            raise ValueError(f"Focus budget exceeded: {proposed_total:.2f} > {budget:.2f}")
        if intensity == 0.0:
            allocations.pop(location_id, None)
        else:
            allocations[location_id] = intensity

    def clear_focus(self, entity_id: str) -> None:
        self._focus[entity_id].clear()

    def replace_focus(self, entity_id: str, allocations: dict[str, float]) -> None:
        """Atomically replace an entity's finite conscious-focus allocation."""
        if entity_id not in self.profiles:
            raise KeyError(entity_id)
        cleaned: dict[str, float] = {}
        for location_id, intensity in allocations.items():
            if location_id not in self.world.regions and location_id not in self.world.objects:
                raise ValueError(f"Unknown focus location: {location_id}")
            if not 0.0 <= intensity <= 1.0:
                raise ValueError("Focus intensity must be in [0, 1]")
            if intensity > 0.0:
                cleaned[location_id] = intensity

        total = sum(cleaned.values())
        budget = self.profiles[entity_id].consciousness_budget
        if total > budget + 1e-9:
            raise ValueError(f"Focus budget exceeded: {total:.2f} > {budget:.2f}")
        self._focus[entity_id] = cleaned

    def focus_allocations(self, entity_id: str) -> dict[str, float]:
        return dict(self._focus[entity_id])

    def active_observances(self, entity_id: str, game_minute: int | None = None) -> tuple[TemporalObservance, ...]:
        minute = self.world.game_minute if game_minute is None else game_minute
        return tuple(
            observance
            for observance in self.observances
            if observance.entity_id == entity_id and observance.active(minute)
        )

    def snapshot_for_event(self, entity_id: str, event: WorldEvent) -> PresenceSnapshot:
        target_id = event.target_ids[0] if event.target_ids and event.target_ids[0] in self.world.objects else None
        return self.snapshot_at(
            entity_id,
            region_id=event.location_id,
            target_id=target_id,
            game_minute=event.game_minute,
        )

    def snapshot_at(
        self,
        entity_id: str,
        *,
        region_id: str,
        target_id: str | None = None,
        game_minute: int | None = None,
    ) -> PresenceSnapshot:
        profile = self.profiles[entity_id]
        minute = self.world.game_minute if game_minute is None else game_minute
        base = profile.base_by_region.get(region_id, 0.02)

        target = self.world.objects.get(target_id or "")
        anchor = 0.0
        if target is not None:
            condition_factor = 0.15 if target.condition == "destroyed" else 1.0
            anchor += profile.anchor_by_kind.get(target.kind, 0.0) * condition_factor
            if target.owner_id == entity_id:
                anchor += profile.owned_anchor_bonus * condition_factor

        focus = self._focus[entity_id].get(region_id, 0.0)
        if target_id:
            focus += self._focus[entity_id].get(target_id, 0.0)

        active = []
        temporal = 0.0
        for observance in self.active_observances(entity_id, minute):
            if observance.target_kinds and (target is None or target.kind not in observance.target_kinds):
                continue
            temporal += observance.presence_bonus
            active.append(observance.name)

        return PresenceSnapshot(
            entity_id=entity_id,
            region_id=region_id,
            target_id=target_id,
            game_minute=minute,
            base=base,
            anchor=anchor,
            focus=focus,
            temporal=temporal,
            total=_clamp(base + anchor + focus + temporal),
            active_observances=tuple(active),
        )

    def contextual_salience(self, entity_id: str, event: WorldEvent) -> float:
        target = self.world.objects.get(event.target_ids[0]) if event.target_ids else None
        salience = 0.0
        for observance in self.active_observances(entity_id, event.game_minute):
            if observance.target_kinds and (target is None or target.kind not in observance.target_kinds):
                continue
            for tag in event.tags:
                salience = max(salience, observance.salience_by_tag.get(tag, 0.0))
        return _clamp(salience)
