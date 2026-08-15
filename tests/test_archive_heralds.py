from __future__ import annotations

import unittest

from worldzero.archive import Archive
from worldzero.engine import WorldEngine
from worldzero.heralds import HeraldSystem, ReportPriority
from worldzero.ledger import EventLedger
from worldzero.models import Action, ActionType
from worldzero.seed import create_world
from worldzero.simulation import Simulation


def make_system(actors: int = 9):
    world = create_world(seed=42, synthetic_actors=actors)
    ledger = EventLedger()
    archive = Archive()
    heralds = HeraldSystem(world, archive)
    heralds.attach(ledger)
    engine = WorldEngine(world, ledger, seed=43)
    return world, ledger, archive, heralds, engine


class ArchiveHeraldTests(unittest.TestCase):
    def test_same_seed_produces_same_archive_and_routing(self) -> None:
        def run_once():
            world, ledger, archive, heralds, engine = make_system(actors=12)
            Simulation(engine, minutes_per_step=10, seed=44).run(80)
            return (
                [entry.as_dict() for entry in archive.entries],
                [
                    (
                        decision.event_id,
                        decision.entity_id,
                        decision.priority.value,
                        decision.attention_score,
                        decision.actor_identity_known,
                    )
                    for decision in heralds.decisions
                ],
                [
                    (report.entity_id, report.priority.value, report.summary, report.known_actor_ids)
                    for inbox in heralds.inboxes.values()
                    for report in inbox.all_reports
                ],
                ledger.listener_errors,
            )

        self.assertEqual(run_once(), run_once())

    def test_public_temple_destruction_wakes_death_and_identifies_actor(self) -> None:
        _, ledger, _, heralds, engine = make_system()
        result = engine.apply(Action("arra", ActionType.DESTROY_TEMPLE, target_id="temple_last_gate"))
        self.assertTrue(result.ok)

        inbox = heralds.inbox("death")
        self.assertEqual(1, len(inbox.immediate))
        report = inbox.immediate[0]
        self.assertEqual(ReportPriority.IMMEDIATE, report.priority)
        self.assertEqual(("arra",), report.known_actor_ids)
        self.assertIn("Arra", report.summary)
        self.assertEqual((), ledger.listener_errors)

    def test_secret_temple_destruction_is_known_but_actor_is_not(self) -> None:
        _, ledger, archive, heralds, engine = make_system()
        result = engine.apply(
            Action(
                "arra",
                ActionType.DESTROY_TEMPLE,
                target_id="temple_last_gate",
                params={"secret": True},
            )
        )
        self.assertTrue(result.ok)

        report = heralds.inbox("death").immediate[0]
        self.assertEqual((), report.known_actor_ids)
        self.assertIn("unknown", report.summary.lower())
        self.assertNotIn("Arra", report.summary)

        # The objective Archive keeps provenance; the subjective report does not leak it.
        self.assertEqual(("arra",), archive.entries[0].actor_ids)
        death_knowledge = heralds.knowledge("death")
        self.assertEqual(1, len(death_knowledge))
        self.assertEqual((), death_knowledge[0].known_actor_ids)
        self.assertNotIn("Arra", death_knowledge[0].summary)
        self.assertEqual((), ledger.listener_errors)

    def test_public_actor_identity_survives_in_subjective_knowledge(self) -> None:
        _, _, _, heralds, engine = make_system()
        self.assertTrue(engine.apply(Action("arra", ActionType.DESTROY_TEMPLE, target_id="temple_last_gate")).ok)
        matches = heralds.knowledge("death", actor_id="arra")
        self.assertEqual(1, len(matches))
        self.assertIn("Arra", matches[0].summary)

    def test_single_wood_harvest_does_not_bother_nature(self) -> None:
        _, _, _, heralds, engine = make_system()
        self.assertTrue(engine.apply(Action("arra", ActionType.TRAVEL, target_id="northwood")).ok)
        self.assertTrue(engine.apply(Action("arra", ActionType.HARVEST_WOOD)).ok)
        inbox = heralds.inbox("nature")
        self.assertEqual(0, len(inbox.immediate))
        self.assertEqual(0, len(inbox.digest))

    def test_single_necromancy_study_is_archived_without_digest_noise(self) -> None:
        _, _, _, heralds, engine = make_system()
        self.assertTrue(
            engine.apply(Action("arra", ActionType.STUDY_NECROMANCY, target_id="old_ash_graveyard")).ok
        )
        inbox = heralds.inbox("death")
        self.assertEqual(0, len(inbox.immediate))
        self.assertEqual(0, len(inbox.digest))
        decisions = [
            decision
            for decision in heralds.decisions
            if decision.event_id == 1 and decision.entity_id == "god_death"
        ]
        self.assertEqual(1, len(decisions))
        self.assertEqual(ReportPriority.ARCHIVE_ONLY, decisions[0].priority)

    def test_many_weak_logging_events_become_one_trend(self) -> None:
        _, ledger, archive, heralds, engine = make_system()
        self.assertTrue(engine.apply(Action("arra", ActionType.TRAVEL, target_id="northwood")).ok)
        for _ in range(12):
            self.assertTrue(engine.apply(Action("arra", ActionType.HARVEST_WOOD)).ok)

        inbox = heralds.inbox("nature")
        trend_reports = [report for report in inbox.digest if "aggregated trend" in report.reason]
        self.assertEqual(1, len(trend_reports))
        self.assertEqual(12, len(trend_reports[0].source_event_ids))
        self.assertIn("logging pressure", trend_reports[0].summary)
        self.assertTrue(any(entry.event_type == "TREND_WOOD_HARVESTED" for entry in archive.entries))
        self.assertEqual((), ledger.listener_errors)

    def test_prayers_are_batched_instead_of_waking_god_one_by_one(self) -> None:
        _, _, _, heralds, engine = make_system()
        for _ in range(15):
            self.assertTrue(engine.apply(Action("arra", ActionType.PRAY, params={"deity": "trade"})).ok)

        inbox = heralds.inbox("trade")
        self.assertEqual(0, len(inbox.immediate))
        self.assertEqual(1, len(inbox.digest))
        self.assertEqual(15, len(inbox.digest[0].source_event_ids))

    def test_archive_find_preserves_event_provenance(self) -> None:
        _, _, archive, _, engine = make_system()
        engine.apply(Action("arra", ActionType.TRAVEL, target_id="northwood"))
        engine.apply(Action("arra", ActionType.FISH, target_id="lake_mirror", params={"tool": "silver_rod"}))
        matches = archive.find(tags=("silver_rod",), actor_id="arra")
        self.assertEqual(1, len(matches))
        self.assertEqual("FISHED", matches[0].event_type)
        self.assertEqual(1, len(matches[0].source_event_ids))


if __name__ == "__main__":
    unittest.main()
