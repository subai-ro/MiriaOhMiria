from __future__ import annotations

from .models import Actor, ActorKind, Region, WorldObject, WorldState


def create_world(seed: int = 42, synthetic_actors: int = 30) -> WorldState:
    world = WorldState(seed=seed)

    world.regions = {
        "northwood": Region(
            id="northwood",
            name="Northwood",
            neighbors=("ash_valley", "underpeak"),
            metrics={
                "population": 0.25,
                "wealth": 0.35,
                "forest_health": 0.88,
                "animal_population": 0.82,
                "undead_activity": 0.02,
                "public_fear": 0.08,
            },
        ),
        "ash_valley": Region(
            id="ash_valley",
            name="Ash Valley",
            neighbors=("northwood", "red_march"),
            metrics={
                "population": 0.80,
                "wealth": 0.62,
                "forest_health": 0.32,
                "animal_population": 0.28,
                "undead_activity": 0.12,
                "public_fear": 0.18,
                "death_cult_influence": 0.55,
            },
        ),
        "red_march": Region(
            id="red_march",
            name="Red March",
            neighbors=("ash_valley",),
            metrics={
                "population": 0.48,
                "wealth": 0.47,
                "forest_health": 0.18,
                "animal_population": 0.21,
                "undead_activity": 0.04,
                "public_fear": 0.31,
                "war_tension": 0.71,
            },
        ),
        "underpeak": Region(
            id="underpeak",
            name="Underpeak",
            neighbors=("northwood",),
            accessible=False,
            metrics={
                "population": 0.02,
                "wealth": 0.10,
                "forest_health": 0.05,
                "animal_population": 0.16,
                "undead_activity": 0.20,
                "public_fear": 0.40,
            },
        ),
    }

    world.objects = {
        "lake_mirror": WorldObject(
            id="lake_mirror",
            name="Mirror Lake",
            kind="lake",
            location_id="northwood",
            properties={"size": "small", "water_type": "fresh"},
        ),
        "lake_whisper": WorldObject(
            id="lake_whisper",
            name="Whisper Lake",
            kind="lake",
            location_id="northwood",
            properties={"size": "small", "water_type": "fresh"},
        ),
        "temple_last_gate": WorldObject(
            id="temple_last_gate",
            name="Temple of the Last Gate",
            kind="temple",
            location_id="ash_valley",
            owner_id="god_death",
            properties={"importance": 0.85},
        ),
        "old_ash_graveyard": WorldObject(
            id="old_ash_graveyard",
            name="Old Ash Graveyard",
            kind="graveyard",
            location_id="ash_valley",
            owner_id="god_death",
        ),
        "underpeak_river_gate": WorldObject(
            id="underpeak_river_gate",
            name="Sealed River Gate",
            kind="river_gate",
            location_id="underpeak",
            condition="sealed",
            properties={"water_type": "underground"},
        ),
        "underpeak_burial_shelf": WorldObject(
            id="underpeak_burial_shelf",
            name="Buried Underpeak Shelf",
            kind="burial_shelf",
            location_id="underpeak",
            condition="buried",
            properties={},
        ),
    }

    world.actors["arra"] = Actor(
        id="arra",
        name="Arra",
        kind=ActorKind.PLAYER,
        location_id="ash_valley",
        gold=120,
        inventory={"silver_rod": 1},
    )

    region_cycle = ("northwood", "ash_valley", "red_march")
    for index in range(1, synthetic_actors + 1):
        actor_id = f"sim_{index:03d}"
        world.actors[actor_id] = Actor(
            id=actor_id,
            name=f"Wanderer {index:03d}",
            kind=ActorKind.SIMULATED,
            location_id=region_cycle[(index - 1) % len(region_cycle)],
            gold=50 + (index * 7) % 90,
            inventory={},
            traits={
                "curiosity": ((index * 17) % 100) / 100,
                "piety": ((index * 31) % 100) / 100,
                "risk": ((index * 47) % 100) / 100,
            },
        )

    world.validate_invariants()
    return world
