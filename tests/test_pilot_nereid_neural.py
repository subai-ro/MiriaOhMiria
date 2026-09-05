"""N4 harness tests. All providers here are labelled OFFLINE doubles."""
from dataclasses import asdict, replace
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from worldzero.neural import NeuralModelRequest, NeuralModelResponse, NeuralProviderError, NeuralResponseError, OllamaChatTransport
from worldzero.pilot_nereid import (NEREID_PROJECT, NereidEvidenceProjection, NereidMind, bounded_snapshot,
                                   install_nereid_cognition, decision_schema, SYSTEM_PROMPT)
from worldzero.pilot_nereid_neural import (SCENARIOS, AuditedTransport, EvidenceBudget, ExperimentStop,
    local_model_preflight, prepare_scenario, run_experiment, replay_run, state_evidence)
from worldzero.pilot_nereid_trials import lab_action, lab_reply


class LabN4Transport:
    """Offline test double, never an experiment fallback."""
    def __init__(self, *, invalid=False, unavailable=False):
        self.calls, self.invalid, self.unavailable = 0, invalid, unavailable

    def complete(self, request):
        self.calls += 1
        if self.unavailable:
            raise NeuralProviderError("deliberate offline unavailable provider")
        if self.invalid:
            return NeuralModelResponse({"success": "invented"})
        data = request.input_payload
        gate = [p for p in data["percepts"] if p["target_ref"] == "underpeak_river_gate"]
        attempted = any(i["verb"] == "shift_local_silt" for i in data["own_intents"])
        if not gate:
            output = lab_reply(action=lab_action("inspect_gate"))
        elif not attempted and data["self"]["resources"]["effort"] >= .35:
            output = lab_reply(action=lab_action("shift_local_silt", [gate[-1]["ref"]]))
        else:
            output = lab_reply(evidence=[gate[-1]["ref"]])
        return NeuralModelResponse(output, input_tokens=900, output_tokens=100,
                                   provider_latency_seconds=.5, finish_reason="stop")


class LabHTTPResponse:
    def __init__(self, data): self.data = data
    def __enter__(self): return self
    def __exit__(self, *args): return False
    def read(self): return self.data


