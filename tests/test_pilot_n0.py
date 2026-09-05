from __future__ import annotations

import unittest
from unittest.mock import patch

from worldzero.affordances import GATE_SITE, GATE_TARGET, PhysicalActionRequest, PhysicalActionType
from worldzero.models import Action, ActionType
from worldzero.pilot_playable import create_pilot_i1_loop
from worldzero.processes.aqueous_echo import EchoSenseRequest
from worldzero.project_runtime import IntentResolution, ProjectDecision, ProjectIntent
from worldzero.projects import AttemptOutcome, ProjectStatus


NEREID_PROJECT = "nereid_return_underpeak"


class LabClockMind:
    """Scheduling double only, never canonical cognition or a demo policy."""

    def __init__(self, action=None, *, delay=360, observe=None):
        self.action = action
        self.delay = delay
        self.observe = observe
        self.minutes = []

    def decide(self, percept):
        self.minutes.append(percept.game_minute)
        if self.observe:
            self.observe(percept)
        intents = ()
        if len(self.minutes) == 1 and self.action is not None:
            intents = (ProjectIntent("lab.clock.physical", (GATE_TARGET,), {"verb": self.action}),)
        return ProjectDecision(
            strategy="Lab scheduling probe; no canonical character behavior",
            subjective_evidence_refs=(),
            next_review_minute=percept.game_minute + self.delay,
            intents=intents,
        )


class LabPhysicalResolver:
    """Test request adapter; all physical results still come from D.2.2."""

    rule_id = "lab.clock.existing_physics"

    def __init__(self, session):
        self.session = session

    def resolve(self, *, project, intent, game_minute):
        result = self.session.perform(PhysicalActionRequest(
            project.owner_id, PhysicalActionType(intent.params["verb"]),
            intent.target_refs[0], params={"effort": 1.0},
        ))
        return IntentResolution(
            ok=result.ok,
            outcome=AttemptOutcome(result.outcome.value) if result.ok else AttemptOutcome.BLOCKED,
            message=result.message,
            result_event_ids=(result.event_id,) if result.event_id is not None else (),
        )


def install_lab_mind(loop, mind, *, due=300, project_id=NEREID_PROJECT):
    session = loop.session
    project = session.projects.get(project_id)
    session.projects.reconsider(
        project_id, game_minute=session.world.game_minute,
        current_strategy=project.current_strategy, next_review_minute=due,
    )
    session.project_runtime.register_mind(project.owner_id, mind)
    session.project_runtime.register_resolver("lab.clock.physical", LabPhysicalResolver(session))


