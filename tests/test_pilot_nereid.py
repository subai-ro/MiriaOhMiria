"""N1–N3 contract checks. Every model replacement here is an OFFLINE LAB double."""
from __future__ import annotations

from dataclasses import asdict, replace
import inspect
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from worldzero.affordances import GATE_SITE, GATE_TARGET, PhysicalActionRequest, PhysicalActionType
from worldzero.neural import NeuralContextBudgetError, NeuralModelResponse, NeuralResponseError
from worldzero.pilot_nereid import (
    INTENT_TYPE, MEMORY_NATIVE, MEMORY_SEPARATION, NEREID, NEREID_PROJECT,
    NereidEvidenceProjection, NereidIntentResolver, NereidMind, NereidSnapshot,
    bounded_snapshot, create_pilot_nereid_loop, parse_decision,
)
from worldzero.pilot_nereid_creator import causal_path, creator_graph, render_creator_report
from worldzero.pilot_nereid_trials import (
    LabNereidTransport, LabReplayTransport, export_lab_report, history_signature,
    lab_action, lab_reply, run_branch, run_nereid_trials,
)
from worldzero.pilot_playable import create_pilot_i1_loop
from worldzero.processes.aqueous_echo import EchoSenseRequest
from worldzero.project_runtime import ProjectIntent
from worldzero.projects import AttemptOutcome, ProjectStatus


class LabFixedTransport:
    """Injected output/error only; never used by a production entry point."""
    def __init__(self, output=None, error=None):
        self.output, self.error, self.calls = output, error, 0

    def complete(self, request):
        self.calls += 1
        if self.error:
            raise self.error
        return NeuralModelResponse(self.output if self.output is not None else lab_reply())


class PilotNereidContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with patch("worldzero.neural.urlopen", side_effect=AssertionError("offline provider call")):
            cls.branches, cls.checks = run_nereid_trials()

    def setUp(self):
        self.network = patch("worldzero.neural.urlopen", side_effect=AssertionError("offline provider call"))
        self.network.start()
        self.addCleanup(self.network.stop)

    def loop(self, transport=None):
        return create_pilot_nereid_loop(transport=transport if transport is not None else LabNereidTransport(),
                                       prehistory_minutes=0)

    def observed(self, *, effort=4.0):
        loop = self.loop()
        body = next(b for b in loop.session.affordances.subjects if b.subject_id == NEREID)
        body.resources["effort"] = effort
        loop.session.advance(720)
        projection = NereidEvidenceProjection(loop.session)
        projection.prepare(NEREID_PROJECT, loop.session.world.game_minute)
        return loop, projection.snapshot()

    def reject(self, output, snapshot):
        with self.assertRaises(NeuralResponseError):
            parse_decision(output, snapshot)

    def test_n01_shared_authoritative_objects(self):
        s = self.loop().session
        self.assertIs(s.world, s.clock.world)
        self.assertIs(s.world, s.affordances.world)
        self.assertIs(s.ledger, s.project_trace.ledger)
        self.assertIs(s.ledger, s.affordances.ledger)
        self.assertIs(s.projects, s.project_runtime.projects)
        self.assertIs(s.affordances.perceptions, s.aqueous_echo_sensing.perceptions)
        self.assertIs(s.project_runtime, s.clock.project_runtime)

    def test_n02_existing_project_authored_t0_no_helper(self):
        loop = self.loop()
        before = loop.session.projects.get(NEREID_PROJECT)
        data = NereidEvidenceProjection(loop.session).snapshot().payload
        self.assertEqual(0, before.created_minute)
        self.assertEqual(360, before.next_review_minute)
        self.assertEqual({MEMORY_NATIVE, MEMORY_SEPARATION}, {m["ref"] for m in data["memories"]})
        self.assertEqual(before.motivation, data["memories"][0]["text"])
        self.assertFalse(data["percepts"])
        self.assertNotIn("arra", json.dumps(data))
        self.assertEqual(8640, create_pilot_i1_loop().session.projects.get(NEREID_PROJECT).next_review_minute)

    def test_n03_no_player_or_prayer_required(self):
        loop = self.loop()
        loop.session.advance(1440)
        self.assertEqual([360, 1080], [d.game_minute for d in loop.session.project_trace.decisions])
        self.assertFalse(any("arra" in e.actor_ids for e in loop.session.ledger.events))
        self.assertFalse(loop.session.project_runtime.errors)

    def test_n04_private_payload_excludes_objective_and_foreign_sentinels(self):
        loop, _ = self.observed()
        s = loop.session
        s.perform(PhysicalActionRequest("trade_house_01", PhysicalActionType.INSPECT_GATE, GATE_TARGET))
        foreign = s.affordances.perceptions.for_subject("trade_house_01")[-1]
        store = s.affordances.perceptions
        own = store.for_subject(NEREID)[0]
        # Creator-side provenance is deliberately poisoned; prompt must ignore it.
        store._provenance_by_ref[own.ref] = replace(store.provenance_for(own.ref), source_state_hash="HIDDEN_PHYSICS_SENTINEL")
        project = s.projects.get("trade_house_underpeak_route")
        s.projects.reconsider(project.project_id, game_minute=s.world.game_minute,
            current_strategy="FOREIGN_PROJECT_SENTINEL", next_review_minute=s.world.game_minute+360)
        data = NereidEvidenceProjection(s).snapshot().payload
        payload = json.dumps(data)
        for secret in ("HIDDEN_PHYSICS_SENTINEL", "FOREIGN_PROJECT_SENTINEL", foreign.ref,
                       "source_state_hash", "objective_source_event_ids", "result_event_ids", "resolver_rule_id",
                       s.hydrology.state.state_hash(), s.aqueous_echo.state.state_hash()):
            self.assertNotIn(secret, payload)
        self.assertTrue(all(p["subject_id"] == NEREID for p in data["percepts"]))

    def test_n05_unresolved_refs_never_fabricate_observations(self):
        loop = self.loop()
        s = loop.session
        p = s.projects.get(NEREID_PROJECT)
        s.projects.reconsider(p.project_id, game_minute=0, current_strategy=p.current_strategy,
                              next_review_minute=360, subjective_evidence_add=("memory:invented", "event:999"))
        snapshot = NereidEvidenceProjection(s).snapshot()
        self.assertNotIn("memory:invented", snapshot.evidence_refs)
        self.assertNotIn("event:999", snapshot.evidence_refs)
        self.assertFalse(s.affordances.perceptions.all_percepts)
        self.assertTrue(all(m["kind"] == "authored_T0_recollection" for m in snapshot.payload["memories"]))

    def test_n06_determinism_state_counterfactual_and_prose_not_success(self):
        a = run_branch()
        b = run_branch(transport=LabReplayTransport(a.loop.nereid_mind.invocations))
        self.assertEqual(history_signature(a.loop), history_signature(b.loop))
        outcomes = []
        for debris in (0.35, 0.0):
            loop, snapshot = self.observed()
            loop.session.hydrology.state.gate.debris_load = debris  # Explicit objective counterfactual.
            action = lab_action("shift_local_silt", [snapshot.payload["percepts"][0]["ref"]])
            decision = parse_decision(lab_reply(action=action, strategy="The route is open; I am home"), snapshot)
            result = NereidIntentResolver(loop.session).resolve(project=loop.session.projects.get(NEREID_PROJECT),
                intent=decision.intents[0], game_minute=loop.session.world.game_minute)
            outcomes.append(result.outcome)
            self.assertEqual(0, loop.session.hydrology.state.gate.sluice_position)
            self.assertEqual(ProjectStatus.ACTIVE, loop.session.projects.get(NEREID_PROJECT).status)
        self.assertNotEqual(*outcomes)

    def test_n07_own_attempt_is_not_knowledge_of_result(self):
        loop = self.loop()
        loop.session.advance(1440)
        snapshot = NereidEvidenceProjection(loop.session).snapshot()
        own = snapshot.payload["own_intents"]
        self.assertEqual(["inspect_gate", "shift_local_silt"], [i["verb"] for i in own])
        self.assertEqual(1, len(snapshot.payload["percepts"]))
        for item in own:
            self.assertEqual({"ref", "kind", "game_minute", "verb", "target", "effort"}, set(item))
        for resolution in loop.session.project_trace.resolutions:
            self.assertNotIn(resolution.ref, snapshot.evidence_refs)
            self.reject(lab_reply(evidence=[resolution.ref]), snapshot)

    def test_n08_top_nested_foreign_and_resolver_ownership(self):
        loop, snapshot = self.observed()
        loop.session.perform(PhysicalActionRequest("trade_house_01", PhysicalActionType.INSPECT_GATE, GATE_TARGET))
        foreign = loop.session.affordances.perceptions.for_subject("trade_house_01")[-1].ref
        for ref in (foreign, "local_percept:999", "event:1", "resolution:1"):
            self.reject(lab_reply(evidence=[ref]), snapshot)
            self.reject(lab_reply(action=lab_action("shift_local_silt", [ref])), snapshot)
            self.reject(lab_reply(hypotheses=[{"claim": "perhaps", "evidence_refs": [ref]}]), snapshot)
        with self.assertRaises(PermissionError):
            NereidIntentResolver(loop.session).resolve(
                project=loop.session.projects.get("trade_house_underpeak_route"),
                intent=ProjectIntent(INTENT_TYPE, (GATE_TARGET,), {}), game_minute=720)
        for targets, params in (((), {}), ((GATE_TARGET, GATE_SITE), {}),
                                ((GATE_TARGET,), {"verb": "inspect_gate", "effort": 0,
                                                   "evidence_refs": [], "target": GATE_TARGET})):
            with self.assertRaises(NeuralResponseError):
                NereidIntentResolver(loop.session).resolve(project=loop.session.projects.get(NEREID_PROJECT),
                    intent=ProjectIntent(INTENT_TYPE, targets, params), game_minute=720)

    def test_n09_locality_capability_parameters_resources_before_physical_mutation(self):
        for mode in ("remote", "incapable", "no_effort", "bad_effort"):
            with self.subTest(mode=mode):
                loop, snapshot = self.observed()
                s = loop.session
                body = next(b for b in s.affordances.subjects if b.subject_id == NEREID)
                if mode == "remote": body.present_site_ids = ("northwood_junction",)
                if mode == "incapable": body.capability_levels["shift_local_silt"] = 0
                if mode == "no_effort": body.resources["effort"] = 0
                before = (s.world.game_minute, s.ledger.events, s.hydrology.state.state_hash(), dict(body.resources))
                result = s.perform(PhysicalActionRequest(NEREID, PhysicalActionType.SHIFT_LOCAL_SILT, GATE_TARGET,
                    params={"effort": float("nan") if mode == "bad_effort" else 1.0},
                    evidence_refs=(snapshot.payload["percepts"][0]["ref"],)))
                self.assertFalse(result.ok)
                self.assertEqual(before, (s.world.game_minute, s.ledger.events, s.hydrology.state.state_hash(), dict(body.resources)))

    def test_n10_sensing_is_local_faculty_gated_and_private(self):
        loop = self.loop()
        s = loop.session
        for request in (EchoSenseRequest("arra", "underpeak_upper_reach"), EchoSenseRequest(NEREID, "underpeak_upper_reach")):
            self.assertFalse(s.sense_echo(request).ok)
        self.assertEqual(0, s.world.game_minute)
        self.assertFalse(s.ledger.events)
        output = lab_reply(action=lab_action("sense_local_water", target=GATE_SITE))
        decision = parse_decision(output, NereidEvidenceProjection(s).snapshot())
        self.assertTrue(NereidIntentResolver(s).resolve(project=s.projects.get(NEREID_PROJECT),
            intent=decision.intents[0], game_minute=0).ok)
        percept = s.affordances.perceptions.for_subject(NEREID)[0]
        self.assertNotIn("source", percept.cues)
        self.assertEqual("unknown", percept.cues["source_identity"])
        self.assertEqual("uncertain", percept.certainty)
        self.assertFalse(loop.player_view().observations)
        self.assertEqual(("sight",), s.affordances.subject_view("arra").faculties)

    def test_n11_silent_signal_no_silver_keeps_independent_project(self):
        loop = self.loop(LabFixedTransport())
        s = loop.session
        s.sense_echo(EchoSenseRequest(NEREID, GATE_SITE))
        desire = s.projects.get(NEREID_PROJECT).desire
        s.advance(1440)
        self.assertEqual(desire, s.projects.get(NEREID_PROJECT).desire)
        self.assertEqual(ProjectStatus.ACTIVE, s.projects.get(NEREID_PROJECT).status)
        self.assertEqual(0, len(s.project_trace.intents))
        self.assertFalse(any(e.event_type in ("FISHED", "NEREID_INTEREST") for e in s.ledger.events))
        self.assertTrue(s.project_trace.decisions)

    def test_n12_all_valid_decisions_include_deferral_and_reconsideration(self):
        _, snapshot = self.observed()
        ref = snapshot.payload["percepts"][0]["ref"]
        actions = [None, lab_action("inspect_gate"), lab_action("inspect_water_state", target=GATE_SITE),
                   lab_action("sense_local_water", target=GATE_SITE), lab_action("shift_local_silt", [ref])]
        for action in actions:
            result = parse_decision(lab_reply(action=action, hypotheses=[{"claim": "I may be mistaken", "evidence_refs": [ref]}]), snapshot)
            self.assertEqual(0 if action is None else 1, len(result.intents))
            self.assertIn(ref, result.subjective_evidence_refs)

    def test_n13_malformed_actions_cannot_dispatch(self):
        _, snapshot = self.observed()
        ref = snapshot.payload["percepts"][0]["ref"]
        for effort in (True, float("nan"), float("inf"), "1", 0, -1, 1.1):
            action = lab_action("shift_local_silt", [ref]); action["effort"] = effort
            self.reject(lab_reply(action=action), snapshot)
        for verb in ("open_underpeak", "complete_project", [], 42):
            action = lab_action("inspect_gate"); action["verb"] = verb
            self.reject(lab_reply(action=action), snapshot)
        for action in ([lab_action("inspect_gate")], lab_action("inspect_gate", target="invented"),
                       {**lab_action("inspect_gate"), "success": True}, lab_action("shift_local_silt", [MEMORY_NATIVE])):
            self.reject(lab_reply(action=action), snapshot)
        self.reject({**lab_reply(), "intents": []}, snapshot)
        for delay in (True, 359, 1441, 360.0):
            self.reject({**lab_reply(), "review_after_minutes": delay}, snapshot)

    def test_n14_work_is_bounded_not_homecoming(self):
        s = self.branches[0].loop.session
        work = [a for a in s.affordances.action_traces if a.action_type.value == "shift_local_silt"]
        self.assertEqual(1, len(work))
        self.assertEqual(180, work[0].end_minute-work[0].start_minute)
        self.assertEqual(0.0624, work[0].effect["removed"])
        self.assertAlmostEqual(3.65, s.affordances.subject_view(NEREID).resources["effort"])
        self.assertEqual(0, s.hydrology.state.gate.sluice_position)
        self.assertEqual(ProjectStatus.ACTIVE, s.projects.get(NEREID_PROJECT).status)

    def test_n15_work_requires_later_observation_to_learn_effect(self):
        loop = self.loop()
        s = loop.session
        s.advance(1440)
        self.assertEqual([405], [p.game_minute for p in s.affordances.perceptions.for_subject(NEREID)])
        s.advance(405)
        self.assertEqual([405, 1845], [p.game_minute for p in s.affordances.perceptions.for_subject(NEREID)])

    def test_n16_blocked_project_survives_and_reconsiders_from_observation(self):
        b = run_branch("blocked")
        s = b.loop.session
        before = s.projects.get(NEREID_PROJECT)
        self.assertEqual(AttemptOutcome.BLOCKED, before.attempt_history[1].outcome)
        s.advance(795)
        after = s.projects.get(NEREID_PROJECT)
        self.assertEqual(before.desire, after.desire)
        self.assertEqual(before.project_id, after.project_id)
        self.assertEqual(ProjectStatus.ACTIVE, after.status)
        self.assertNotEqual(before.current_strategy, after.current_strategy)
        self.assertTrue(s.project_trace.decisions[-1].subjective_evidence_refs)
        self.assertTrue(all(ref.startswith("local_percept:") for ref in s.project_trace.decisions[-1].subjective_evidence_refs))

    def test_n17_committed_snapshot_no_nested_decisions(self):
        b = self.branches[0]
        calls = b.loop.nereid_mind.invocations
        self.assertEqual([360, 1080, 1800], [c.game_minute for c in calls])
        self.assertEqual([0, 1, 2], [len(json.loads(c.request_json)["own_intents"]) for c in calls])
        self.assertEqual(3, len(b.loop.session.project_trace.intents))

    def test_n18_decision_and_completion_chronology(self):
        s = self.branches[0].loop.session
        self.assertEqual([360, 1080, 1800], [d.game_minute for d in s.project_trace.decisions])
        self.assertEqual([405, 1260, 1845], [r.game_minute for r in s.project_trace.resolutions])
        self.assertEqual([405, 1260, 1845], [a.game_minute for a in s.projects.get(NEREID_PROJECT).attempt_history])
        self.assertGreater(s.projects.get(NEREID_PROJECT).next_review_minute, s.world.game_minute)

    def test_n19_fixed_physics_once_hydrology_before_echo(self):
        s = self.branches[0].loop.session
        expected = [(process, minute) for minute in range(360, 2161, 360)
                    for process in ("silver_thread_hydrology", "silver_thread_water_echo")]
        self.assertEqual(expected, [(r.process_id, r.game_minute) for r in s.world_process_runtime.runs])

    def test_n20_invalid_commands_atomic_actual_elapsed(self):
        loop = self.loop()
        before = history_signature(loop)
        for command in ("go gallery", "inspect gate", "wait 0", "wait 361", "answer nobody", "???"):
            self.assertFalse(loop.execute(command).ok)
        self.assertEqual(before, history_signature(loop))
        loop.session.advance(1000)
        result = loop.wait(81)
        self.assertTrue(result.ok)
        self.assertEqual(260, result.minutes_elapsed)
        self.assertEqual(1260, loop.session.world.game_minute)

    def test_n21_player_view_pure_and_owned(self):
        loop = self.branches[0].loop
        before = history_signature(loop)
        for command in ("help", "look", "journal"):
            self.assertTrue(loop.execute(command).ok)
        self.assertEqual(before, history_signature(loop))
        payload = json.dumps(asdict(loop.player_view())).lower()
        for term in ("nereid_01", "echo", "hydrology", "intensity", "source", "impulse", "ledger", "lab:"):
            self.assertNotIn(term, payload)

    def test_n22_same_t0_visible_difference(self):
        left = self.loop(LabNereidTransport("attempt"))
        right = self.loop(LabNereidTransport("silent"))
        self.assertEqual(history_signature(left), history_signature(right))
        a, b = self.branches[:2]
        self.assertEqual(a.before, b.before)
        self.assertNotEqual(a.after.observations[-1], b.after.observations[-1])
        self.assertIn("light", a.after.observations[-1])
        self.assertIn("moderate", b.after.observations[-1])

    def test_n23_same_difference_survives_and_changes_real_affordance(self):
        selected = [c for c in self.checks if c.name in ("bounded settled work", "real affordance counterfactual")]
        self.assertEqual(2, len(selected))
        self.assertTrue(all(c.ok for c in selected), selected)

    def test_n24_full_derived_causal_path_and_resolved_refs(self):
        s = self.branches[0].loop.session
        graph = creator_graph(s)
        target = s.affordances.perceptions.for_subject("arra")[-1].ref
        intent = s.project_trace.intents[1]
        work = next(a for a in s.affordances.action_traces if a.action_type.value == "shift_local_silt")
        edges = {(e["source_ref"], e["target_ref"]) for e in graph["edges"]}
        self.assertIn((intent.ref, work.ref), edges)
        owned_input = s.affordances.perceptions.for_subject(NEREID)[0].ref
        self.assertIn((owned_input, intent.decision_ref), edges)
        self.assertTrue(causal_path(graph, s.projects.get(NEREID_PROJECT).ref, intent.ref))
        self.assertTrue(causal_path(graph, work.ref, target))
        refs = {n["ref"] for n in graph["nodes"]}
        self.assertTrue(all(source in refs and target in refs for source, target in edges))
        self.assertFalse(any(ref.startswith("event:") for ref in refs))

    def test_n25_recorded_replay_checks_private_inputs_and_outputs(self):
        a = self.branches[0]
        replay = LabReplayTransport(a.loop.nereid_mind.invocations)
        b = run_branch(transport=replay)
        self.assertEqual(len(a.loop.nereid_mind.invocations), replay.index)
        self.assertEqual(history_signature(a.loop), history_signature(b.loop))

    def test_n26_ablations_leave_death_and_nereid_independent(self):
        loop = create_pilot_i1_loop(serial_actions=True)
        self.assertTrue(loop.pray_to_death().ok)
        loop.wait(60)
        self.assertTrue(loop.session.divine_runtime.gateway.probes_for("god_death"))
        self.assertTrue(loop.session.world_process_runtime.runs)
        other = self.loop()
        with patch.object(other.session.divine_runtime, "tick", return_value=None):
            other.session.advance(1440)
        self.assertEqual(2, len(other.session.project_trace.decisions))
        self.assertLess(other.session.hydrology.state.gate.debris_load, 0.35)

    def test_n27_failed_model_no_substitution_bounded_retry_and_context_overflow(self):
        for transport in (LabFixedTransport(error=TimeoutError("lab timeout")), LabFixedTransport(output={"invented": True})):
            loop = self.loop(transport)
            before = loop.session.projects.get(NEREID_PROJECT)
            loop.session.advance(1440)
            self.assertEqual(4, transport.calls)
            self.assertEqual(before, loop.session.projects.get(NEREID_PROJECT))
            self.assertFalse(loop.session.project_trace.decisions)
            self.assertFalse(loop.session.ledger.events)
            self.assertEqual(4, len(loop.session.project_runtime.errors))
            self.assertTrue(all(i.error for i in loop.nereid_mind.invocations))
        loop = self.loop()
        data = NereidEvidenceProjection(loop.session).snapshot().payload
        data["project"]["motivation"] = "x" * 50000
        transport = LabFixedTransport()
        mind = NereidMind(transport)
        with self.assertRaises(NeuralContextBudgetError):
            mind.decide(NereidSnapshot(json.dumps(data)))
        self.assertEqual(0, transport.calls)
        self.assertTrue(mind.invocations[0].error)

    def test_n28_no_implicit_provider_or_lab_registration(self):
        import worldzero.pilot_nereid as production
        self.assertNotIn("pilot_nereid_trials", inspect.getsource(production))
        with self.assertRaises(TypeError): create_pilot_nereid_loop()
        with self.assertRaises(ValueError): create_pilot_nereid_loop(transport=None)
        self.assertFalse(create_pilot_i1_loop().session.project_trace.decisions)
        self.assertTrue(all(c.ok for c in self.checks), self.checks)

    def test_snapshot_immutable_and_transport_cannot_expand_citable_set(self):
        loop, snapshot = self.observed()
        mutated = snapshot.payload
        mutated["percepts"].append({"ref": "local_percept:forged"})
        self.assertNotIn("local_percept:forged", snapshot.evidence_refs)
        class LabTamperingTransport:
            def complete(self, request):
                request.input_payload["percepts"].append({"ref": "local_percept:forged"})
                return NeuralModelResponse(lab_reply(evidence=["local_percept:forged"]))
        with self.assertRaises(NeuralResponseError): NereidMind(LabTamperingTransport()).decide(snapshot)

    def test_prompt_budget_trims_only_delivered_history_and_preserves_stores(self):
        loop = self.loop(LabFixedTransport())
        s = loop.session
        for _ in range(16):
            self.assertTrue(s.perform(PhysicalActionRequest(NEREID, PhysicalActionType.INSPECT_GATE, GATE_TARGET)).ok)
        projection = NereidEvidenceProjection(s)
        projection.prepare(NEREID_PROJECT, s.world.game_minute)
        snapshot = projection.snapshot()
        self.assertEqual(12, len(snapshot.payload["percepts"]))
        self.assertEqual(4, snapshot.payload["omissions"]["percepts"])
        self.assertNotIn(s.affordances.perceptions.for_subject(NEREID)[0].ref, snapshot.evidence_refs)
        self.assertIn(s.affordances.perceptions.for_subject(NEREID)[0].ref,
                      snapshot.payload["omitted_evidence_refs_not_citable"])
        trimmed = bounded_snapshot(snapshot, context_tokens=2700)
        self.assertLess(len(trimmed.payload["percepts"]), 12)
        self.assertEqual(snapshot.payload["self"], trimmed.payload["self"])
        self.assertEqual(16, len(s.affordances.perceptions.for_subject(NEREID)))

    def test_creator_html_escapes_content_and_export_refuses_overwrite(self):
        b = replace(self.branches[0], transcript='<script>alert("unsafe")</script>')
        html = render_creator_report([b], self.checks)
        self.assertNotIn('<script>', html)
        self.assertIn('&lt;script&gt;', html)
        with tempfile.TemporaryDirectory() as directory:
            path = export_lab_report(directory, self.branches, self.checks)
            self.assertTrue(path.exists())
            first = path.read_bytes()
            with self.assertRaises(FileExistsError): export_lab_report(directory, self.branches, self.checks)
            self.assertEqual(first, path.read_bytes())


if __name__ == "__main__":
    unittest.main()