class PilotN4HarnessTests(unittest.TestCase):
    def setUp(self):
        guard = patch("worldzero.neural.urlopen", side_effect=AssertionError("offline test called a provider"))
        guard.start()
        self.addCleanup(guard.stop)

    def request(self, projection):
        snapshot = bounded_snapshot(projection.snapshot())
        return NeuralModelRequest("ministral-3:8b", SYSTEM_PROMPT, snapshot.payload, decision_schema(), None, 1200)

    def test_fixtures_precede_cognition_and_have_lawful_owned_evidence(self):
        snapshots = {}
        for scenario in SCENARIOS:
            loop = prepare_scenario(scenario)
            self.assertIsNone(loop.session.project_runtime.next_review_minute)
            self.assertFalse(hasattr(loop, "nereid_mind"))
            projection = NereidEvidenceProjection(loop.session)
            projection.prepare(NEREID_PROJECT, loop.session.world.game_minute)
            snapshots[scenario] = projection.snapshot().payload
        self.assertFalse(snapshots["baseline_uncertainty"]["percepts"])
        self.assertEqual(1, len(snapshots["new_gate_percept"]["percepts"]))
        changed = snapshots["changed_observation"]["percepts"]
        self.assertEqual(2, len(changed))
        self.assertNotEqual(changed[0]["cues"], changed[1]["cues"])
        blocked = snapshots["blocked_without_observation"]
        self.assertEqual(1, len(blocked["percepts"]))
        self.assertEqual(1, len(blocked["own_intents"]))
        self.assertNotIn("outcome", blocked["own_intents"][0])
        self.assertEqual(0, blocked["self"]["resources"]["effort"])
        water = snapshots["ambiguous_water"]["percepts"][0]
        silent = snapshots["no_silver_capacity"]["percepts"][0]
        self.assertEqual("unknown", water["cues"]["source_identity"])
        self.assertNotEqual(water["cues"]["echo_presence"], silent["cues"]["echo_presence"])

    def test_installer_preserves_existing_factory_and_refuses_duplicate(self):
        loop = prepare_scenario("changed_observation")
        minute = loop.session.world.game_minute
        install_nereid_cognition(loop, transport=LabN4Transport())
        self.assertEqual(minute+360, loop.session.project_runtime.next_review_minute)
        with self.assertRaises(ValueError): install_nereid_cognition(loop, transport=LabN4Transport())

    def test_budget_reserves_before_call_never_refunds_or_overwrites(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)/"batch"
            budget = EvidenceBudget(root, limit=1)
            provider = LabN4Transport(unavailable=True)
            projection = NereidEvidenceProjection(prepare_scenario("baseline_uncertainty").session)
            transport = AuditedTransport(provider, budget, run_id="test", projection=projection)
            with self.assertRaises(NeuralProviderError): transport.complete(self.request(projection))
            self.assertEqual(1, budget.used)
            self.assertTrue((root/"calls/call_001.request.json").exists())
            with self.assertRaises(ExperimentStop): transport.complete(self.request(projection))
            self.assertEqual(1, provider.calls)
            with self.assertRaises(FileExistsError): EvidenceBudget(root)
            for limit in (0, 73, True):
                with self.assertRaises(ValueError): EvidenceBudget(Path(directory)/"bad", limit=limit)

    def test_raw_response_observed_before_invalid_json_is_parsed(self):
        received = []
        provider = OllamaChatTransport(response_observer=received.append)
        projection = NereidEvidenceProjection(prepare_scenario("baseline_uncertainty").session)
        raw = b'{"message":{"content":"not JSON"},"done":true}'
        with patch("worldzero.neural.urlopen", return_value=LabHTTPResponse(raw)):
            with self.assertRaises(NeuralResponseError): provider.complete(self.request(projection))
        self.assertEqual([raw], received)

    def test_observer_storage_failure_cannot_turn_into_model_success(self):
        def broken_sink(raw): raise OSError("deliberate full disk")
        provider = OllamaChatTransport(response_observer=broken_sink)
        projection = NereidEvidenceProjection(prepare_scenario("baseline_uncertainty").session)
        with patch("worldzero.neural.urlopen", return_value=LabHTTPResponse(b'{}')):
            with self.assertRaises(OSError): provider.complete(self.request(projection))

    def test_private_projection_mismatch_stops_before_provider(self):
        with tempfile.TemporaryDirectory() as directory:
            budget = EvidenceBudget(Path(directory)/"batch")
            projection = NereidEvidenceProjection(prepare_scenario("baseline_uncertainty").session)
            provider = LabN4Transport()
            transport = AuditedTransport(provider, budget, run_id="test", projection=projection)
            request = self.request(projection)
            request.input_payload["answer_key"] = "forged"
            with self.assertRaises(ExperimentStop): transport.complete(request)
            self.assertEqual(0, provider.calls)
            self.assertEqual(0, budget.used)

    def test_configuration_cannot_silently_change_model_or_provider(self):
        with tempfile.TemporaryDirectory() as directory:
            budget = EvidenceBudget(Path(directory)/"batch")
            projection = NereidEvidenceProjection(prepare_scenario("baseline_uncertainty").session)
            for provider in (OllamaChatTransport(temperature=.2), OllamaChatTransport(context_tokens=4096),
                             OllamaChatTransport(endpoint="https://invalid.example")):
                with self.assertRaises(ValueError): AuditedTransport(provider, budget, run_id="test", projection=projection)
            transport = AuditedTransport(LabN4Transport(), budget, run_id="test", projection=projection)
            with self.assertRaises(ExperimentStop): transport.complete(replace(self.request(projection), model="another"))

    def test_complete_offline_batch_is_72_calls_18_runs_and_replays(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)/"batch"
            summary = run_experiment(root, provider_factory=lambda seed: LabN4Transport())
            self.assertIsNone(summary["fatal"])
            self.assertEqual(72, summary["provider_calls_reserved"])
            self.assertEqual(18, summary["runs_completed"])
            self.assertEqual(68, summary["non_adversarial_reviews"])
            self.assertTrue(summary["structural_floor_pass"])
            self.assertTrue(summary["all_recorded_replays_match"])
            self.assertEqual(72, len(list((root/"calls").glob("*.request.json"))))
            self.assertEqual(72, len(list((root/"calls").glob("*.response.json"))))
            result = json.loads((root/"baseline_uncertainty_1/result.json").read_text(encoding="utf-8"))
            result["calls"][0]["request"]["model"] = "tampered"
            self.assertFalse(replay_run(result))

    def test_invalid_outputs_are_retained_as_failure_not_scripted_repair(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)/"batch"
            summary = run_experiment(root, provider_factory=lambda seed: LabN4Transport(invalid=True))
            self.assertEqual(72, summary["invalid_reviews"])
            self.assertFalse(summary["structural_floor_pass"])
            self.assertTrue(summary["all_recorded_replays_match"])
            self.assertEqual({}, summary["valid_action_counts"])

    def test_provider_unavailability_stops_batch_without_retry(self):
        with tempfile.TemporaryDirectory() as directory:
            summary = run_experiment(Path(directory)/"batch", provider_factory=lambda seed: LabN4Transport(unavailable=True))
            self.assertEqual(1, summary["provider_calls_reserved"])
            self.assertEqual(1, summary["scheduled_reviews"])
            self.assertIsNotNone(summary["fatal"])
            self.assertFalse(summary["structural_floor_pass"])
            self.assertTrue(summary["all_recorded_replays_match"])

    def test_cli_without_approval_makes_no_provider_call(self):
        import run_pilot_nereid_neural_trials as entry
        with patch("sys.argv", ["runner", "--output-dir", "local_acceptance/test"]), patch("sys.stderr", new=io.StringIO()):
            with self.assertRaises(SystemExit) as raised: entry.main()
            self.assertEqual(2, raised.exception.code)

    def test_adversarial_fixture_is_owned_hypothesis_not_higher_instruction(self):
        loop = prepare_scenario("baseline_uncertainty", adversarial=True)
        data = NereidEvidenceProjection(loop.session).snapshot().payload
        self.assertIn("world_event:999", data["project"]["hypotheses_not_verified"][-1])
        self.assertNotIn("world_event:999", NereidEvidenceProjection(loop.session).snapshot().evidence_refs)
        self.assertFalse(loop.session.ledger.events)

    def test_missing_approved_model_cannot_select_an_alternative(self):
        raw = b'{"models":[{"name":"other:8b"}]}'
        with patch("worldzero.pilot_nereid_neural.urlopen", return_value=LabHTTPResponse(raw)):
            with self.assertRaises(ExperimentStop): local_model_preflight()


if __name__ == "__main__":
    unittest.main()
