from __future__ import annotations

import unittest

from worldzero.archive import Archive
from worldzero.engine import WorldEngine
from worldzero.heralds import HeraldSystem, ReportPriority
from worldzero.ledger import EventLedger
from worldzero.models import Action, ActionType
from worldzero.seed import create_world


def make_system(day: int = 1):
    world = create_world(seed=42, synthetic_actors=0)
    world.game_minute = (day - 1) * 24 * 60
    ledger = EventLedger()
    archive = Archive()
    heralds = HeraldSystem(world, archive)
    heralds.attach(ledger)
    engine = WorldEngine(world, ledger, seed=43)
    return world, ledger, archive, heralds, engine


def death_decision(heralds: HeraldSystem, event_id: int):
    matches = [
        decision
        for decision in heralds.decisions
        if decision.event_id == event_id and decision.entity_id == "god_death"
    ]
    return matches[0] if matches else None


class DivinePresenceTests(unittest.TestCase):
    def test_same_graveyard_visit_changes_meaning_on_day_of_the_dead(self) -> None:
        _, normal_ledger, _, normal_heralds, normal_engine = make_system(day=1)
        normal_result = normal_engine.apply(
            Action("arra", ActionType.VISIT_SITE, target_id="old_ash_graveyard")
        )
        self.assertTrue(normal_result.ok)
        normal_event = normal_ledger.events[0]
        normal = death_decision(normal_heralds, normal_event.event_id)

        _, feast_ledger, _, feast_heralds, feast_engine = make_system(day=10)
        feast_result = feast_engine.apply(
            Action("arra", ActionType.VISIT_SITE, target_id="old_ash_graveyard")
        )
        self.assertTrue(feast_result.ok)
        feast_event = feast_ledger.events[0]
        feast = death_decision(feast_heralds, feast_event.event_id)

        self.assertEqual(normal_event.event_type, feast_event.event_type)
        self.assertEqual(normal_event.tags, feast_event.tags)
        self.assertIsNotNone(normal)
        self.assertIsNotNone(feast)
        assert normal is not None and feast is not None
        self.assertAlmostEqual(0.56, normal.presence)
        self.assertEqual(0.0, normal.contextual_salience)
        self.assertEqual(ReportPriority.ARCHIVE_ONLY, normal.priority)
        self.assertFalse(normal.actor_identity_known)

        self.assertAlmostEqual(1.0, feast.presence)
        self.assertAlmostEqual(0.72, feast.contextual_salience)
        self.assertEqual(ReportPriority.DIGEST, feast.priority)
        self.assertTrue(feast.actor_identity_known)
        self.assertGreater(feast.perception_score, normal.perception_score)
        self.assertGreater(feast.attention_score, normal.attention_score)
        self.assertEqual(1, len(feast_heralds.inbox("death").digest))

    def test_conscious_focus_makes_secret_mundane_visit_detailed(self) -> None:
        _, _, _, heralds, engine = make_system(day=1)
        heralds.presence.set_focus("god_death", "old_ash_graveyard", 1.00)
        result = engine.apply(
            Action(
                "arra",
                ActionType.VISIT_SITE,
                target_id="old_ash_graveyard",
                params={"secret": True},
            )
        )
        self.assertTrue(result.ok)
        decision = death_decision(heralds, result.event_id or -1)
        self.assertIsNotNone(decision)
        assert decision is not None
        self.assertAlmostEqual(1.0, decision.presence)
        self.assertAlmostEqual(1.00, decision.focus)
        self.assertEqual(ReportPriority.DIGEST, decision.priority)
        self.assertTrue(decision.actor_identity_known)
        self.assertEqual(("arra",), heralds.knowledge("death")[0].known_actor_ids)

    def test_maximum_presence_does_not_override_an_identity_veil(self) -> None:
        world, _, _, heralds, engine = make_system(day=1)
        world.actors["arra"].traits["divine_identity_veil"] = 1.0
        heralds.presence.set_focus("god_death", "old_ash_graveyard", 1.00)

        result = engine.apply(
            Action(
                "arra",
                ActionType.VISIT_SITE,
                target_id="old_ash_graveyard",
                params={"secret": True},
            )
        )
        self.assertTrue(result.ok)
        decision = death_decision(heralds, result.event_id or -1)
        self.assertIsNotNone(decision)
        assert decision is not None
        self.assertAlmostEqual(1.0, decision.presence)
        self.assertFalse(decision.actor_identity_known)
        knowledge = heralds.knowledge("death")[0]
        self.assertEqual((), knowledge.known_actor_ids)
        self.assertEqual((f"veil:event:{result.event_id}",), knowledge.veiled_subject_refs)

    def test_maximum_presence_can_still_miss_an_event_behind_event_opposition(self) -> None:
        world, _, archive, heralds, engine = make_system(day=1)
        world.actors["arra"].traits["divine_event_veil"] = 1.0
        heralds.presence.set_focus("god_death", "ash_valley", 1.00)

        result = engine.apply(
            Action(
                "arra",
                ActionType.SPEAK,
                params={"text": "A sentence spoken behind a metaphysical veil.", "audience": "public"},
            )
        )
        self.assertTrue(result.ok)
        self.assertEqual(1, len(archive.entries))
        self.assertIsNone(death_decision(heralds, result.event_id or -1))
        self.assertEqual((), heralds.knowledge("death"))

    def test_consciousness_budget_is_normalized_and_failed_overallocation_is_atomic(self) -> None:
        _, _, _, heralds, _ = make_system()
        self.assertAlmostEqual(1.0, heralds.presence.profiles["god_death"].consciousness_budget)
        heralds.presence.set_focus("god_death", "old_ash_graveyard", 0.60)
        heralds.presence.set_focus("god_death", "northwood", 0.40)
        with self.assertRaises(ValueError):
            heralds.presence.set_focus("god_death", "red_march", 0.01)
        self.assertEqual(
            {"old_ash_graveyard": 0.60, "northwood": 0.40},
            heralds.presence.focus_allocations("god_death"),
        )

    def test_high_local_presence_can_perceive_unrelated_private_action(self) -> None:
        _, _, _, heralds, engine = make_system(day=1)
        first = engine.apply(
            Action("arra", ActionType.SPEAK, params={"text": "A quiet mundane remark.", "audience": "private"})
        )
        self.assertTrue(first.ok)
        self.assertIsNone(death_decision(heralds, first.event_id or -1))

        heralds.presence.set_focus("god_death", "ash_valley", 0.70)
        second = engine.apply(
            Action("arra", ActionType.SPEAK, params={"text": "Another quiet mundane remark.", "audience": "private"})
        )
        self.assertTrue(second.ok)
        focused = death_decision(heralds, second.event_id or -1)
        self.assertIsNotNone(focused)
        assert focused is not None
        self.assertEqual(0.0, focused.relevance)
        self.assertGreaterEqual(focused.presence, 0.85)
        self.assertTrue(focused.actor_identity_known)
        self.assertIn("conscious focus", focused.reason)

    def test_destroyed_temple_weakens_a_consciousness_anchor(self) -> None:
        _, _, _, heralds, engine = make_system(day=1)
        before = heralds.presence.snapshot_at(
            "god_death", region_id="ash_valley", target_id="temple_last_gate"
        )
        result = engine.apply(Action("arra", ActionType.DESTROY_TEMPLE, target_id="temple_last_gate"))
        self.assertTrue(result.ok)
        after = heralds.presence.snapshot_at(
            "god_death", region_id="ash_valley", target_id="temple_last_gate"
        )
        self.assertGreater(before.anchor, after.anchor)
        self.assertGreater(before.total, after.total)


if __name__ == "__main__":
    unittest.main()
