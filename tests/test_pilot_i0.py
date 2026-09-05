from __future__ import annotations

import unittest

from worldzero.affordances import PhysicalActionType
from worldzero.models import Action, ActionType
from worldzero.pilot import (
    DEATH_PROJECT_ID,
    AshValleyDeathBrain,
    create_pilot_i0_session,
    inspect_arra_bank,
)
from worldzero.processes.aqueous_echo import EchoSenseRequest


class PilotI0IntegrationTests(unittest.TestCase):
    def test_composition_reuses_authoritative_world_ledger_and_evidence_stores(self) -> None:
        session = create_pilot_i0_session()

        self.assertIs(session.world, session.engine.world)
        self.assertIs(session.world, session.hydrology.world)
        self.assertIs(session.world, session.aqueous_echo.world)
        self.assertIs(session.world, session.divine_runtime.gateway.world)
        self.assertIs(session.ledger, session.engine.ledger)
        self.assertIs(session.ledger, session.hydrology.ledger)
        self.assertIs(session.ledger, session.aqueous_echo.ledger)
        self.assertIs(session.ledger, session.divine_runtime.gateway.ledger)
        self.assertIs(session.ledger, session.project_trace.ledger)
        self.assertIs(session.affordances.perceptions, session.aqueous_echo_sensing.perceptions)
        self.assertEqual(session.world.game_minute, session.clock.game_minute)
        self.assertIsInstance(session.divine_runtime.agent("death").brain, AshValleyDeathBrain)
        self.assertEqual("god_death", session.projects.get(DEATH_PROJECT_ID).owner_id)

    def test_arra_has_no_water_sense_and_only_gets_ordinary_bank_cues(self) -> None:
        session = create_pilot_i0_session()
        arra = next(item for item in session.affordances.subjects if item.subject_id == "arra")
        self.assertEqual(("sight",), arra.faculties)
        self.assertNotIn("water_sense", arra.faculties)

        inspection = inspect_arra_bank(session)
        self.assertTrue(inspection.ok)
        self.assertIsNotNone(inspection.percept)
        assert inspection.percept is not None
        self.assertEqual(
            {"surface_signs", "visible_stability"},
            set(inspection.percept.cues),
        )
        player_text = f"{inspection.percept.summary} {inspection.percept.cues}".casefold()
        for forbidden in ("echo", "impulse", "intensity", "source"):
            self.assertNotIn(forbidden, player_text)

        before = (
            session.world.game_minute,
            session.aqueous_echo.state.state_hash(),
            len(session.ledger.events),
            len(session.affordances.perceptions.for_subject("arra")),
        )
        rejected = session.sense_echo(EchoSenseRequest("arra", "underpeak_upper_reach"))
        self.assertFalse(rejected.ok)
        self.assertEqual(
            before,
            (
                session.world.game_minute,
                session.aqueous_echo.state.state_hash(),
                len(session.ledger.events),
                len(session.affordances.perceptions.for_subject("arra")),
            ),
        )

    def test_lawful_prayer_can_lead_to_one_bounded_probe_without_bank_truth(self) -> None:
        session = create_pilot_i0_session()
        inspection = inspect_arra_bank(session)
        self.assertTrue(inspection.ok)
        assert inspection.event_id is not None

        prayer = session.apply(Action("arra", ActionType.PRAY, params={"deity": "death"}))
        self.assertTrue(prayer.ok)
        assert prayer.event_id is not None
        session.advance(60)

        death_knowledge = session.heralds.knowledge("death")
        prayer_knowledge = tuple(
            item for item in death_knowledge if item.event_type == "PRAYER_OFFERED"
        )
        self.assertEqual(1, len(prayer_knowledge))
        self.assertEqual(("arra",), prayer_knowledge[0].known_actor_ids)
        self.assertEqual((prayer.event_id,), prayer_knowledge[0].source_event_ids)
        self.assertFalse(
            any(inspection.event_id in item.source_event_ids for item in death_knowledge)
        )

        probes = session.divine_runtime.gateway.probes_for("god_death")
        self.assertEqual(1, len(probes))
        self.assertEqual((prayer.event_id,), probes[0].causal_event_ids)
        probe_event = session.ledger.events[probes[0].manifestation_event_id - 1]
        self.assertEqual("DIVINE_PROBE_MANIFESTED", probe_event.event_type)
        self.assertEqual((prayer.event_id,), probe_event.causal_parent_ids)

        subjective_payload = " ".join(
            " ".join(
                (
                    item.event_type,
                    item.location_id,
                    item.summary,
                    *item.tags,
                )
            )
            for item in death_knowledge
        ).casefold()
        for forbidden in (
            "underpeak_burial_shelf",
            "exposure_fraction",
            "cover_depth_equiv",
            "state_hash",
            "aqueous",
            "silver echo",
            "ordinary_bank",
        ):
            self.assertNotIn(forbidden, subjective_payload)
        self.assertEqual((), session.clock.errors)

    def test_event_veil_can_make_death_miss_the_prayer_entirely(self) -> None:
        session = create_pilot_i0_session()
        session.world.actors["arra"].traits["divine_event_veil"] = 1.0

        prayer = session.apply(Action("arra", ActionType.PRAY, params={"deity": "death"}))
        self.assertTrue(prayer.ok)
        session.advance(60)

        self.assertEqual((), session.heralds.knowledge("death"))
        self.assertEqual((), session.divine_runtime.gateway.probes_for("god_death"))
        self.assertEqual(1, len(session.archive.entries))

    def test_mortal_probe_response_is_subjective_testimony_not_verified_truth(self) -> None:
        session = create_pilot_i0_session()
        prayer = session.apply(Action("arra", ActionType.PRAY, params={"deity": "death"}))
        self.assertTrue(prayer.ok)
        session.advance(60)
        probe = session.divine_runtime.gateway.probes_for("god_death")[0]

        response = session.apply(
            Action(
                "arra",
                ActionType.SPEAK,
                params={
                    "text": "I saw exposed bones in the bank, and I think the dead are calling.",
                    "audience": "private",
                    "response_to_probe_ref": probe.probe_ref,
                },
            )
        )
        self.assertTrue(response.ok)
        session.advance(1)

        response_knowledge = next(
            item
            for item in session.heralds.knowledge("death")
            if response.event_id in item.source_event_ids
        )
        self.assertEqual(probe.probe_ref, response_knowledge.response_to_probe_ref)
        self.assertIn("exposed bones", response_knowledge.summary)
        self.assertEqual(0.0, session.hydrology.state.burial_bank.exposure_fraction)
        response_event = session.ledger.events[(response.event_id or 1) - 1]
        self.assertNotIn("verified", response_event.data)
        self.assertNotIn("truth", response_event.data)
        self.assertEqual(
            "response_perceived",
            session.divine_runtime.agent("death").thoughts[-1].probe_memories[0].status.value,
        )

    def test_identical_state_seed_intent_and_history_resolve_identically(self) -> None:
        left = create_pilot_i0_session(seed=77)
        right = create_pilot_i0_session(seed=77)

        for session in (left, right):
            inspection = inspect_arra_bank(session)
            self.assertTrue(inspection.ok)
            prayer = session.apply(
                Action("arra", ActionType.PRAY, params={"deity": "death"})
            )
            self.assertTrue(prayer.ok)
            session.advance(60)

        self.assertEqual(
            tuple(event.as_dict() for event in left.ledger.events),
            tuple(event.as_dict() for event in right.ledger.events),
        )
        self.assertEqual(
            left.divine_runtime.gateway.probes_for("god_death"),
            right.divine_runtime.gateway.probes_for("god_death"),
        )
        self.assertEqual(
            left.divine_runtime.agent("death").thoughts,
            right.divine_runtime.agent("death").thoughts,
        )
        self.assertEqual(
            left.hydrology.state.state_hash(),
            right.hydrology.state.state_hash(),
        )

    def test_arra_seed_capability_is_inspection_only(self) -> None:
        session = create_pilot_i0_session()
        arra = next(item for item in session.affordances.subjects if item.subject_id == "arra")
        self.assertGreater(arra.capability(PhysicalActionType.INSPECT_BANK), 0.0)
        self.assertEqual(0.0, arra.capability(PhysicalActionType.REINFORCE_BANK))


if __name__ == "__main__":
    unittest.main()
