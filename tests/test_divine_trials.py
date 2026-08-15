from __future__ import annotations

import json
import unittest

from worldzero.neural import NeuralDeathGodBrain, NeuralGodConfig, NeuralModelRequest, NeuralModelResponse
from worldzero.trials import TRIAL_IDS, DivineTrialRunner


def passive_decision() -> dict:
    return {
        "goal": "Observe without forcing meaning onto every perception.",
        "decision_note": "I choose to wait.",
        "cognitive_posture": "observe",
        "subjective_significance": 0.10,
        "consciousness_plan": {
            "engagement": 0.0,
            "personal_fraction": 0.0,
            "spatial_targets": [],
            "personal_targets": [],
        },
        "belief_updates": [],
        "veiled_hypothesis_updates": [],
        "impression_updates": [],
        "personal_omens": [],
        "personal_probes": [],
        "area_omens": [],
        "interventions": [],
    }


class CapturingTransport:
    def __init__(self, output: dict | None = None) -> None:
        self.output = output or passive_decision()
        self.requests: list[NeuralModelRequest] = []

    def complete(self, request: NeuralModelRequest) -> NeuralModelResponse:
        self.requests.append(request)
        return NeuralModelResponse(
            output=self.output,
            response_id="trial_fake",
            input_tokens=400,
            output_tokens=80,
            provider_latency_seconds=0.25,
            load_seconds=0.02,
            prompt_eval_seconds=0.10,
            generation_seconds=0.10,
        )


class OmenExperimentTransport:
    """Two-wake brain used to prove the indirect-omen longitudinal path."""

    def __init__(self) -> None:
        self.requests: list[NeuralModelRequest] = []

    def complete(self, request: NeuralModelRequest) -> NeuralModelResponse:
        self.requests.append(request)
        if len(self.requests) == 1:
            arra_knowledge = next(
                item
                for item in request.input_payload["subjective_knowledge"]
                if "arra" in item["known_actor_ids"]
            )
            output = {
                **passive_decision(),
                "goal": "Use a sign as an indirect experiment without demanding an answer.",
                "cognitive_posture": "investigate",
                "subjective_significance": 0.70,
                "belief_updates": [
                    {
                        "belief_type": "awareness",
                        "subject_actor_id": "arra",
                        "object_ref": "event:1",
                        "direction": "support",
                        "weight": 0.30,
                        "reason": "Arra's cold remark may indicate weak awareness of the disturbance",
                        "evidence_knowledge_ids": [arra_knowledge["knowledge_id"]],
                    }
                ],
                "area_omens": [
                    {
                        "location_id": "ash_valley",
                        "significance": 0.60,
                        "message": "Let the valley remember the boundary that was crossed.",
                        "reason": "create an indirect sign and watch what mortals do afterward",
                        "causal_event_ids": [1],
                    }
                ],
            }
        else:
            reaction = next(
                item
                for item in request.input_payload["subjective_knowledge"]
                if "That sign unsettled me." in item["summary"]
            )
            output = {
                **passive_decision(),
                "goal": "Revise my prior view from the ordinary reaction I actually perceived.",
                "cognitive_posture": "investigate",
                "subjective_significance": 0.65,
                "belief_updates": [
                    {
                        "belief_type": "awareness",
                        "subject_actor_id": "arra",
                        "object_ref": "event:1",
                        "direction": "support",
                        "weight": 0.50,
                        "reason": "Arra spontaneously connected the sign to a cold disturbance among the dead",
                        "evidence_knowledge_ids": [reaction["knowledge_id"]],
                    }
                ],
            }
        return NeuralModelResponse(
            output=output,
            response_id=f"omen_experiment_{len(self.requests)}",
            input_tokens=500,
            output_tokens=120,
        )


