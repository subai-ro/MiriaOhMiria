"""N4 retry interface tests. Every supplied choice is an OFFLINE LAB double."""
from copy import deepcopy
from dataclasses import asdict, replace
import json
import math
from pathlib import Path
import re
import tempfile
import unittest
from unittest.mock import patch

from worldzero.affordances import GATE_SITE, GATE_TARGET, PhysicalActionRequest, PhysicalActionType
from worldzero.neural import NeuralContextBudgetError, NeuralModelResponse, NeuralResponseError
from worldzero.pilot_nereid import (MEMORY_NATIVE, NEREID, NEREID_PROJECT, NereidEvidenceProjection,
    NereidIntentResolver, NereidMind, NereidSnapshot, create_pilot_nereid_loop, parse_decision, prepare_nereid_request)
from worldzero.pilot_nereid_contract_v2 import (CONTRACT_ID, SYSTEM_PROMPT_V2, parse_decision_v2, prepare_request_v2)
from worldzero.pilot_nereid_neural import (AuditedTransport, EvidenceBudget, ExperimentStop,
    prepare_scenario, replay_run, run_experiment, state_evidence)
from worldzero.pilot_nereid_trials import LabNereidTransport, lab_action, lab_reply, run_nereid_trials


def schema_accepts(schema, value):
    """Independent test oracle for the finite JSON-schema subset emitted here."""
    if "anyOf" in schema:
        return any(schema_accepts(branch, value) for branch in schema["anyOf"])
    kind = schema["type"]
    if kind == "null": return value is None
    if kind == "object":
        return (isinstance(value, dict) and set(value) == set(schema["required"])
                and all(schema_accepts(schema["properties"][k], v) for k, v in value.items()))
    if kind == "array":
        return (isinstance(value, list) and schema.get("minItems", 0) <= len(value) <= schema["maxItems"]
                and (not schema.get("uniqueItems") or len({json.dumps(v, sort_keys=True) for v in value}) == len(value))
                and all(schema_accepts(schema["items"], v) for v in value))
    if kind == "string":
        return (isinstance(value, str) and schema.get("minLength", 0) <= len(value) <= schema.get("maxLength", math.inf)
                and ("enum" not in schema or value in schema["enum"])
                and ("pattern" not in schema or bool(re.search(schema["pattern"], value))))
    if kind in ("integer", "number"):
        return (type(value) in ((int,) if kind == "integer" else (int, float)) and math.isfinite(value)
                and schema.get("minimum", -math.inf) <= value <= schema.get("maximum", math.inf)
                and ("exclusiveMinimum" not in schema or value > schema["exclusiveMinimum"]))
    raise AssertionError(f"unhandled test schema keyword/type: {kind}")


class LabV2WireTransport:
    """Wire-format adaptation of a labelled lab policy, NEVER production repair."""
    def __init__(self, inner=None, *, invalid=False):
        self.inner = inner if inner is not None else LabNereidTransport()
        self.invalid = invalid

    def complete(self, request):
        response = self.inner.complete(request)
        output = deepcopy(response.output)
        if output["action"] and output["action"]["verb"] != "shift_local_silt":
            output["action"].pop("effort", None)
        if self.invalid:
            output = lab_reply(action=lab_action("inspect_gate"))  # Deliberately old, invalid v2 shape.
        return replace(response, output=output)


