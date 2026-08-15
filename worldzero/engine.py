from __future__ import annotations

import random
from typing import Callable

from .ledger import EventLedger
from .materials import MaterialCatalog, create_default_material_catalog
from .models import Action, ActionResult, ActionType, Actor, WorldState
from .perception import PerceptualAspect, PerceptualBarrier


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


class WorldEngine:
    """Authoritative mutation boundary for World Zero."""

    def __init__(
        self,
        world: WorldState,
        ledger: EventLedger | None = None,
        seed: int | None = None,
        materials: MaterialCatalog | None = None,
    ) -> None:
        self.world = world
        self.ledger = ledger or EventLedger()
        self.rng = random.Random(world.seed if seed is None else seed)
        self.materials = materials or create_default_material_catalog()
        self._handlers: dict[ActionType, Callable[[Actor, Action], ActionResult]] = {
            ActionType.TRAVEL: self._travel,
            ActionType.VISIT_SITE: self._visit_site,
            ActionType.FISH: self._fish,
            ActionType.HARVEST_WOOD: self._harvest_wood,
            ActionType.TRADE: self._trade,
            ActionType.PRAY: self._pray,
            ActionType.STUDY_NECROMANCY: self._study_necromancy,
            ActionType.RAISE_DEAD: self._raise_dead,
            ActionType.SPEAK: self._speak,
            ActionType.DESTROY_TEMPLE: self._destroy_temple,
        }

    def apply(self, action: Action) -> ActionResult:
        actor = self.world.actors.get(action.actor_id)
        if actor is None:
            return ActionResult(False, f"Unknown actor: {action.actor_id}")

        handler = self._handlers.get(action.type)
        if handler is None:
            return ActionResult(False, f"Unsupported action: {action.type}")

        result = handler(actor, action)
        self.world.validate_invariants()
        return result

    def _record(
        self,
        *,
        event_type: str,
        actor: Actor,
        target_ids: tuple[str, ...] = (),
        tags: tuple[str, ...] = (),
        data: dict | None = None,
        location_id: str | None = None,
        publicity: float = 0.5,
        secrecy: float = 0.0,
        witness_limit: int = 3,
        causal_parent_ids: tuple[int, ...] = (),
        perceptual_barriers: tuple[PerceptualBarrier, ...] = (),
    ) -> ActionResult:
        event_location = location_id or actor.location_id
        witnesses = tuple(
            candidate.id
            for candidate in sorted(self.world.actors.values(), key=lambda item: item.id)
            if candidate.id != actor.id and candidate.location_id == event_location
        )[:witness_limit]
        event = self.ledger.append(
            game_minute=self.world.game_minute,
            event_type=event_type,
            actor_ids=(actor.id,),
            target_ids=target_ids,
            location_id=event_location,
            tags=tags,
            witness_ids=witnesses,
            publicity=publicity,
            secrecy=secrecy,
            data=data or {},
            causal_parent_ids=causal_parent_ids,
            perceptual_barriers=perceptual_barriers + self._actor_perceptual_barriers(actor),
        )
        return ActionResult(True, event_type, event.event_id)

    @staticmethod
    def _actor_perceptual_barriers(actor: Actor) -> tuple[PerceptualBarrier, ...]:
        """Prototype seam for entity-level supernatural concealment.

        These traits are server-side experimental mechanics, not actions a
        mortal can request.  They prove that mundane secrecy and perceptual
        opposition are different layers; future sources can be artifacts,
        wards, locations, other deities, or stranger metaphysics.
        """
        barriers: list[PerceptualBarrier] = []
        identity_veil = float(actor.traits.get("divine_identity_veil", 0.0))
        if identity_veil > 0.0:
            barriers.append(
                PerceptualBarrier(
                    kind="entity_identity_veil",
                    strength=_clamp(identity_veil),
                    aspects=(PerceptualAspect.IDENTITY, PerceptualAspect.CAUSAL_LINK),
                    subject_actor_ids=(actor.id,),
                )
            )
        event_veil = float(actor.traits.get("divine_event_veil", 0.0))
        if event_veil > 0.0:
            barriers.append(
                PerceptualBarrier(
                    kind="entity_event_veil",
                    strength=_clamp(event_veil),
                    aspects=(
                        PerceptualAspect.EVENT,
                        PerceptualAspect.IDENTITY,
                        PerceptualAspect.CAUSAL_LINK,
                    ),
                    subject_actor_ids=(actor.id,),
                )
            )
        return tuple(barriers)

    def _travel(self, actor: Actor, action: Action) -> ActionResult:
        target = action.target_id
        if not target or target not in self.world.regions:
            return ActionResult(False, "Unknown destination")
        current = self.world.regions[actor.location_id]
        destination = self.world.regions[target]
        if target not in current.neighbors:
            return ActionResult(False, f"{destination.name} is not adjacent to {current.name}")
        if not destination.accessible:
            return ActionResult(False, f"{destination.name} is currently inaccessible")

        origin = actor.location_id
        actor.location_id = target
        return self._record(
            event_type="TRAVELLED",
            actor=actor,
            target_ids=(target,),
            location_id=target,
            tags=("movement",),
            data={"from": origin, "to": target},
            publicity=0.45,
            secrecy=0.10,
            witness_limit=4,
        )

    def _visit_site(self, actor: Actor, action: Action) -> ActionResult:
        site = self.world.objects.get(action.target_id or "")
        if site is None:
            return ActionResult(False, "Unknown site")
        if site.location_id != actor.location_id:
            return ActionResult(False, "Site is not in the actor's current region")

        secret = bool(action.params.get("secret", False))
        return self._record(
            event_type="SITE_VISITED",
            actor=actor,
            target_ids=(site.id,),
            tags=("visit", "site", site.kind),
            data={"site_kind": site.kind, "secret": secret},
            publicity=0.06 if secret else 0.25,
            secrecy=0.90 if secret else 0.15,
            witness_limit=0 if secret else 2,
        )

    def _fish(self, actor: Actor, action: Action) -> ActionResult:
        lake = self.world.objects.get(action.target_id or "")
        if lake is None or lake.kind != "lake" or lake.location_id != actor.location_id:
            return ActionResult(False, "A local lake must be selected")

        tool = str(action.params.get("tool", "hands"))
        try:
            material_profile = self.materials.require(tool)
        except ValueError as exc:
            return ActionResult(False, str(exc))
        if tool != "hands" and actor.inventory.get(tool, 0) < 1:
            return ActionResult(False, f"Actor does not possess contact item: {tool}")

        contact = self.materials.medium_contact(
            item_id=tool,
            medium_kind="water",
            medium_ref=lake.id,
            base_contact_units=1.0,
        )

        roll = self.rng.random()
        if roll < 0.20:
            catch = "nothing"
        elif roll < 0.85:
            catch = "river_fish"
            actor.inventory[catch] = actor.inventory.get(catch, 0) + 1
        else:
            catch = "silver_carp"
            actor.inventory[catch] = actor.inventory.get(catch, 0) + 1

        region = self.world.regions[actor.location_id]
        region.metrics["animal_population"] = _clamp(region.metrics.get("animal_population", 0.5) - 0.0005)

        tags = ["fishing", "water", "nature", "material_contact", tool]
        for material_id in material_profile.material_fractions:
            tags.extend((material_id, f"material:{material_id}"))

        return self._record(
            event_type="FISHED",
            actor=actor,
            target_ids=(lake.id,),
            tags=tuple(tags),
            data={
                "catch": catch,
                "lake_size": lake.properties.get("size"),
                "tool": tool,
                "material_contacts": [contact.as_dict()],
            },
            publicity=0.12,
            secrecy=0.20,
            witness_limit=1,
        )

    def _harvest_wood(self, actor: Actor, action: Action) -> ActionResult:
        if actor.location_id != "northwood":
            return ActionResult(False, "Wood harvesting is only implemented in Northwood")
        amount = self.rng.randint(1, 3)
        actor.inventory["timber"] = actor.inventory.get("timber", 0) + amount
        region = self.world.regions[actor.location_id]
        region.metrics["forest_health"] = _clamp(region.metrics["forest_health"] - amount * 0.002)
        return self._record(
            event_type="WOOD_HARVESTED",
            actor=actor,
            tags=("nature", "resource", "logging"),
            data={"amount": amount, "resource": "timber"},
            publicity=0.30,
            secrecy=0.10,
            witness_limit=2,
        )

    def _trade(self, actor: Actor, action: Action) -> ActionResult:
        prices = {"timber": 6, "river_fish": 4, "silver_carp": 18}
        item = str(action.params.get("item", ""))
        quantity = int(action.params.get("quantity", 1))
        if item not in prices or quantity <= 0:
            return ActionResult(False, "Unsupported trade")
        if actor.inventory.get(item, 0) < quantity:
            return ActionResult(False, "Not enough inventory")

        actor.inventory[item] -= quantity
        actor.gold += prices[item] * quantity
        return self._record(
            event_type="ITEM_SOLD",
            actor=actor,
            tags=("trade", "economy"),
            data={"item": item, "quantity": quantity, "gold_received": prices[item] * quantity},
            publicity=0.55,
            witness_limit=5,
        )

    def _pray(self, actor: Actor, action: Action) -> ActionResult:
        deity = str(action.params.get("deity", "")).strip().lower()
        if deity not in {"nature", "death", "trade"}:
            return ActionResult(False, "Unknown deity")
        key = f"devotion_{deity}"
        actor.traits[key] = _clamp(actor.traits.get(key, 0.0) + 0.02)
        return self._record(
            event_type="PRAYER_OFFERED",
            actor=actor,
            tags=("religion", deity),
            data={"deity": deity},
            publicity=0.50,
            secrecy=0.05,
            witness_limit=4,
        )

    def _study_necromancy(self, actor: Actor, action: Action) -> ActionResult:
        if actor.location_id != "ash_valley":
            return ActionResult(False, "Known necromantic sources are currently in Ash Valley")
        actor.traits["necromantic_practice"] = _clamp(actor.traits.get("necromantic_practice", 0.0) + 0.12)
        return self._record(
            event_type="NECROMANCY_STUDIED",
            actor=actor,
            target_ids=((action.target_id or "old_ash_graveyard"),),
            tags=("death", "magic", "necromancy", "forbidden_knowledge"),
            data={"practice_level": actor.traits["necromantic_practice"]},
            publicity=0.08,
            secrecy=0.85,
            witness_limit=1,
        )

    def _raise_dead(self, actor: Actor, action: Action) -> ActionResult:
        if actor.location_id != "ash_valley":
            return ActionResult(False, "No usable corpse is available here")
        if actor.traits.get("necromantic_practice", 0.0) < 0.20:
            return ActionResult(False, "Necromantic practice is insufficient")
        region = self.world.regions[actor.location_id]
        region.metrics["undead_activity"] = _clamp(region.metrics["undead_activity"] + 0.015)
        region.metrics["public_fear"] = _clamp(region.metrics["public_fear"] + 0.01)
        return self._record(
            event_type="DEAD_RAISED",
            actor=actor,
            target_ids=((action.target_id or "anonymous_corpse"),),
            tags=("death", "magic", "necromancy", "undead"),
            data={"undead_activity": region.metrics["undead_activity"]},
            publicity=0.18,
            secrecy=0.65,
            witness_limit=2,
        )

    def _speak(self, actor: Actor, action: Action) -> ActionResult:
        text = str(action.params.get("text", "")).strip()
        if not text:
            return ActionResult(False, "Speech cannot be empty")
        if len(text) > 500:
            return ActionResult(False, "Speech exceeds the prototype limit")
        audience = str(action.params.get("audience", "public"))
        is_public = audience == "public"
        tags = ["speech", "diegetic"]
        data = {"audience": audience, "text": text}
        causal_parent_ids: tuple[int, ...] = ()

        response_to = action.params.get("response_to_probe_ref")
        if response_to is not None:
            if not isinstance(response_to, str) or not response_to.strip():
                return ActionResult(False, "Probe response requires a non-empty probe ref")
            probe_event = next(
                (
                    event
                    for event in reversed(self.ledger.events)
                    if event.event_type == "DIVINE_PROBE_MANIFESTED"
                    and event.data.get("probe_ref") == response_to
                ),
                None,
            )
            if probe_event is None:
                return ActionResult(False, "Referenced divine probe does not exist")
            probe_data = probe_event.data
            if (
                actor.id not in probe_event.target_ids
            ):
                return ActionResult(False, "Actor cannot answer a divine probe they did not receive")
            probe_ref = probe_data.get("probe_ref")
            source_entity_id = probe_data.get("source_entity_id")
            if not isinstance(probe_ref, str) or not isinstance(source_entity_id, str):
                return ActionResult(False, "Referenced divine probe is malformed")
            tags.append("divine_probe_response")
            data.update(
                {
                    "response_to_probe_ref": probe_ref,
                    "response_to_entity_id": source_entity_id,
                }
            )
            causal_parent_ids = (probe_event.event_id,)

        return self._record(
            event_type="DIEGETIC_SPEECH",
            actor=actor,
            target_ids=((action.target_id,) if action.target_id else ()),
            tags=tuple(tags),
            data=data,
            publicity=0.85 if is_public else 0.20,
            secrecy=0.05 if is_public else 0.65,
            witness_limit=8 if is_public else 2,
            causal_parent_ids=causal_parent_ids,
        )

    def _destroy_temple(self, actor: Actor, action: Action) -> ActionResult:
        temple = self.world.objects.get(action.target_id or "")
        if temple is None or temple.kind != "temple":
            return ActionResult(False, "Target is not a temple")
        if temple.location_id != actor.location_id:
            return ActionResult(False, "Temple is not in the actor's region")
        if temple.condition == "destroyed":
            return ActionResult(False, "Temple is already destroyed")

        secret = bool(action.params.get("secret", False))
        temple.condition = "destroyed"
        region = self.world.regions[actor.location_id]
        if temple.owner_id == "god_death":
            region.metrics["death_cult_influence"] = _clamp(region.metrics.get("death_cult_influence", 0.0) - 0.10)
        region.metrics["public_fear"] = _clamp(region.metrics.get("public_fear", 0.0) + 0.05)
        return self._record(
            event_type="TEMPLE_DESTROYED",
            actor=actor,
            target_ids=(temple.id,),
            tags=("religion", "destruction", "death", "temple"),
            data={
                "owner_id": temple.owner_id,
                "importance": temple.properties.get("importance", 0.5),
                "condition": temple.condition,
                "attempted_secretly": secret,
            },
            publicity=0.05 if secret else 0.95,
            secrecy=0.95 if secret else 0.05,
            witness_limit=0 if secret else 8,
        )