class PilotN0SchedulingTests(unittest.TestCase):
    def loop(self):
        return create_pilot_i1_loop(prehistory_minutes=0, serial_actions=True)

    def test_opt_in_reuses_one_session_and_registers_no_production_mind(self):
        loop = self.loop()
        session = loop.session
        self.assertTrue(session.clock.serial_actions)
        self.assertIs(session.world, session.clock.world)
        self.assertIs(session.world, session.affordances.world)
        self.assertIs(session.project_runtime, session.clock.project_runtime)
        self.assertIs(session.projects, session.project_runtime.projects)
        self.assertIs(session.ledger, session.project_trace.ledger)
        self.assertIs(session.affordances.perceptions, session.aqueous_echo_sensing.perceptions)
        self.assertIsNone(session.project_runtime.next_review_minute)
        session.advance(720)
        self.assertFalse(session.project_trace.decisions)
        self.assertFalse(session.ledger.events)
        self.assertEqual(4, len(session.world_process_runtime.runs))

    def test_timed_attempt_commits_before_project_or_divine_reentry(self):
        loop = self.loop()
        session = loop.session
        mind = LabClockMind(PhysicalActionType.SHIFT_LOCAL_SILT.value)
        install_lab_mind(loop, mind)
        nested_reviews = []
        divine_observations = []

        def during_advance(minute):
            if minute == 480:
                nested_reviews.append(session.project_runtime.tick(minute))

        session.world.subscribe_time_advance(during_advance)
        real_tick = session.divine_runtime.tick

        def divine_probe():
            divine_observations.append((session.world.game_minute, len(session.project_trace.resolutions)))
            real_tick()

        with patch.object(session.divine_runtime, "tick", side_effect=divine_probe):
            session.advance(301)
        self.assertEqual([300], mind.minutes)
        self.assertEqual([()], nested_reviews)
        self.assertEqual([(480, 1)], divine_observations)
        self.assertEqual(480, session.world.game_minute)
        action = session.affordances.action_traces[0]
        self.assertEqual((300, 480), (action.start_minute, action.end_minute))
        self.assertEqual(300, session.project_trace.decisions[0].game_minute)
        self.assertEqual(480, session.project_trace.resolutions[0].game_minute)
        project = session.projects.get(NEREID_PROJECT)
        self.assertEqual(480, project.attempt_history[0].game_minute)
        self.assertEqual(ProjectStatus.ACTIVE, project.status)
        self.assertGreater(project.next_review_minute, 480)
        self.assertEqual((), session.affordances.perceptions.for_subject("nereid_01"))
        self.assertEqual(
            [("silver_thread_hydrology", 360), ("silver_thread_water_echo", 360)],
            [(item.process_id, item.game_minute) for item in session.world_process_runtime.runs],
        )
        self.assertFalse(session.clock.errors)
        self.assertFalse(session.project_runtime.errors)

    def test_long_no_player_advance_uses_contemporary_review_times(self):
        loop = self.loop()
        session = loop.session
        snapshots = []
        # Creator-side assertion probe, not information supplied to the double.
        mind = LabClockMind(
            PhysicalActionType.INSPECT_GATE.value,
            observe=lambda p: snapshots.append((p.game_minute, tuple(
                item.game_minute for item in session.affordances.subject_view("nereid_01").percepts
            ))),
        )
        install_lab_mind(loop, mind)
        session.advance(1440)
        self.assertEqual([300, 660, 1020, 1380], mind.minutes)
        self.assertEqual((300, ()), snapshots[0])
        self.assertEqual((660, (345,)), snapshots[1])
        self.assertTrue(all(time <= now for now, times in snapshots for time in times))
        self.assertEqual(1440, session.world.game_minute)
        self.assertEqual(8, len(session.world_process_runtime.runs))
        self.assertFalse(any("arra" in item.actor_ids for item in session.ledger.events))

    def test_other_due_project_sees_actual_completion_not_old_tick_minute(self):
        loop = self.loop()
        session = loop.session
        first = LabClockMind(PhysicalActionType.SHIFT_LOCAL_SILT.value)
        observed = []
        second = LabClockMind(observe=lambda p: observed.append(len(session.project_trace.resolutions)))
        install_lab_mind(loop, first)
        install_lab_mind(loop, second, project_id="trade_house_underpeak_route")
        # A direct nested tick must not run the other due project mid-work either.
        session.world.subscribe_time_advance(
            lambda minute: session.project_runtime.tick(minute) if minute == 480 else None
        )
        session.advance(301)
        self.assertEqual([300], first.minutes)
        self.assertEqual([480], second.minutes)
        self.assertEqual([1], observed)
        self.assertEqual([300, 480], [item.game_minute for item in session.project_trace.decisions])

    def test_movement_commits_location_and_event_before_due_mind(self):
        for direct in (False, True):
            with self.subTest(direct=direct):
                loop = self.loop()
                observed = []
                mind = LabClockMind(PhysicalActionType.SHIFT_LOCAL_SILT.value, observe=lambda p: observed.append((
                    p.game_minute, loop.navigation.current_site.site_id,
                    loop.session.ledger.events[-1].event_type,
                )))
                install_lab_mind(loop, mind, due=1)
                result = loop.navigation.move(GATE_SITE) if direct else loop.move("gate")
                self.assertTrue(result.ok)
                self.assertEqual([(15, GATE_SITE, "LOCAL_SITE_TRAVERSED")], observed)
                self.assertEqual(195, result.duration_minutes if direct else result.minutes_elapsed)
                movement = loop.session.ledger.events[0]
                self.assertEqual(15, movement.game_minute)
                self.assertEqual(15, movement.data["duration_minutes"])

    def test_invalid_commands_and_views_do_not_drain_due_autonomy(self):
        loop = self.loop()
        session = loop.session
        mind = LabClockMind(PhysicalActionType.SHIFT_LOCAL_SILT.value)
        install_lab_mind(loop, mind, due=1)
        session.world.advance(1)  # Test fixture leaves one review overdue.
        for command in ("go bank", "go gallery", "look gate", "inspect gate", "answer nope", "wait 0", "???"):
            self.assertFalse(loop.execute(command).ok, command)
        for command in ("help", "look", "journal"):
            self.assertTrue(loop.execute(command).ok, command)
        loop.player_view()
        self.assertFalse(session.apply(Action("missing", ActionType.PRAY)).ok)
        self.assertFalse(session.sense_echo(EchoSenseRequest("arra", "underpeak_upper_reach")).ok)
        self.assertFalse(session.perform(PhysicalActionRequest(
            "arra", PhysicalActionType.INSPECT_GATE, GATE_TARGET,
        )).ok)
        self.assertEqual(1, session.world.game_minute)
        self.assertEqual([], mind.minutes)
        self.assertFalse(session.ledger.events)
        self.assertFalse(session.project_trace.decisions)

    def test_inspection_commits_private_percept_before_any_due_review(self):
        loop = self.loop()
        observed = []
        mind = LabClockMind(observe=lambda p: observed.append((
            p.game_minute, len(loop.session.affordances.perceptions.for_subject("arra")),
            loop.session.ledger.events[-1].event_type,
        )))
        install_lab_mind(loop, mind, due=1)
        result = loop.inspect()
        self.assertEqual([(60, 1, "LOCAL_INSPECTION_PERFORMED")], observed)
        self.assertEqual(60, result.minutes_elapsed)

    def test_prayer_and_answer_are_complete_before_due_review(self):
        loop = self.loop()
        session = loop.session
        observed = []
        mind = LabClockMind(observe=lambda p: observed.append((
            p.game_minute, session.ledger.events[-1].event_type,
        )))
        install_lab_mind(loop, mind, due=1)
        session.world.advance(1)
        self.assertTrue(loop.pray_to_death().ok)
        self.assertEqual([(1, "PRAYER_OFFERED")], observed)
        # The frozen divine runtime still controls when the prayer is noticed.
        session.advance(60)
        self.assertTrue(session.divine_runtime.gateway.probes_for("god_death"))
        reply_minute = session.world.game_minute + 1
        install_lab_mind(loop, mind, due=reply_minute)
        reply = loop.answer("I saw an ordinary bank.")
        self.assertTrue(reply.ok)
        self.assertEqual((reply_minute, "DIEGETIC_SPEECH"), observed[-1])
        self.assertEqual(1, reply.minutes_elapsed)

    def test_wait_counts_autonomous_work_inside_deadline_without_double_counting(self):
        loop = self.loop()
        mind = LabClockMind(PhysicalActionType.SHIFT_LOCAL_SILT.value)
        install_lab_mind(loop, mind)
        result = loop.wait(301)
        self.assertEqual(480, result.minutes_elapsed)
        self.assertIn("480 minutes", result.message)
        self.assertEqual(480, loop.session.world.game_minute)
        other = self.loop()
        install_lab_mind(other, LabClockMind(PhysicalActionType.SHIFT_LOCAL_SILT.value))
        other.session.advance(1000)
        self.assertEqual(1000, other.session.world.game_minute)

    def test_blocked_work_preserves_project_without_spending_action_time(self):
        loop = self.loop()
        session = loop.session
        body = next(item for item in session.affordances.subjects if item.subject_id == "nereid_01")
        body.resources["effort"] = 0.0
        mind = LabClockMind(PhysicalActionType.SHIFT_LOCAL_SILT.value)
        install_lab_mind(loop, mind)
        session.advance(301)
        project = session.projects.get(NEREID_PROJECT)
        self.assertEqual(ProjectStatus.ACTIVE, project.status)
        self.assertEqual(AttemptOutcome.BLOCKED, project.attempt_history[0].outcome)
        self.assertEqual(300, project.attempt_history[0].game_minute)
        self.assertEqual(301, session.world.game_minute)
        self.assertFalse(session.ledger.events)
        self.assertFalse(session.affordances.perceptions.for_subject("nereid_01"))

    def test_none_and_failed_decisions_cannot_spin_or_rewrite_project(self):
        for fail in (False, True):
            with self.subTest(fail=fail):
                loop = self.loop()
                calls = []

                class LabUnavailableMind:
                    def decide(self, percept):
                        calls.append(percept.game_minute)
                        if fail:
                            raise ValueError("deliberate lab cognition failure")
                        return None

                install_lab_mind(loop, LabUnavailableMind())
                before = loop.session.projects.get(NEREID_PROJECT)
                loop.session.advance(1440)
                self.assertEqual([300, 660, 1020, 1380], calls)
                self.assertEqual(before, loop.session.projects.get(NEREID_PROJECT))
                self.assertEqual(4 if fail else 0, len(loop.session.project_runtime.errors))
                self.assertFalse(loop.session.project_trace.decisions)

    def test_review_deadline_that_expires_during_work_is_rolled_forward(self):
        loop = self.loop()
        mind = LabClockMind(PhysicalActionType.SHIFT_LOCAL_SILT.value, delay=1)
        install_lab_mind(loop, mind)
        loop.session.advance(301)
        project = loop.session.projects.get(NEREID_PROJECT)
        self.assertEqual([300], mind.minutes)
        self.assertEqual(481, project.next_review_minute)
        self.assertEqual(300, project.last_reconsidered_minute)
        self.assertEqual(1, len(project.attempt_history))

    def test_identical_serial_histories_replay_identically(self):
        sessions = []
        for _ in range(2):
            loop = self.loop()
            install_lab_mind(loop, LabClockMind(PhysicalActionType.SHIFT_LOCAL_SILT.value))
            loop.session.advance(1440)
            sessions.append(loop.session)
        left, right = sessions
        self.assertEqual(left.ledger.events, right.ledger.events)
        self.assertEqual(left.projects.projects, right.projects.projects)
        self.assertEqual(left.project_trace.decisions, right.project_trace.decisions)
        self.assertEqual(left.project_trace.resolutions, right.project_trace.resolutions)
        self.assertEqual(left.world_process_runtime.runs, right.world_process_runtime.runs)
        self.assertEqual(left.hydrology.state.state_hash(), right.hydrology.state.state_hash())

    def test_serial_time_rejects_invalid_intervals_atomically(self):
        loop = self.loop()
        for minutes in (0, -1, True, 1.5):
            with self.subTest(minutes=minutes), self.assertRaises(ValueError):
                loop.session.advance(minutes)
        self.assertEqual(0, loop.session.world.game_minute)
        self.assertFalse(loop.session.project_trace.decisions)

    def test_physics_failure_during_npc_work_cannot_be_swallowed_as_mind_failure(self):
        loop = self.loop()
        session = loop.session
        install_lab_mind(loop, LabClockMind(PhysicalActionType.SHIFT_LOCAL_SILT.value))
        later_mind = LabClockMind()
        install_lab_mind(loop, later_mind, project_id="trade_house_underpeak_route")

        def fail_at_completion(minute):
            if minute == 480:
                raise RuntimeError("deliberate authoritative listener failure")

        session.world.subscribe_time_advance(fail_at_completion)
        with self.assertRaises(RuntimeError):
            session.advance(301)
        self.assertFalse(session.project_trace.resolutions)
        self.assertEqual([], later_mind.minutes)
        with self.assertRaises(RuntimeError):
            session.advance(1)

    def test_default_i1_factory_keeps_frozen_mode(self):
        loop = create_pilot_i1_loop()
        self.assertFalse(loop.session.clock.serial_actions)
        self.assertEqual(720, loop.session.world.game_minute)
        self.assertEqual(15, loop.move("gate").minutes_elapsed)
        self.assertEqual(45, loop.inspect().minutes_elapsed)
        self.assertEqual(60, loop.wait(60).minutes_elapsed)

    def test_raw_timed_bridges_require_the_serial_session_boundary(self):
        loop = self.loop()
        session = loop.session
        request = PhysicalActionRequest("nereid_01", PhysicalActionType.INSPECT_GATE, GATE_TARGET)
        with self.assertRaisesRegex(RuntimeError, "PilotSession action boundary"):
            session.affordances.perform(request)
        echo = EchoSenseRequest("nereid_01", GATE_SITE)
        with self.assertRaisesRegex(RuntimeError, "PilotSession action boundary"):
            session.aqueous_echo_sensing.sense(echo)
        self.assertEqual(0, session.world.game_minute)
        self.assertFalse(session.ledger.events)
        self.assertTrue(session.perform(request).ok)
        self.assertTrue(session.sense_echo(echo).ok)

    def test_failed_action_restores_guard_without_running_due_mind(self):
        loop = self.loop()
        mind = LabClockMind()
        install_lab_mind(loop, mind, due=1)

        def broken_operation():
            raise ValueError("deliberate pre-commit lab failure")

        with self.assertRaises(ValueError):
            loop.session.clock.run_action(broken_operation)
        self.assertEqual([], mind.minutes)
        loop.session.advance(1)
        self.assertEqual([1], mind.minutes)


if __name__ == "__main__":
    unittest.main()