class PilotNereidV2Tests(unittest.TestCase):
    def setUp(self):
        guard = patch("worldzero.neural.urlopen", side_effect=AssertionError("offline test called provider"))
        guard.start()
        self.addCleanup(guard.stop)

    def setup_view(self, scenario="new_gate_percept"):
        loop = prepare_scenario(scenario)
        projection = NereidEvidenceProjection(loop.session)
        projection.prepare(NEREID_PROJECT, loop.session.world.game_minute)
        request, snapshot = prepare_request_v2(projection.snapshot())
        return loop, request, snapshot

    def action(self, verb="inspect_gate", target=GATE_TARGET, refs=(), effort=1):
        result = {"verb": verb, "target": target, "evidence_refs": list(refs)}
        if verb == "shift_local_silt": result["effort"] = effort
        return result

    def assert_contract(self, output, request, snapshot, *, valid):
        self.assertEqual(valid, schema_accepts(request.output_schema, output), output)
        if valid:
            return parse_decision_v2(output, snapshot)
        with self.assertRaises(NeuralResponseError): parse_decision_v2(output, snapshot)

    def test_each_catalog_action_and_deferral_match_schema_parser(self):
        _, request, snapshot = self.setup_view()
        self.assert_contract(lab_reply(), request, snapshot, valid=True)
        for entry in request.input_payload["action_catalog"]:
            refs = entry["eligible_percept_refs"][:1] if entry["verb"] == "shift_local_silt" else []
            output = lab_reply(action=self.action(entry["verb"], entry["target"], refs))
            self.assert_contract(output, request, snapshot, valid=True)

    def test_inspection_has_no_effort_and_extra_field_is_rejected(self):
        _, request, snapshot = self.setup_view()
        for verb, target in (("inspect_gate", GATE_TARGET), ("inspect_water_state", GATE_SITE), ("sense_local_water", GATE_SITE)):
            for effort in (0, 1, 2, None):
                output = lab_reply(action={**self.action(verb, target), "effort": effort})
                self.assert_contract(output, request, snapshot, valid=False)

    def test_captured_out_of_range_work_efforts_still_fail(self):
        _, request, snapshot = self.setup_view()
        # Actual initial-batch numeric failures included 1.5, 2 and 4; no clamping.
        for effort in (True, "1", 0, -1, 1.5, 2, 4, float("nan"), float("inf")):
            output = lab_reply(action=self.action("shift_local_silt", refs=["local_percept:1"], effort=effort))
            self.assert_contract(output, request, snapshot, valid=False)
        for effort in (.01, .5, 1):
            self.assert_contract(lab_reply(action=self.action("shift_local_silt", refs=["local_percept:1"], effort=effort)),
                                 request, snapshot, valid=True)

    def test_missing_work_effort_is_not_filled_from_resources(self):
        _, request, snapshot = self.setup_view()
        output = lab_reply(action=self.action("shift_local_silt", refs=["local_percept:1"]))
        del output["action"]["effort"]
        self.assert_contract(output, request, snapshot, valid=False)

    def test_target_aliases_do_not_become_real_handles(self):
        _, request, snapshot = self.setup_view()
        for verb, target in (("inspect_gate", GATE_SITE), ("shift_local_silt", GATE_SITE),
                             ("inspect_water_state", GATE_TARGET), ("inspect_gate", "underpeak_gate")):
            self.assert_contract(lab_reply(action=self.action(verb, target, ["local_percept:1"])), request, snapshot, valid=False)

    def test_attempt_memory_can_support_thought_but_not_action(self):
        _, request, snapshot = self.setup_view("blocked_without_observation")
        self.assert_contract(lab_reply(evidence=["project_attempt:1"], hypotheses=[
            {"claim": "I attempted work, but do not know its effect", "evidence_refs": ["project_attempt:1"]}]),
            request, snapshot, valid=True)
        for refs in (["project_attempt:1"], [MEMORY_NATIVE], ["local_percept:1", "project_attempt:1"], []):
            self.assert_contract(lab_reply(action=self.action("shift_local_silt", refs=refs)), request, snapshot, valid=False)

    def test_nested_unknown_foreign_and_duplicate_refs_are_rejected(self):
        loop, _, _ = self.setup_view()
        loop.session.perform(PhysicalActionRequest("trade_house_01", PhysicalActionType.INSPECT_GATE, GATE_TARGET))
        projection = NereidEvidenceProjection(loop.session)
        request, snapshot = prepare_request_v2(projection.snapshot())
        foreign = loop.session.affordances.perceptions.for_subject("trade_house_01")[-1].ref
        for refs in ([foreign], ["local_percept:999"], ["world_event:1"], ["local_percept:1"] * 2):
            for output in (lab_reply(evidence=refs), lab_reply(hypotheses=[{"claim": "perhaps", "evidence_refs": refs}]),
                           lab_reply(action=self.action("shift_local_silt", refs=refs))):
                self.assert_contract(output, request, snapshot, valid=False)

    def test_unsupported_verbs_extra_fields_and_bad_delay_remain_invalid(self):
        _, request, snapshot = self.setup_view()
        for verb in ("open_underpeak", "complete_project", [], 42):
            self.assert_contract(lab_reply(action=self.action(verb)), request, snapshot, valid=False)
        for delay in (True, 359, 1441, 360.0):
            self.assert_contract({**lab_reply(), "review_after_minutes": delay}, request, snapshot, valid=False)
        for output in ({**lab_reply(), "success": True}, lab_reply(strategy=" "),
                       lab_reply(action={**self.action(), "duration": 1}), lab_reply(action=[self.action()])):
            self.assert_contract(output, request, snapshot, valid=False)

    def test_catalog_depends_on_owned_locality_faculty_not_objective_physics(self):
        loop, request, _ = self.setup_view()
        before = deepcopy(request.input_payload["action_catalog"])
        loop.session.hydrology.state.gate.debris_load = 0
        loop.session.hydrology.state.gate.sluice_position = 1
        projection = NereidEvidenceProjection(loop.session)
        self.assertEqual(before, prepare_request_v2(projection.snapshot())[0].input_payload["action_catalog"])
        body = next(b for b in loop.session.affordances.subjects if b.subject_id == NEREID)
        body.present_site_ids = ("northwood_junction",)
        body.faculties = ()
        body.capability_levels["inspect_water_state"] = 0
        request, snapshot = prepare_request_v2(projection.snapshot())
        self.assertEqual([], request.input_payload["action_catalog"])
        self.assert_contract(lab_reply(), request, snapshot, valid=True)
        self.assert_contract(lab_reply(action=self.action()), request, snapshot, valid=False)

    def test_zero_resources_do_not_create_a_hidden_success_or_forced_deferral(self):
        loop, request, snapshot = self.setup_view("blocked_without_observation")
        before = state_evidence(loop)
        decision = self.assert_contract(lab_reply(action=self.action("shift_local_silt", refs=["local_percept:1"])),
                                        request, snapshot, valid=True)
        result = NereidIntentResolver(loop.session).resolve(project=loop.session.projects.get(NEREID_PROJECT),
            intent=decision.intents[0], game_minute=loop.session.world.game_minute)
        self.assertFalse(result.ok)
        after = state_evidence(loop)
        for key in ("minute", "events", "hydrology", "echo", "percepts", "projects", "bodies"):
            self.assertEqual(before[key], after[key])

    def test_v1_v2_intents_have_identical_physics_costs_time_and_observation(self):
        for verb, target in (("inspect_gate", GATE_TARGET), ("inspect_water_state", GATE_SITE),
                             ("sense_local_water", GATE_SITE), ("shift_local_silt", GATE_TARGET)):
            states = []
            for version in (1, 2):
                loop, _, snapshot = self.setup_view()
                refs = ["local_percept:1"] if verb == "shift_local_silt" else []
                action = lab_action(verb, refs, target) if version == 1 else self.action(verb, target, refs)
                decision = (parse_decision if version == 1 else parse_decision_v2)(lab_reply(action=action), snapshot)
                result = NereidIntentResolver(loop.session).resolve(project=loop.session.projects.get(NEREID_PROJECT),
                    intent=decision.intents[0], game_minute=loop.session.world.game_minute)
                self.assertTrue(result.ok)
                states.append(state_evidence(loop))
            self.assertEqual(*states)

    def test_citable_lists_and_schema_are_rebuilt_after_budget_trimming(self):
        loop = prepare_scenario("baseline_uncertainty")
        for _ in range(16):
            loop.session.perform(PhysicalActionRequest(NEREID, PhysicalActionType.INSPECT_GATE, GATE_TARGET))
        projection = NereidEvidenceProjection(loop.session)
        projection.prepare(NEREID_PROJECT, loop.session.world.game_minute)
        snapshot = projection.snapshot()
        request, delivered = prepare_request_v2(snapshot, context_tokens=3800)
        self.assertLess(len(delivered.payload["percepts"]), 12)
        self.assertEqual(16, len(loop.session.affordances.perceptions.for_subject(NEREID)))
        self.assertEqual(snapshot.payload["self"], delivered.payload["self"])
        self.assertEqual(set(request.input_payload["citable_evidence_refs"]), delivered.evidence_refs)
        for entry in request.input_payload["action_catalog"]:
            self.assertLessEqual(set(entry["eligible_percept_refs"]), delivered.evidence_refs)
        omitted = delivered.payload["omitted_evidence_refs_not_citable"][-1]
        self.assert_contract(lab_reply(evidence=[omitted]), request, delivered, valid=False)

    def test_mandatory_context_overflow_fails_before_provider(self):
        _, _, snapshot = self.setup_view()
        data = snapshot.payload
        data["project"]["motivation"] = "x" * 50000
        provider = LabV2WireTransport()
        with patch.object(provider, "complete") as call:
            with self.assertRaises(NeuralContextBudgetError): NereidMind(provider, contract_version=2).decide(NereidSnapshot(json.dumps(data)))
            call.assert_not_called()

    def test_transport_cannot_expand_delivered_evidence_or_catalog(self):
        _, _, snapshot = self.setup_view()
        class LabTamperingTransport:
            def complete(self, request):
                request.input_payload["citable_evidence_refs"].append("local_percept:forged")
                request.input_payload["percepts"].append({"ref": "local_percept:forged"})
                return NeuralModelResponse(lab_reply(evidence=["local_percept:forged"]))
        with self.assertRaises(NeuralResponseError): NereidMind(LabTamperingTransport(), contract_version=2).decide(snapshot)

    def test_native_request_contains_explicit_textual_numeric_and_ref_rules(self):
        from worldzero.neural import OllamaChatTransport
        _, request, _ = self.setup_view()
        native = OllamaChatTransport().build_payload(request)
        self.assertEqual(SYSTEM_PROMPT_V2, native["messages"][0]["content"])
        self.assertIn("strictly greater than 0 and at most 1", native["messages"][0]["content"])
        self.assertIn("Do not include effort", native["messages"][0]["content"])
        self.assertIn("eligible_percept_refs", native["messages"][1]["content"])
        self.assertEqual(request.output_schema, native["format"])
        self.assertEqual({"temperature": .15, "num_ctx": 8192, "num_predict": 1200}, native["options"])

    def test_audit_checks_prompt_schema_and_projection_before_reserving_call(self):
        loop, request, _ = self.setup_view()
        with tempfile.TemporaryDirectory() as directory:
            budget = EvidenceBudget(Path(directory)/"batch")
            provider = LabV2WireTransport()
            audit = AuditedTransport(provider, budget, run_id="test", projection=NereidEvidenceProjection(loop.session), contract_version=2)
            with self.assertRaises(ExperimentStop): audit.complete(replace(request, system_prompt="forged instruction"))
            self.assertEqual(0, budget.used)

    def test_all_twelve_end_to_end_boundaries_also_pass_through_v2(self):
        def factory(**kwargs):
            kwargs["transport"] = LabV2WireTransport(kwargs["transport"])
            return create_pilot_nereid_loop(**kwargs, contract_version=2)
        with patch("worldzero.pilot_nereid_trials.create_pilot_nereid_loop", side_effect=factory):
            branches, checks = run_nereid_trials()
        self.assertEqual(12, len(checks))
        self.assertTrue(all(c.ok for c in checks), checks)
        self.assertEqual(2, branches[0].loop.nereid_mind.contract_version)
        self.assertNotIn(CONTRACT_ID, json.dumps(asdict(branches[0].after)))

    def test_v2_complete_offline_72_call_batch_and_exact_replay(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)/"batch"
            summary = run_experiment(root, provider_factory=lambda seed: LabV2WireTransport(), contract_version=2)
            self.assertTrue(summary["structural_floor_pass"], summary)
            self.assertEqual(72, summary["provider_calls_reserved"])
            self.assertEqual(18, summary["runs_completed"])
            self.assertTrue(summary["all_recorded_replays_match"])
            result = json.loads((root/"new_gate_percept_1/result.json").read_text(encoding="utf-8"))
            self.assertEqual(2, result["contract_version"])
            self.assertTrue(replay_run(result))
            result["contract_version"] = 1
            self.assertFalse(replay_run(result))

    def test_invalid_v2_shape_never_repaired_and_all_failures_replay(self):
        with tempfile.TemporaryDirectory() as directory:
            summary = run_experiment(Path(directory)/"batch", provider_factory=lambda seed: LabV2WireTransport(invalid=True), contract_version=2)
            self.assertEqual(72, summary["invalid_reviews"])
            self.assertFalse(summary["structural_floor_pass"])
            self.assertTrue(summary["all_recorded_replays_match"])

    def test_unknown_contract_versions_do_not_silently_fallback(self):
        _, _, snapshot = self.setup_view()
        for version in (0, 3, True, "2"):
            with self.assertRaises(ValueError): prepare_nereid_request(snapshot, contract_version=version)


if __name__ == "__main__":
    unittest.main()