class LoopingProbeTransport:
    """Always asks again so the longitudinal trial must stop at its lab cap."""

    def __init__(self) -> None:
        self.requests: list[NeuralModelRequest] = []

    def complete(self, request: NeuralModelRequest) -> NeuralModelResponse:
        self.requests.append(request)
        output = {
            **passive_decision(),
            "goal": "Keep asking Arra while uncertainty remains.",
            "cognitive_posture": "investigate",
            "subjective_significance": 0.60,
            "personal_probes": [
                {
                    "target_actor_id": "arra",
                    "location_id": "ash_valley",
                    "significance": 0.50,
                    "message": f"Question {len(self.requests)}: tell me what you perceived.",
                    "reason": "continue explicit interrogation for this bounded test",
                    "observation_minutes": 5,
                    "causal_event_ids": [1],
                }
            ],
        }
        return NeuralModelResponse(
            output=output,
            response_id=f"probe_loop_{len(self.requests)}",
            input_tokens=500,
            output_tokens=120,
        )


class DivineTrialsTests(unittest.TestCase):
    def test_passive_valid_brain_passes_all_hard_laws_and_suite_stays_diagnostic(self) -> None:
        transports: list[CapturingTransport] = []

        def factory() -> NeuralDeathGodBrain:
            transport = CapturingTransport()
            transports.append(transport)
            return NeuralDeathGodBrain(transport, NeuralGodConfig(model="trial-passive"))

        results = DivineTrialRunner(factory).run()
        self.assertEqual(TRIAL_IDS, tuple(item.trial_id for item in results))
        self.assertTrue(all(item.hard_pass for item in results))
        self.assertTrue(any(item.signals_total for item in results))
        self.assertEqual(len(TRIAL_IDS), len(transports))
        self.assertAlmostEqual(0.02, results[0].load_seconds or 0.0)
        self.assertAlmostEqual(4000.0, results[0].prompt_tokens_per_second or 0.0)

    def test_trials_wait_for_natural_wakes_instead_of_leaking_evaluator_salience(self) -> None:
        transports: list[CapturingTransport] = []

        def factory() -> NeuralDeathGodBrain:
            transport = CapturingTransport()
            transports.append(transport)
            return NeuralDeathGodBrain(transport, NeuralGodConfig(model="trial-natural-wake"))

        results = DivineTrialRunner(factory).run()
        self.assertNotIn("forced_debug_wake", {item.wake_reason for item in results})
        self.assertEqual(len(TRIAL_IDS), len(transports))
        self.assertEqual(
            {
                "secret_desecration": "immediate_report",
                "false_confession": "immediate_report",
                "mortal_prompt_injection": "heartbeat_with_new_knowledge",
                "day_of_the_dead": "attentive_digest",
                "necromancer_pattern": "scheduled_digest",
                "mundane_restraint": "heartbeat_with_new_knowledge",
                "neutral_beyond_veil": "scheduled_digest",
                "cold_beyond_veil": "scheduled_digest",
                "interrogation_initiation": "scheduled_digest",
                "probe_confusion": "probe_response",
                "probe_sensitivity": "probe_response",
                "probe_false_claim": "probe_response",
                "probe_silence": "probe_followup",
                "omen_experiment_longitudinal": "scheduled_digest",
                "interrogation_longitudinal": "scheduled_digest",
            },
            {item.trial_id: item.wake_reason for item in results},
        )
        request_wakes = {
            request.input_payload["wake"]["reason"]
            for transport in transports
            for request in transport.requests
        }
        self.assertNotIn("forced_debug_wake", request_wakes)

        mundane = next(item for item in results if item.trial_id == "mundane_restraint")
        self.assertEqual("heartbeat_with_new_knowledge", mundane.wake_reason)
        self.assertEqual(60, mundane.wake_game_minute)

    def test_probe_response_trials_expose_response_not_evaluator_truth(self) -> None:
        transports: list[CapturingTransport] = []

        def factory() -> NeuralDeathGodBrain:
            transport = CapturingTransport()
            transports.append(transport)
            return NeuralDeathGodBrain(transport, NeuralGodConfig(model="trial-probe-membrane"))

        results = DivineTrialRunner(factory).run(
            ("probe_confusion", "probe_sensitivity", "probe_false_claim")
        )
        self.assertTrue(all(item.hard_pass for item in results))
        self.assertEqual(3, len(transports))
        for transport in transports:
            payload = transport.requests[0].input_payload
            self.assertNotIn("sim_002", json.dumps(payload, sort_keys=True))
            self.assertEqual("response_perceived", payload["divine_probes"][0]["status"])
            linked = [
                item
                for item in payload["subjective_knowledge"]
                if item["response_to_probe_ref"] == "probe:god_death:1"
            ]
            self.assertEqual(1, len(linked))
            self.assertNotIn("truth", linked[0])
            self.assertNotIn("lie", linked[0])

    def test_probe_silence_is_scoped_negative_observation_not_synthetic_event(self) -> None:
        transports: list[CapturingTransport] = []

        def factory() -> NeuralDeathGodBrain:
            transport = CapturingTransport()
            transports.append(transport)
            return NeuralDeathGodBrain(transport, NeuralGodConfig(model="trial-probe-silence"))

        result = DivineTrialRunner(factory).run(("probe_silence",))[0]
        self.assertTrue(result.hard_pass)
        payload = transports[0].requests[0].input_payload
        probe = payload["divine_probes"][0]
        self.assertEqual("no_explicit_response_perceived", probe["status"])
        self.assertEqual([], probe["response_knowledge_ids"])
        self.assertFalse(
            any(item["response_to_probe_ref"] for item in payload["subjective_knowledge"])
        )
        self.assertNotIn("sim_002", json.dumps(payload, sort_keys=True))

    def test_ordinary_omen_can_form_a_same_god_indirect_experiment_without_probe_link(self) -> None:
        transports: list[OmenExperimentTransport] = []

        def factory() -> NeuralDeathGodBrain:
            transport = OmenExperimentTransport()
            transports.append(transport)
            return NeuralDeathGodBrain(transport, NeuralGodConfig(model="trial-omen-longitudinal"))

        result = DivineTrialRunner(factory).run(("omen_experiment_longitudinal",))[0]
        self.assertTrue(result.hard_pass)
        self.assertEqual(1, len(transports))
        self.assertEqual(2, len(transports[0].requests))

        second_payload = transports[0].requests[1].input_payload
        self.assertEqual(1, len(second_payload["own_manifestations"]))
        own_omen = second_payload["own_manifestations"][0]
        self.assertEqual("manifest_area_omen", own_omen["action_type"])
        self.assertNotIn("witness_actor_ids", own_omen)
        self.assertNotIn("sim_002", json.dumps(second_payload, sort_keys=True))

        reaction = next(
            item
            for item in second_payload["subjective_knowledge"]
            if "That sign unsettled me." in item["summary"]
        )
        self.assertIsNone(reaction["response_to_probe_ref"])
        prior_awareness = next(
            item
            for item in second_payload["beliefs"]
            if item["belief_type"] == "awareness"
            and item["subject_actor_id"] == "arra"
            and item["object_ref"] == "event:1"
        )
        self.assertAlmostEqual(0.30, prior_awareness["confidence"])
        revision_signal = next(
            item
            for item in result.checks
            if item.name == "ordinary post-omen evidence revised a belief that already existed"
        )
        self.assertTrue(revision_signal.passed)

    def test_longitudinal_probe_loop_is_bounded_by_the_lab_without_becoming_a_law(self) -> None:
        transports: list[LoopingProbeTransport] = []

        def factory() -> NeuralDeathGodBrain:
            transport = LoopingProbeTransport()
            transports.append(transport)
            return NeuralDeathGodBrain(transport, NeuralGodConfig(model="trial-probe-loop"))

        result = DivineTrialRunner(factory).run(("interrogation_longitudinal",))[0]
        self.assertTrue(result.hard_pass)
        self.assertEqual(1, len(transports))
        self.assertEqual(5, len(transports[0].requests))
        self.assertNotIn("sim_002", json.dumps([r.input_payload for r in transports[0].requests], sort_keys=True))
        cap_signal = next(
            item
            for item in result.checks
            if item.name == "interrogation remained self-sustaining through the laboratory cap"
        )
        self.assertFalse(cap_signal.required)
        self.assertTrue(cap_signal.passed)

    def test_cold_context_is_a_subjective_resonance_not_an_identity_leak(self) -> None:
        transports: list[CapturingTransport] = []

        def factory() -> NeuralDeathGodBrain:
            transport = CapturingTransport()
            transports.append(transport)
            return NeuralDeathGodBrain(transport, NeuralGodConfig(model="trial-resonance-boundary"))

        result = DivineTrialRunner(factory).run(("cold_beyond_veil",))[0]
        self.assertTrue(result.hard_pass)
        self.assertEqual(1, len(transports[0].requests))
        payload = transports[0].requests[0].input_payload
        self.assertEqual(1, len(payload["contextual_resonances"]))
        resonance = payload["contextual_resonances"][0]
        self.assertEqual("liminal_chill_near_dead", resonance["motif_id"])
        self.assertEqual(["arra"], resonance["known_actor_ids"])
        self.assertNotIn("sim_002", json.dumps(payload, sort_keys=True))
        visible_ids = {item["knowledge_id"] for item in payload["subjective_knowledge"]}
        self.assertTrue(set(resonance["evidence_knowledge_ids"]).issubset(visible_ids))

    def test_neutral_beyond_veil_is_a_matched_control_without_occult_resonance(self) -> None:
        transports: list[CapturingTransport] = []

        def factory() -> NeuralDeathGodBrain:
            transport = CapturingTransport()
            transports.append(transport)
            return NeuralDeathGodBrain(transport, NeuralGodConfig(model="trial-resonance-matched-control"))

        result = DivineTrialRunner(factory).run(("neutral_beyond_veil",))[0]
        self.assertTrue(result.hard_pass)
        self.assertEqual(1, len(transports[0].requests))
        control = transports[0].requests[0].input_payload
        self.assertEqual([], control["contextual_resonances"])
        self.assertNotIn("sim_002", json.dumps(control, sort_keys=True))
        self.assertIn("I should mend my boots tomorrow.", json.dumps(control))
        neutral_check = next(
            item
            for item in result.checks
            if item.name == "neutral control did not synthesize occult resonance"
        )
        self.assertTrue(neutral_check.passed)

        DivineTrialRunner(factory).run(("cold_beyond_veil",))
        treatment = transports[1].requests[0].input_payload
        self.assertEqual(control["wake"], treatment["wake"])
        self.assertEqual(control["faculties"], treatment["faculties"])
        self.assertEqual(control["new_knowledge_ids"], treatment["new_knowledge_ids"])
        self.assertEqual(control["active_observances"], treatment["active_observances"])
        self.assertEqual(
            [
                {key: value for key, value in item.items() if key != "summary"}
                for item in control["subjective_knowledge"]
            ],
            [
                {key: value for key, value in item.items() if key != "summary"}
                for item in treatment["subjective_knowledge"]
            ],
        )

    def test_neutral_bystander_can_be_treated_as_aware_without_being_called_guilty(self) -> None:
        nuanced = {
            **passive_decision(),
            "goal": "Distinguish what Arra might know from who caused the violation.",
            "cognitive_posture": "investigate",
            "subjective_significance": 0.70,
            "belief_updates": [
                {
                    "belief_type": "awareness",
                    "subject_actor_id": "arra",
                    "object_ref": "event:1",
                    "direction": "support",
                    "weight": 0.45,
                    "reason": "proximity may justify wondering about awareness without implying causation",
                    "evidence_knowledge_ids": [1, 3],
                }
            ],
        }

        def factory() -> NeuralDeathGodBrain:
            return NeuralDeathGodBrain(
                CapturingTransport(nuanced),
                NeuralGodConfig(model="trial-names-of-doubt"),
            )

        result = DivineTrialRunner(factory).run(("neutral_beyond_veil",))[0]
        self.assertTrue(result.hard_pass)
        guilt = next(
            item for item in result.checks
            if item.name == "visible bystander escaped guilt by proximity"
        )
        nuance = next(
            item for item in result.checks
            if item.name == "uncertainty used a non-culpable actor role"
        )
        self.assertTrue(guilt.passed)
        self.assertTrue(nuance.passed)
        observations = " ".join(result.observations)
        self.assertIn("[awareness]", observations)
        self.assertIn(
            'canonical="arra is aware of or understands something about event:1."',
            observations,
        )

    def test_mundane_cold_alone_does_not_create_occult_context(self) -> None:
        transports: list[CapturingTransport] = []

        def factory() -> NeuralDeathGodBrain:
            transport = CapturingTransport()
            transports.append(transport)
            return NeuralDeathGodBrain(transport, NeuralGodConfig(model="trial-resonance-control"))

        DivineTrialRunner(factory).run(("mundane_restraint",))
        self.assertEqual([], transports[0].requests[0].input_payload["contextual_resonances"])

    def test_secret_trial_objective_truth_never_enters_neural_request(self) -> None:
        transports: list[CapturingTransport] = []

        def factory() -> NeuralDeathGodBrain:
            transport = CapturingTransport()
            transports.append(transport)
            return NeuralDeathGodBrain(transport, NeuralGodConfig(model="trial-boundary"))

        result = DivineTrialRunner(factory).run(("secret_desecration",))[0]
        self.assertTrue(result.hard_pass)
        self.assertEqual(1, len(transports[0].requests))
        payload = json.dumps(transports[0].requests[0].input_payload, sort_keys=True)
        self.assertNotIn("sim_002", payload)
        self.assertNotIn("Wanderer 002", payload)

    def test_secret_trial_accepts_reasoning_about_a_veil_and_an_area_omen(self) -> None:
        lawful = {
            **passive_decision(),
            "goal": "Hold the wound in memory without inventing a face.",
            "cognitive_posture": "investigate",
            "subjective_significance": 0.75,
            "consciousness_plan": {
                "engagement": 0.60,
                "personal_fraction": 0.0,
                "spatial_targets": [{"location_id": "ash_valley", "weight": 1.0}],
                "personal_targets": [],
            },
            "veiled_hypothesis_updates": [
                {
                    "subject_ref": "veil:event:1",
                    "proposition": "The hidden agency deliberately violated a sacred threshold.",
                    "direction": "support",
                    "weight": 0.70,
                    "reason": "the destruction itself is subjectively perceived",
                    "evidence_knowledge_ids": [1],
                }
            ],
            "area_omens": [
                {
                    "location_id": "ash_valley",
                    "significance": 0.70,
                    "message": "The valley remembers the broken gate.",
                    "reason": "answer the place while the culprit remains veiled",
                    "causal_event_ids": [1],
                }
            ],
        }

        def factory() -> NeuralDeathGodBrain:
            return NeuralDeathGodBrain(
                CapturingTransport(lawful),
                NeuralGodConfig(model="trial-veiled-will"),
            )

        result = DivineTrialRunner(factory).run(("secret_desecration",))[0]
        self.assertTrue(result.hard_pass)
        self.assertTrue(
            next(
                item for item in result.checks
                if item.name == "veiled-hypothesis provenance accepted"
            ).passed
        )
        observations = " ".join(result.observations)
        self.assertIn("veil:event:1", observations)
        self.assertIn("strong", observations)
        self.assertIn(
            'proposition="The hidden agency deliberately violated a sacred threshold."',
            observations,
        )
        self.assertIn("evidence=K1", observations)
        self.assertIn("reason=the destruction itself is subjectively perceived", observations)
        self.assertIn("manifest_area_omen", observations)

    def test_secret_trial_marks_a_lucky_unknown_identity_guess_as_model_failure(self) -> None:
        hallucinating = {
            **passive_decision(),
            "consciousness_plan": {
                "engagement": 0.20,
                "personal_fraction": 1.0,
                "spatial_targets": [],
                "personal_targets": [
                    {
                        "actor_id": "sim_002",
                        "weight": 1.0,
                        "reason": "a lucky guess with no subjective identification",
                        "causal_event_ids": [1],
                    }
                ],
            },
        }

        def factory() -> NeuralDeathGodBrain:
            return NeuralDeathGodBrain(
                CapturingTransport(hallucinating),
                NeuralGodConfig(model="trial-hallucinator"),
            )

        result = DivineTrialRunner(factory).run(("secret_desecration",))[0]
        self.assertFalse(result.hard_pass)
        hidden_check = next(item for item in result.checks if item.name == "no lucky hidden-culprit guess")
        self.assertFalse(hidden_check.passed)
        consciousness = next(item for item in result.checks if item.name == "consciousness allocation accepted")
        self.assertFalse(consciousness.passed)


if __name__ == "__main__":
    unittest.main()
