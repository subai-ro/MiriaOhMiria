from __future__ import annotations

import unittest

from worldzero.affordances import GATE_TARGET, PhysicalActionRequest, PhysicalActionType
from worldzero.pilot_playable import (
    GALLERY_SITE,
    GATE_SITE,
    PILOT_I1_PREHISTORY_MINUTES,
    UPPER_REACH_SITE,
    create_pilot_i1_loop,
    render_player_journal,
    render_player_view,
)


def _run_branch(kind: str, *, seed: int = 91):
    loop = create_pilot_i1_loop(seed=seed)
    assert loop.inspect().ok
    if kind == "h0":
        assert loop.wait(60).ok
        assert loop.wait(1).ok
        assert loop.wait(360).ok
    else:
        assert loop.pray_to_death().ok
        assert loop.wait(60).ok
        if kind == "h1":
            assert loop.answer("The bank looked ordinary. I found nothing unusual.").ok
        elif kind == "h2":
            assert loop.answer(
                "I saw exposed bones in the bank, and I think the dead are calling."
            ).ok
        else:
            raise ValueError(kind)
        assert loop.wait(360).ok
    return loop


class PilotI1PlayableLoopTests(unittest.TestCase):
    def test_autonomous_prehistory_runs_before_any_player_event(self) -> None:
        loop = create_pilot_i1_loop()
        session = loop.session

        self.assertEqual(PILOT_I1_PREHISTORY_MINUTES, loop.started_minute)
        self.assertEqual(PILOT_I1_PREHISTORY_MINUTES, session.world.game_minute)
        self.assertEqual(4, len(session.world_process_runtime.runs))
        self.assertFalse(
            any("arra" in event.actor_ids for event in session.ledger.events)
        )
        self.assertEqual(0, session.projects.get("nereid_return_underpeak").created_minute)
        self.assertEqual(0, session.projects.get("trade_house_underpeak_route").created_minute)

    def test_navigation_rejects_invalid_route_atomically_and_moves_local_body(self) -> None:
        loop = create_pilot_i1_loop()
        before = (
            loop.session.world.game_minute,
            loop.navigation.current_site.site_id,
            len(loop.session.ledger.events),
        )
        rejected = loop.move("gallery")
        self.assertFalse(rejected.ok)
        self.assertEqual(
            before,
            (
                loop.session.world.game_minute,
                loop.navigation.current_site.site_id,
                len(loop.session.ledger.events),
            ),
        )

        moved = loop.move("gate")
        self.assertTrue(moved.ok)
        self.assertEqual(15, moved.minutes_elapsed)
        self.assertEqual(GATE_SITE, loop.navigation.current_site.site_id)
        self.assertEqual(before[0] + 15, loop.session.world.game_minute)
        self.assertEqual("LOCAL_SITE_TRAVERSED", loop.session.ledger.events[-1].event_type)

    def test_current_place_and_remote_command_targets_fail_clearly_and_atomically(self) -> None:
        loop = create_pilot_i1_loop()
        before = (
            loop.session.world.game_minute,
            loop.navigation.current_site.site_id,
            len(loop.session.ledger.events),
        )

        already_here = loop.execute("go bank")
        remote_look = loop.execute("look gallery")
        remote_inspection = loop.execute("inspect gallery")

        self.assertFalse(already_here.ok)
        self.assertIn("already at", already_here.message)
        self.assertFalse(remote_look.ok)
        self.assertIn("cannot see", remote_look.message)
        self.assertFalse(remote_inspection.ok)
        self.assertIn("must be at", remote_inspection.message)
        self.assertEqual(
            before,
            (
                loop.session.world.game_minute,
                loop.navigation.current_site.site_id,
                len(loop.session.ledger.events),
            ),
        )
        self.assertTrue(loop.execute("look bank").ok)

    def test_gate_silt_work_action_is_available_only_at_gate_and_has_effect(self) -> None:
        loop = create_pilot_i1_loop()
        before_remote = loop.session.hydrology.state.gate.debris_load

        blocked = loop.execute("work")
        self.assertFalse(blocked.ok)
        self.assertIn("gate", blocked.message.casefold())

        self.assertTrue(loop.move("gate").ok)
        before = loop.session.hydrology.state.gate.debris_load
        view = loop.player_view()
        self.assertIn("Work the gate's silt", view.available_actions)

        worked = loop.execute("work gate 0.6")
        self.assertTrue(worked.ok)
        self.assertIn("bounded tongue of silt", worked.message)
        self.assertLess(loop.session.hydrology.state.gate.debris_load, before)
        self.assertLess(loop.session.hydrology.state.gate.debris_load, before_remote)
        self.assertIn("Work the gate's silt", loop.player_view().available_actions)

        self.assertTrue(loop.execute("go bank").ok)
        self.assertNotIn("Work the gate's silt", loop.player_view().available_actions)
        self.assertFalse(loop.execute("work").ok)


    def test_player_map_command_renders_navigation_and_preserves_time(self) -> None:
        loop = create_pilot_i1_loop()
        before = loop.session.world.game_minute

        bank_map = loop.execute("map")
        self.assertTrue(bank_map.ok)
        self.assertIn("Status:", bank_map.message)
        self.assertIn("Nearby exits: The Sealed River Gate", bank_map.message)
        self.assertIn("Navigation map:", bank_map.message)
        self.assertIn("The Underpeak Reach*", bank_map.message)
        self.assertIn("The Sealed River Gate", bank_map.message)
        self.assertEqual(before, loop.session.world.game_minute)

        self.assertTrue(loop.move("gate").ok)
        gate_map = loop.execute("v")
        self.assertTrue(gate_map.ok)
        self.assertIn("Nearby exits: The Underpeak Reach, The Old Gallery", gate_map.message)
        self.assertIn("The Sealed River Gate*", gate_map.message)
        self.assertIn("Gate debris:", gate_map.message)
        self.assertEqual(before + 15, loop.session.world.game_minute)

    def test_help_lists_probe_and_settle(self) -> None:
        loop = create_pilot_i1_loop()
        help_message = loop.execute("help").message
        self.assertIn("probe", help_message)
        self.assertIn("settle", help_message)


    def test_probe_answer_settle_flow_is_explicit(self) -> None:
        loop = create_pilot_i1_loop()
        self.assertTrue(loop.pray_to_death().ok)
        start_minute = loop.session.world.game_minute
        self.assertTrue(loop.wait(60).ok)

        self.assertEqual(start_minute + 60, loop.session.world.game_minute)

        probe = loop.execute("probe")
        self.assertTrue(probe.ok)
        self.assertIn("Reply with", probe.message)

        blocked_settle = loop.execute("settle")
        self.assertFalse(blocked_settle.ok)
        self.assertIn("probe", blocked_settle.message.casefold())

        self.assertTrue(loop.answer("I saw exposed bones in the bank, and I think the dead are calling.").ok)

        before = loop.session.world.game_minute
        settled = loop.execute("settle 30")
        self.assertTrue(settled.ok)
        self.assertEqual(before + 30, loop.session.world.game_minute)

        cleared_probe = loop.execute("probe")
        self.assertFalse(cleared_probe.ok)


    def test_player_hud_command_renders_world_state_snapshot(self) -> None:
        loop = create_pilot_i1_loop()
        before = loop.session.world.game_minute

        hud = loop.execute("hud")
        self.assertTrue(hud.ok)
        self.assertIn("HUD:", hud.message)
        self.assertIn(f"Minute: {before}", hud.message)
        self.assertIn("Projects:", hud.message)
        self.assertIn("nereid_return_underpeak", hud.message)
        self.assertIn("trade_house_underpeak_route", hud.message)
        self.assertIn("Unanswered probe:", hud.message)
        self.assertEqual(before, loop.session.world.game_minute)

        self.assertIn("HUD:", render_player_view(loop.player_view()))



    def test_journal_separates_owned_observations_received_words_and_own_replies(self) -> None:
        loop = create_pilot_i1_loop()
        self.assertTrue(loop.inspect().ok)
        self.assertTrue(loop.pray_to_death().ok)
        self.assertTrue(loop.wait(60).ok)
        reply = "I want to lead your armies against the Cities of Light."
        self.assertTrue(loop.answer(reply).ok)

        view = loop.player_view()
        journal = render_player_journal(view)
        self.assertEqual((reply,), view.spoken_words)
        self.assertIn("Observations:", journal)
        self.assertIn("Words received:", journal)
        self.assertIn("Your replies:", journal)
        self.assertIn(reply, journal)
        self.assertEqual(journal, loop.execute("journal").message)

    def test_i1_presents_natural_gate_and_gallery_observation_prose(self) -> None:
        loop = create_pilot_i1_loop()
        self.assertTrue(loop.move("gate").ok)
        gate = loop.inspect()
        self.assertTrue(gate.ok)
        self.assertIn("The sluice appears", gate.message)
        self.assertIn("the outflow is", gate.message)

        self.assertTrue(loop.move("gallery").ok)
        gallery = loop.inspect()
        self.assertTrue(gallery.ok)
        self.assertEqual(
            "The gallery is heavily blocked and damp. The route is blocked.",
            gallery.message,
        )
        self.assertNotIn("the route blocked", gallery.message.casefold())

    def test_player_view_uses_owned_observations_and_visible_manifestations_only(self) -> None:
        loop = create_pilot_i1_loop()
        self.assertTrue(loop.move("gate").ok)
        foreign = loop.session.perform(
            PhysicalActionRequest(
                "nereid_01",
                PhysicalActionType.INSPECT_GATE,
                GATE_TARGET,
            )
        )
        self.assertTrue(foreign.ok)
        self.assertIsNotNone(foreign.percept)

        view = loop.player_view()
        self.assertEqual((), view.observations)
        self.assertEqual(("Trade House surveyors",), view.visible_subjects)
        serialized = str(view.as_dict()).casefold()
        for forbidden in (
            "echo",
            "impulse",
            "intensity",
            "source",
            "hydrology",
            "ledger",
            "state_hash",
            "god_death",
            "underpeak_gate_forebay",
        ):
            self.assertNotIn(forbidden, serialized)

    def test_three_places_are_inspected_through_existing_affordance_bridge(self) -> None:
        loop = create_pilot_i1_loop()
        self.assertTrue(loop.inspect().ok)
        self.assertTrue(loop.move("gate").ok)
        self.assertTrue(loop.inspect().ok)
        self.assertTrue(loop.move("gallery").ok)
        self.assertTrue(loop.inspect().ok)

        view = loop.player_view()
        self.assertEqual(GALLERY_SITE, loop.navigation.current_site.site_id)
        self.assertEqual(3, len(view.observations))
        self.assertEqual(3, len(loop.session.affordances.perceptions.for_subject("arra")))
        self.assertEqual(
            3,
            len(
                [
                    item
                    for item in loop.session.affordances.action_traces
                    if item.subject_id == "arra"
                    and item.action_type
                    in {
                        PhysicalActionType.INSPECT_BANK,
                        PhysicalActionType.INSPECT_GATE,
                        PhysicalActionType.SURVEY_GALLERY,
                    }
                ]
            ),
        )

    def test_prayer_creates_a_visible_answer_affordance(self) -> None:
        loop = create_pilot_i1_loop()
        self.assertTrue(loop.pray_to_death().ok)
        self.assertTrue(loop.wait(60).ok)

        before_answer = loop.player_view()
        self.assertEqual(1, len(before_answer.received_words))
        self.assertIn("Answer the grave-cold voice", before_answer.available_actions)
        self.assertTrue(loop.answer("The bank looked ordinary. I found nothing unusual.").ok)
        after_answer = loop.player_view()
        self.assertNotIn("Answer the grave-cold voice", after_answer.available_actions)
        self.assertEqual(1, len(after_answer.received_words))

    def test_false_alarm_changes_death_behavior_without_becoming_truth(self) -> None:
        loop = create_pilot_i1_loop()
        self.assertTrue(loop.pray_to_death().ok)
        self.assertTrue(loop.wait(60).ok)
        response = loop.answer(
            "I saw exposed bones in the bank, and I think the dead are calling."
        )
        self.assertTrue(response.ok)

        manifestations = loop.session.divine_runtime.gateway.manifestations_for("arra")
        self.assertEqual(2, len(manifestations))
        self.assertIn("heard, not proven", manifestations[-1].message)
        self.assertEqual(0.0, loop.session.hydrology.state.burial_bank.exposure_fraction)
        omen_event = next(
            event
            for event in reversed(loop.session.ledger.events)
            if event.event_type == "DIVINE_OMEN_SENT"
        )
        response_event = next(
            event
            for event in reversed(loop.session.ledger.events)
            if event.event_type == "DIEGETIC_SPEECH"
        )
        self.assertEqual((response_event.event_id,), omen_event.causal_parent_ids)
        self.assertNotIn("verified", response_event.data)
        self.assertNotIn("truth", response_event.data)

    def test_h0_h1_h2_have_visible_durable_and_causal_differences(self) -> None:
        h0 = _run_branch("h0")
        h1 = _run_branch("h1")
        h2 = _run_branch("h2")

        self.assertEqual(h0.session.world.game_minute, h1.session.world.game_minute)
        self.assertEqual(h1.session.world.game_minute, h2.session.world.game_minute)
        self.assertEqual(0, len(h0.player_view().received_words))
        self.assertEqual(1, len(h1.player_view().received_words))
        self.assertEqual(2, len(h2.player_view().received_words))
        self.assertEqual(2, len(h2.session.divine_runtime.gateway.manifestations_for("arra")))
        self.assertEqual(0.0, h2.session.hydrology.state.burial_bank.exposure_fraction)
        for loop in (h0, h1, h2):
            self.assertEqual("active", loop.session.projects.get("nereid_return_underpeak").status.value)
            self.assertEqual("active", loop.session.projects.get("trade_house_underpeak_route").status.value)

    def test_identical_i1_history_is_deterministic(self) -> None:
        left = _run_branch("h2", seed=123)
        right = _run_branch("h2", seed=123)

        self.assertEqual(
            tuple(event.as_dict() for event in left.session.ledger.events),
            tuple(event.as_dict() for event in right.session.ledger.events),
        )
        self.assertEqual(left.player_view(), right.player_view())
        self.assertEqual(
            left.session.divine_runtime.agent("death").thoughts,
            right.session.divine_runtime.agent("death").thoughts,
        )

    def test_rendered_view_and_history_contain_no_story_director_contract(self) -> None:
        loop = _run_branch("h2")
        rendered = render_player_view(loop.player_view()).casefold()
        for forbidden in ("quest", "ending", "story director", "state_hash"):
            self.assertNotIn(forbidden, rendered)
        self.assertFalse(
            any(
                token in event.event_type
                for event in loop.session.ledger.events
                for token in ("QUEST", "ENDING", "STORY_DIRECTOR")
            )
        )


if __name__ == "__main__":
    unittest.main()
