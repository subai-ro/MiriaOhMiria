from __future__ import annotations

import unittest

from worldzero.engine import WorldEngine
from worldzero.ledger import EventLedger
from worldzero.models import Action, ActionType
from worldzero.seed import create_world
from worldzero.simulation import Simulation, run_arra_demo


def simulate(seed: int = 42, actors: int = 12, steps: int = 40):
    world = create_world(seed=seed, synthetic_actors=actors)
    engine = WorldEngine(world, EventLedger(), seed=seed + 1)
    simulation = Simulation(engine, minutes_per_step=10, seed=seed + 2)
    simulation.run(steps)
    return world, engine


class WorldZeroTests(unittest.TestCase):
    def test_same_seed_produces_same_history(self) -> None:
        _, first = simulate()
        _, second = simulate()
        self.assertEqual(
            [event.as_dict() for event in first.ledger.events],
            [event.as_dict() for event in second.ledger.events],
        )

    def test_underpeak_is_inaccessible(self) -> None:
        world = create_world(synthetic_actors=0)
        engine = WorldEngine(world)
        engine.apply(Action("arra", ActionType.TRAVEL, target_id="northwood"))
        before = len(engine.ledger.events)
        result = engine.apply(Action("arra", ActionType.TRAVEL, target_id="underpeak"))
        self.assertFalse(result.ok)
        self.assertEqual("northwood", world.actors["arra"].location_id)
        self.assertEqual(before, len(engine.ledger.events))

    def test_silver_fishing_is_recorded_for_future_resonance(self) -> None:
        world = create_world(synthetic_actors=0)
        engine = WorldEngine(world, seed=7)
        self.assertTrue(engine.apply(Action("arra", ActionType.TRAVEL, target_id="northwood")).ok)
        result = engine.apply(
            Action("arra", ActionType.FISH, target_id="lake_mirror", params={"tool": "silver_rod"})
        )
        self.assertTrue(result.ok)
        event = engine.ledger.events[-1]
        self.assertEqual("FISHED", event.event_type)
        self.assertIn("silver_rod", event.tags)
        self.assertEqual("small", event.data["lake_size"])

    def test_temple_cannot_be_destroyed_twice(self) -> None:
        world = create_world(synthetic_actors=0)
        engine = WorldEngine(world)
        action = Action("arra", ActionType.DESTROY_TEMPLE, target_id="temple_last_gate")
        first = engine.apply(action)
        fear_after_first = world.regions["ash_valley"].metrics["public_fear"]
        influence_after_first = world.regions["ash_valley"].metrics["death_cult_influence"]
        events_after_first = len(engine.ledger.events)
        second = engine.apply(action)

        self.assertTrue(first.ok)
        self.assertFalse(second.ok)
        self.assertEqual(events_after_first, len(engine.ledger.events))
        self.assertEqual(fear_after_first, world.regions["ash_valley"].metrics["public_fear"])
        self.assertEqual(influence_after_first, world.regions["ash_valley"].metrics["death_cult_influence"])

    def test_secret_temple_destruction_is_recorded_as_secret(self) -> None:
        world = create_world(synthetic_actors=6)
        engine = WorldEngine(world)
        result = engine.apply(
            Action("arra", ActionType.DESTROY_TEMPLE, target_id="temple_last_gate", params={"secret": True})
        )
        self.assertTrue(result.ok)
        event = engine.ledger.events[-1]
        self.assertEqual((), event.witness_ids)
        self.assertGreaterEqual(event.secrecy, 0.9)
        self.assertLessEqual(event.publicity, 0.1)

    def test_demo_creates_necromancy_and_nereid_signals(self) -> None:
        world = create_world(synthetic_actors=0)
        engine = WorldEngine(world, seed=5)
        results = run_arra_demo(engine)
        self.assertTrue(all("OK" in line for line in results))

        arra_events = [event for event in engine.ledger.events if "arra" in event.actor_ids]
        silver_fishing = [event for event in arra_events if event.event_type == "FISHED" and "silver_rod" in event.tags]
        necromancy = [event for event in arra_events if "necromancy" in event.tags]
        speech = [event for event in arra_events if event.event_type == "DIEGETIC_SPEECH"]

        self.assertEqual(3, len(silver_fishing))
        self.assertGreaterEqual(len(necromancy), 3)
        self.assertEqual(1, len(speech))
        self.assertGreaterEqual(world.actors["arra"].traits["necromantic_practice"], 0.20)

    def test_world_invariants_hold_after_long_run(self) -> None:
        world, _ = simulate(seed=101, actors=30, steps=500)
        world.validate_invariants()


if __name__ == "__main__":
    unittest.main()
