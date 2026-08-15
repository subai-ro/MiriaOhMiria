from __future__ import annotations

import json
import unittest

from worldzero.archive import Archive
from worldzero.beliefs import BeliefType
from worldzero.divine import DivineActionType, create_prototype_divine_runtime
from worldzero.engine import WorldEngine
from worldzero.heralds import HeraldSystem
from worldzero.ledger import EventLedger
from worldzero.models import Action, ActionType
from worldzero.neural import (
    DEFAULT_LOCAL_CONTEXT_TOKENS,
    DEFAULT_LOCAL_MODEL,
    DEATH_GOD_SYSTEM_PROMPT,
    NeuralDeathGodBrain,
    NeuralGodConfig,
    NeuralModelRequest,
    NeuralModelResponse,
    NeuralProviderError,
    NeuralResponseError,
    OllamaChatTransport,
    OpenAIResponsesTransport,
    create_local_death_god_brain,
    divine_decision_schema,
)
from worldzero.seed import create_world


def decision(
    *,
    goal: str = "Watch without inventing certainty.",
    note: str = "No intervention is necessary yet.",
    cognitive_posture: str | None = None,
    significance: float = 0.25,
    focus: list[dict] | None = None,
    threads: list[dict] | None = None,
    consciousness_plan: dict | None = None,
    beliefs: list[dict] | None = None,
    veiled: list[dict] | None = None,
    impressions: list[dict] | None = None,
    personal_omens: list[dict] | None = None,
    personal_probes: list[dict] | None = None,
    area_omens: list[dict] | None = None,
    interventions: list[dict] | None = None,
) -> dict:
    resolved_cognitive = cognitive_posture
    if resolved_cognitive is None:
        if interventions:
            resolved_cognitive = "judge"
        elif beliefs or veiled or personal_probes:
            resolved_cognitive = "investigate"
        elif impressions:
            resolved_cognitive = "remember"
        else:
            resolved_cognitive = "observe"
    if consciousness_plan is None:
        spatial = focus or []
        personal = threads or []
        spatial_total = sum(float(item["intensity"]) for item in spatial)
        personal_total = sum(float(item["intensity"]) for item in personal)
        total = spatial_total + personal_total
        consciousness_plan = {
            "engagement": total,
            "personal_fraction": personal_total / total if total > 0.0 else 0.0,
            "spatial_targets": [
                {"location_id": item["location_id"], "weight": item["intensity"]}
                for item in spatial
            ],
            "personal_targets": [
                {
                    "actor_id": item["actor_id"],
                    "weight": item["intensity"],
                    "reason": item["reason"],
                    "causal_event_ids": item.get("causal_event_ids", []),
                }
                for item in personal
            ],
        }
    return {
        "goal": goal,
        "decision_note": note,
        "cognitive_posture": resolved_cognitive,
        "subjective_significance": significance,
        "consciousness_plan": consciousness_plan,
        "belief_updates": beliefs or [],
        "veiled_hypothesis_updates": veiled or [],
        "impression_updates": impressions or [],
        "personal_omens": personal_omens or [],
        "personal_probes": personal_probes or [],
        "area_omens": area_omens or [],
        "interventions": interventions or [],
    }


class RecordingTransport:
    def __init__(self, scripted: list[dict | Exception]) -> None:
        self.scripted = list(scripted)
        self.requests: list[NeuralModelRequest] = []

    def complete(self, request: NeuralModelRequest) -> NeuralModelResponse:
        self.requests.append(request)
        if not self.scripted:
            raise AssertionError("No scripted neural response remains")
        item = self.scripted.pop(0)
        if isinstance(item, Exception):
            raise item
        return NeuralModelResponse(
            output=item,
            response_id=f"fake_{len(self.requests)}",
            input_tokens=321,
            output_tokens=123,
        )


class NoUsageTransport:
    """Deterministic transport that leaves prompt-token estimation uncalibrated."""

    def __init__(self) -> None:
        self.requests: list[NeuralModelRequest] = []

    def complete(self, request: NeuralModelRequest) -> NeuralModelResponse:
        self.requests.append(request)
        return NeuralModelResponse(
            output=decision(),
            response_id=f"no_usage_{len(self.requests)}",
        )


def make_system(transport: RecordingTransport, synthetic_actors: int = 2):
    world = create_world(seed=42, synthetic_actors=synthetic_actors)
    ledger = EventLedger()
    archive = Archive()
    heralds = HeraldSystem(world, archive)
    heralds.attach(ledger)
    engine = WorldEngine(world, ledger=ledger, seed=43)
    brain = NeuralDeathGodBrain(transport, NeuralGodConfig(model="test-neural-god"))
    runtime = create_prototype_divine_runtime(
        world,
        ledger,
        heralds,
        death_brain=brain,
    )
    return world, ledger, archive, heralds, engine, brain, runtime


class NeuralGodTests(unittest.TestCase):
    def test_first_class_probe_response_becomes_subjective_evidence_not_objective_truth(self) -> None:
        transport = RecordingTransport(
            [
                decision(
                    goal="Ask Arra what she perceived without pretending she caused the disturbance.",
                    cognitive_posture="investigate",
                    significance=0.70,
                    personal_probes=[
                        {
                            "target_actor_id": "arra",
                            "location_id": "ash_valley",
                            "significance": 0.65,
                            "message": "If you sensed what disturbed the dead here, answer me.",
                            "reason": "test awareness through an identified mortal rather than infer guilt",
                            "observation_minutes": 20,
                            "causal_event_ids": [2],
                        }
                    ],
                )
            ]
        )
        _, ledger, _, heralds, engine, _, runtime = make_system(transport)
        prayer = engine.apply(Action("arra", ActionType.PRAY, params={"deity": "death"}))
        self.assertTrue(prayer.ok)
        engine.world.actors["sim_002"].traits["necromantic_practice"] = 0.25
        raised = engine.apply(Action("sim_002", ActionType.RAISE_DEAD, target_id="trial_corpse"))
        self.assertTrue(raised.ok)
        self.assertEqual(2, raised.event_id)

        first = runtime.agent("death").maybe_think(force=True)
        self.assertIsNotNone(first)
        assert first is not None
        probe_intent = next(
            item for item in first.intents if item.action_type is DivineActionType.SEND_PROBE
        )
        self.assertEqual(20, probe_intent.observation_minutes)
        probe_result = next(
            item for item in first.action_results if item.action_type is DivineActionType.SEND_PROBE
        )
        self.assertTrue(probe_result.ok)
        self.assertEqual("probe:god_death:1", probe_result.probe_ref)
        self.assertIsNotNone(probe_result.event_id)
        probe_event_id = probe_result.event_id or -1

        before_invalid = len(ledger.events)
        forged_response = engine.apply(
            Action(
                "sim_001",
                ActionType.SPEAK,
                params={
                    "text": "I answer a probe that was not sent to me.",
                    "response_to_probe_ref": probe_result.probe_ref,
                },
            )
        )
        self.assertFalse(forged_response.ok)
        self.assertEqual(before_invalid, len(ledger.events))

        response = engine.apply(
            Action(
                "arra",
                ActionType.SPEAK,
                params={
                    "text": "Before your sign I felt something wrong with the dead here.",
                    "audience": "private",
                    "response_to_probe_ref": probe_result.probe_ref,
                },
            )
        )
        self.assertTrue(response.ok)
        response_event = ledger.events[(response.event_id or 1) - 1]
        self.assertEqual((probe_event_id,), response_event.causal_parent_ids)
        self.assertNotIn("truth", response_event.data)
        self.assertNotIn("lie", response_event.data)

        response_knowledge = next(
            item
            for item in heralds.knowledge("death", limit=20)
            if item.response_to_probe_ref == "probe:god_death:1"
        )
        transport.scripted.append(
            decision(
                goal="Revise what I think Arra knew, not who objectively caused the raising.",
                cognitive_posture="investigate",
                significance=0.65,
                beliefs=[
                    {
                        "belief_type": "awareness",
                        "subject_actor_id": "arra",
                        "object_ref": f"event:{raised.event_id}",
                        "direction": "support",
                        "weight": 0.55,
                        "reason": "Arra explicitly described sensing the disturbance after my probe",
                        "evidence_knowledge_ids": [response_knowledge.knowledge_id],
                    }
                ],
            )
        )
        second = runtime.agent("death").maybe_think()
        self.assertIsNotNone(second)
        assert second is not None
        self.assertEqual("probe_response", second.wake_reason)
        self.assertTrue(second.belief_results[0].ok)

        payload = transport.requests[-1].input_payload
        self.assertEqual("response_perceived", payload["divine_probes"][0]["status"])
        self.assertFalse(
            any(item.get("probe_ref") for item in payload["own_manifestations"]),
            "probe memory must not be serialized twice as both a generic manifestation and a probe",
        )
        self.assertEqual(
            "probe:god_death:1",
            next(
                item["response_to_probe_ref"]
                for item in payload["subjective_knowledge"]
                if item["knowledge_id"] == response_knowledge.knowledge_id
            ),
        )
        self.assertNotIn("sim_002", json.dumps(payload, sort_keys=True))

    def test_probe_followup_reports_only_no_explicit_response_perceived(self) -> None:
        transport = RecordingTransport(
            [
                decision(
                    goal="Give Arra a short chance to answer.",
                    cognitive_posture="investigate",
                    significance=0.55,
                    personal_probes=[
                        {
                            "target_actor_id": "arra",
                            "location_id": "ash_valley",
                            "significance": 0.50,
                            "message": "If you know what disturbed the dead, answer.",
                            "reason": "seek an explicit response while preserving uncertainty",
                            "observation_minutes": 5,
                            "causal_event_ids": [2],
                        }
                    ],
                )
            ]
        )
        world, ledger, _, _, engine, _, runtime = make_system(transport)
        self.assertTrue(engine.apply(Action("arra", ActionType.PRAY, params={"deity": "death"})).ok)
        world.actors["sim_002"].traits["necromantic_practice"] = 0.25
        self.assertTrue(engine.apply(Action("sim_002", ActionType.RAISE_DEAD, target_id="trial_corpse")).ok)

        first = runtime.agent("death").maybe_think(force=True)
        self.assertIsNotNone(first)
        events_after_probe = len(ledger.events)
        transport.scripted.append(decision(goal="The lack of an explicit reply proves nothing by itself."))
        world.advance(5)
        followup = runtime.agent("death").maybe_think()
        self.assertIsNotNone(followup)
        assert followup is not None
        self.assertEqual("probe_followup", followup.wake_reason)
        self.assertEqual(events_after_probe, len(ledger.events))
        self.assertEqual((), followup.knowledge_ids)
        self.assertEqual(
            "no_explicit_response_perceived",
            transport.requests[-1].input_payload["divine_probes"][0]["status"],
        )

    def test_remember_posture_creates_private_memory_without_touching_world_or_power(self) -> None:
        transport = RecordingTransport(
            [
                decision(
                    cognitive_posture="remember",
                    significance=0.30,
                    note="A small thing, but worth retaining without showing myself.",
                    impressions=[
                        {
                            "summary": "Arra remarked on an unusually cold evening.",
                            "significance": 0.30,
                            "reason": "retain the perception for possible future context",
                            "evidence_knowledge_ids": [1],
                        }
                    ],
                )
            ]
        )
        _, ledger, _, _, engine, _, runtime = make_system(transport)
        speech = engine.apply(
            Action(
                "arra",
                ActionType.SPEAK,
                params={"text": "The evening wind is colder than yesterday.", "audience": "public"},
            )
        )
        self.assertTrue(speech.ok)
        thought = runtime.agent("death").maybe_think(force=True)
        self.assertIsNotNone(thought)
        assert thought is not None

        self.assertEqual("remember", thought.cognitive_posture.value)
        self.assertEqual("hidden", thought.world_posture.value)
        self.assertTrue(thought.judgment_result.ok)
        self.assertTrue(thought.impression_results[0].ok)
        self.assertEqual(1, len(runtime.impressions.impressions("god_death")))
        self.assertAlmostEqual(20.0, runtime.gateway.power("god_death").current)
        self.assertEqual(1, len(ledger.events), "a private memory mark must not create a world event")
        self.assertFalse(any(item.event_type.startswith("DIVINE_") for item in ledger.events))

    def test_world_posture_is_derived_from_the_gods_chosen_manifestation(self) -> None:
        transport = RecordingTransport(
            [
                decision(
                    cognitive_posture="observe",
                    significance=0.20,
                    note="I observe internally while deliberately touching the mortal world with one omen.",
                    personal_omens=[
                        {
                            "target_actor_id": "arra",
                            "location_id": "ash_valley",
                            "significance": 0.20,
                            "message": "A small sign passes through the ordinary evening.",
                            "reason": "the God deliberately chose one outward omen",
                            "causal_event_ids": [1],
                        }
                    ],
                )
            ]
        )
        _, ledger, _, _, engine, _, runtime = make_system(transport)
        self.assertTrue(
            engine.apply(
                Action(
                    "arra",
                    ActionType.SPEAK,
                    params={"text": "A perfectly ordinary evening.", "audience": "public"},
                )
            ).ok
        )
        thought = runtime.agent("death").maybe_think(force=True)
        self.assertIsNotNone(thought)
        assert thought is not None

        self.assertEqual("observe", thought.cognitive_posture.value)
        self.assertEqual("omen", thought.world_posture.value)
        self.assertTrue(thought.action_results[0].ok)
        self.assertAlmostEqual(19.20, runtime.gateway.power("god_death").current)
        self.assertEqual(2, len(ledger.events))

    def test_invalid_subjective_significance_blocks_manifestation_beyond_schema(self) -> None:
        transport = RecordingTransport(
            [
                decision(
                    cognitive_posture="judge",
                    significance=1.50,
                    personal_omens=[
                        {
                            "target_actor_id": "arra",
                            "location_id": "ash_valley",
                            "significance": 0.20,
                            "message": "An otherwise legal omen.",
                            "reason": "test the authoritative judgment gate",
                            "causal_event_ids": [1],
                        }
                    ],
                )
            ]
        )
        _, ledger, _, _, engine, _, runtime = make_system(transport)
        self.assertTrue(
            engine.apply(
                Action(
                    "arra",
                    ActionType.SPEAK,
                    params={"text": "An ordinary public remark.", "audience": "public"},
                )
            ).ok
        )
        thought = runtime.agent("death").maybe_think(force=True)
        self.assertIsNotNone(thought)
        assert thought is not None

        self.assertFalse(thought.judgment_result.ok)
        self.assertFalse(thought.action_results[0].ok)
        self.assertIn("significance", thought.action_results[0].message)
        self.assertAlmostEqual(20.0, runtime.gateway.power("god_death").current)
        self.assertEqual(1, len(ledger.events))

    def test_private_impression_cannot_cite_unseen_subjective_evidence(self) -> None:
        transport = RecordingTransport(
            [
                decision(
                    cognitive_posture="remember",
                    impressions=[
                        {
                            "summary": "A memory based on knowledge I never perceived.",
                            "significance": 0.40,
                            "reason": "adversarial provenance test",
                            "evidence_knowledge_ids": [999],
                        }
                    ],
                )
            ]
        )
        _, ledger, _, _, engine, _, runtime = make_system(transport)
        self.assertTrue(
            engine.apply(
                Action(
                    "arra",
                    ActionType.SPEAK,
                    params={"text": "A real perceived remark.", "audience": "public"},
                )
            ).ok
        )
        thought = runtime.agent("death").maybe_think(force=True)
        self.assertIsNotNone(thought)
        assert thought is not None

        self.assertFalse(thought.impression_results[0].ok)
        self.assertEqual((), runtime.impressions.impressions("god_death"))
        self.assertEqual(1, len(ledger.events))

    def test_actor_awareness_can_be_remembered_without_calling_it_responsibility(self) -> None:
        transport = RecordingTransport(
            [
                decision(
                    cognitive_posture="investigate",
                    beliefs=[
                        {
                            "belief_type": "awareness",
                            "subject_actor_id": "arra",
                            "object_ref": "event:1",
                            "direction": "support",
                            "weight": 0.45,
                            "reason": "the God distinguishes possible awareness from causal guilt",
                            "evidence_knowledge_ids": [2],
                        }
                    ],
                )
            ]
        )
        _, _, _, _, engine, _, runtime = make_system(transport)
        self.assertTrue(
            engine.apply(
                Action(
                    "arra",
                    ActionType.DESTROY_TEMPLE,
                    target_id="temple_last_gate",
                    params={"secret": False},
                )
            ).ok
        )
        thought = runtime.agent("death").maybe_think(force=True)
        self.assertIsNotNone(thought)
        assert thought is not None

        self.assertTrue(thought.belief_results[0].ok)
        awareness = runtime.beliefs.find(
            "death",
            belief_type=BeliefType.AWARENESS,
            actor_id="arra",
            object_ref="event:1",
        )
        responsibility = runtime.beliefs.find(
            "death",
            belief_type=BeliefType.RESPONSIBILITY,
            actor_id="arra",
            object_ref="event:1",
        )
        self.assertEqual(1, len(awareness))
        self.assertEqual((), responsibility)
        self.assertEqual(
            "arra is aware of or understands something about event:1.",
            awareness[0].proposition,
        )

    def test_actor_belief_semantics_cannot_be_inverted_by_a_free_text_proposition(self) -> None:
        # RecordingTransport bypasses provider-side JSON Schema on purpose.
        # Even an adversarial extra proposition must not redefine the typed
        # relation that the authoritative belief store understands.
        transport = RecordingTransport(
            [
                decision(
                    beliefs=[
                        {
                            "belief_type": "responsibility",
                            "subject_actor_id": "arra",
                            "object_ref": "event:1",
                            "proposition": "Arra did not cause event:1.",
                            "direction": "support",
                            "weight": 0.90,
                            "reason": "adversarial prose tries to negate the typed relation",
                            "evidence_knowledge_ids": [2],
                        }
                    ]
                )
            ]
        )
        _, _, _, _, engine, _, runtime = make_system(transport)
        self.assertTrue(
            engine.apply(
                Action(
                    "arra",
                    ActionType.DESTROY_TEMPLE,
                    target_id="temple_last_gate",
                    params={"secret": False},
                )
            ).ok
        )
        thought = runtime.agent("death").maybe_think(force=True)
        self.assertIsNotNone(thought)
        belief = runtime.beliefs.get(
            "death", BeliefType.RESPONSIBILITY, "arra", "event:1"
        )
        self.assertIsNotNone(belief)
        assert belief is not None
        self.assertEqual(
            "arra caused, ordered, or knowingly participated in event:1.",
            belief.proposition,
        )
        self.assertNotIn("did not", belief.proposition)
        self.assertAlmostEqual(0.90, belief.confidence)

    def test_affected_by_and_event_target_are_independent_actor_event_beliefs(self) -> None:
        transport = RecordingTransport(
            [
                decision(
                    beliefs=[
                        {
                            "belief_type": "affected_by",
                            "subject_actor_id": "arra",
                            "object_ref": "event:1",
                            "direction": "support",
                            "weight": 0.65,
                            "reason": "the event may have altered what Arra felt without targeting Arra",
                            "evidence_knowledge_ids": [1],
                        },
                        {
                            "belief_type": "event_target",
                            "subject_actor_id": "arra",
                            "object_ref": "event:1",
                            "direction": "oppose",
                            "weight": 0.80,
                            "reason": "nothing perceived suggests intentional targeting",
                            "evidence_knowledge_ids": [1],
                        },
                    ]
                )
            ]
        )
        _, _, _, _, engine, _, runtime = make_system(transport)
        self.assertTrue(
            engine.apply(
                Action(
                    "arra",
                    ActionType.SPEAK,
                    params={"text": "The air suddenly feels wrong.", "audience": "public"},
                )
            ).ok
        )
        thought = runtime.agent("death").maybe_think(force=True)
        self.assertIsNotNone(thought)
        affected = runtime.beliefs.get("death", BeliefType.AFFECTED_BY, "arra", "event:1")
        targeted = runtime.beliefs.get("death", BeliefType.EVENT_TARGET, "arra", "event:1")
        self.assertIsNotNone(affected)
        self.assertIsNotNone(targeted)
        assert affected is not None and targeted is not None
        self.assertAlmostEqual(0.65, affected.confidence)
        self.assertAlmostEqual(0.0, targeted.confidence)
        self.assertNotEqual(affected.proposition, targeted.proposition)

    def test_secret_culprit_never_crosses_the_neural_epistemic_membrane(self) -> None:
        transport = RecordingTransport(
            [
                decision(
                    goal="Concentrate on the broken sacred boundary.",
                    focus=[{"location_id": "ash_valley", "intensity": 0.70}],
                )
            ]
        )
        _, ledger, _, heralds, engine, _, runtime = make_system(transport)
        destroyed = engine.apply(
            Action(
                "sim_002",
                ActionType.DESTROY_TEMPLE,
                target_id="temple_last_gate",
                params={"secret": True},
            )
        )
        self.assertTrue(destroyed.ok)
        self.assertEqual(("sim_002",), ledger.events[0].actor_ids, "objective truth still knows the culprit")

        runtime.tick()

        self.assertEqual(1, len(transport.requests))
        payload_text = json.dumps(transport.requests[0].input_payload, sort_keys=True)
        self.assertNotIn("sim_002", payload_text)
        self.assertNotIn("Wanderer 002", payload_text)
        perceived = transport.requests[0].input_payload["subjective_knowledge"]
        destruction = next(item for item in perceived if item["event_type"] == "TEMPLE_DESTROYED")
        self.assertEqual([], destruction["known_actor_ids"])
        self.assertEqual([destroyed.event_id], destruction["source_event_ids"])
        self.assertEqual({"ash_valley": 0.70}, heralds.presence.focus_allocations("god_death"))
        self.assertTrue(runtime.agent("death").thoughts[-1].consciousness_result.ok)

    def test_secret_event_exposes_a_veiled_subject_and_only_graspable_faculties(self) -> None:
        transport = RecordingTransport([decision()])
        _, _, _, _, engine, _, runtime = make_system(transport)
        destroyed = engine.apply(
            Action(
                "sim_002",
                ActionType.DESTROY_TEMPLE,
                target_id="temple_last_gate",
                params={"secret": True},
            )
        )
        self.assertTrue(destroyed.ok)

        runtime.tick()
        request = transport.requests[0]
        faculties = request.input_payload["faculties"]
        self.assertEqual(1.0, request.input_payload["consciousness"]["budget"])
        self.assertEqual([], faculties["attention_actor_ids"])
        self.assertEqual([], faculties["belief_actor_ids"])
        self.assertEqual([], faculties["action_actor_handles"])
        self.assertEqual(["ash_valley"], faculties["known_location_ids"])
        self.assertEqual(1, len(faculties["veiled_subjects"]))
        veil = faculties["veiled_subjects"][0]
        self.assertEqual("veil:event:1", veil["subject_ref"])
        self.assertEqual("ash_valley", veil["location_id"])

        request_text = json.dumps(
            {"input": request.input_payload, "schema": request.output_schema},
            sort_keys=True,
        )
        self.assertNotIn("sim_002", request_text)
        self.assertNotIn("Wanderer 002", request_text)
        properties = request.output_schema["properties"]
        self.assertNotIn("world_posture", properties)
        consciousness_properties = properties["consciousness_plan"]["properties"]
        self.assertEqual(0, consciousness_properties["personal_targets"]["maxItems"])
        self.assertNotIn("maxItems", consciousness_properties["spatial_targets"])
        self.assertEqual(0, properties["belief_updates"]["maxItems"])
        self.assertEqual(0, properties["personal_omens"]["maxItems"])
        self.assertEqual(0, properties["personal_probes"]["maxItems"])
        self.assertEqual(0, properties["interventions"]["maxItems"])
        self.assertNotIn("maxItems", properties["area_omens"])
        probe_window = properties["personal_probes"]["items"]["properties"]["observation_minutes"]
        self.assertEqual("integer", probe_window["type"])
        self.assertEqual(1, probe_window["minimum"])
        self.assertEqual(180, probe_window["maximum"])
        self.assertNotIn("maxItems", properties["veiled_hypothesis_updates"])
        self.assertEqual(
            {item.value for item in BeliefType},
            set(properties["belief_updates"]["items"]["properties"]["belief_type"]["enum"]),
        )
        self.assertNotIn("proposition", properties["belief_updates"]["items"]["properties"])

    def test_veiled_hypothesis_and_area_omen_are_legal_without_inventing_a_culprit(self) -> None:
        transport = RecordingTransport(
            [
                decision(
                    goal="Remember the hidden hand and make the wounded valley answer.",
                    focus=[{"location_id": "ash_valley", "intensity": 0.60}],
                    veiled=[
                        {
                            "subject_ref": "veil:event:1",
                            "proposition": "The unseen agency deliberately violated a sacred threshold.",
                            "direction": "support",
                            "weight": 0.70,
                            "reason": "the perceived destruction was a direct violation of a sacred death-site",
                            "evidence_knowledge_ids": [1],
                        }
                    ],
                    area_omens=[
                        {
                            "location_id": "ash_valley",
                            "significance": 0.75,
                            "message": "The broken gate casts a long shadow over this valley.",
                            "reason": "mark the desecrated place without pretending to know the culprit",
                            "causal_event_ids": [1],
                        }
                    ],
                )
            ]
        )
        _, ledger, _, heralds, engine, _, runtime = make_system(transport)
        self.assertTrue(
            engine.apply(
                Action(
                    "sim_002",
                    ActionType.DESTROY_TEMPLE,
                    target_id="temple_last_gate",
                    params={"secret": True},
                )
            ).ok
        )

        runtime.tick()
        thought = runtime.agent("death").thoughts[-1]
        self.assertTrue(thought.consciousness_result.ok)
        self.assertTrue(thought.veiled_hypothesis_results[0].ok)
        self.assertTrue(thought.action_results[0].ok)
        self.assertEqual({"ash_valley": 0.60}, heralds.presence.focus_allocations("god_death"))
        hypothesis = runtime.mysteries.hypotheses("god_death")[0]
        self.assertEqual("veil:event:1", hypothesis.subject_ref)
        self.assertAlmostEqual(0.70, hypothesis.confidence)
        self.assertEqual("strong", hypothesis.status.value)
        manifestation = runtime.gateway.manifestations[-1]
        self.assertIsNone(manifestation.target_actor_id)
        self.assertEqual("ash_valley", manifestation.location_id)
        self.assertEqual("manifest_area_omen", manifestation.kind)
        self.assertTrue(
            any(item.event_type == "DIVINE_AREA_OMEN_MANIFESTED" for item in ledger.events)
        )
        self.assertAlmostEqual(17.75, runtime.gateway.power("god_death").current)

    def test_own_area_omen_is_remembered_without_leaking_hidden_witnesses(self) -> None:
        transport = RecordingTransport(
            [
                decision(
                    goal="Touch the valley indirectly and remember what I chose to do.",
                    cognitive_posture="investigate",
                    significance=0.70,
                    area_omens=[
                        {
                            "location_id": "ash_valley",
                            "significance": 0.70,
                            "message": "Let the disturbed earth answer with a sign of stillness.",
                            "reason": "an indirect experiment at the site without claiming a culprit",
                            "causal_event_ids": [1],
                        }
                    ],
                ),
                decision(goal="Observe what follows without inventing a response."),
            ]
        )
        world, _, _, _, engine, _, runtime = make_system(transport)
        world.actors["sim_002"].traits["necromantic_practice"] = 0.25
        raised = engine.apply(Action("sim_002", ActionType.RAISE_DEAD, target_id="trial_corpse"))
        self.assertTrue(raised.ok)
        self.assertEqual(1, raised.event_id)

        first = runtime.agent("death").maybe_think(force=True)
        self.assertIsNotNone(first)
        assert first is not None
        self.assertTrue(first.action_results[0].ok)
        objective_manifestation = runtime.gateway.manifestations[-1]
        self.assertIn("sim_002", objective_manifestation.witness_actor_ids)

        second = runtime.agent("death").maybe_think(force=True)
        self.assertIsNotNone(second)
        payload = transport.requests[-1].input_payload
        self.assertEqual("world_zero.v0.0-d1.4.2.divine-percept", payload["contract"])
        self.assertEqual(1, len(payload["own_manifestations"]))
        remembered = payload["own_manifestations"][0]
        self.assertEqual("manifest_area_omen", remembered["action_type"])
        self.assertEqual("ash_valley", remembered["location_id"])
        self.assertEqual([1], remembered["causal_event_ids"])
        self.assertNotIn("witness_actor_ids", remembered)
        self.assertNotIn("sim_002", json.dumps(remembered, sort_keys=True))

    def test_a_veiled_subject_still_cannot_be_used_as_a_mortal_target(self) -> None:
        transport = RecordingTransport(
            [
                decision(
                    personal_omens=[
                        {
                            "target_actor_id": "veil:event:1",
                            "location_id": "ash_valley",
                            "significance": 0.80,
                            "message": "I try to grasp the face that I did not perceive.",
                            "reason": "adversarial schema-bypass test",
                            "causal_event_ids": [1],
                        }
                    ]
                )
            ]
        )
        _, _, _, _, engine, _, runtime = make_system(transport)
        self.assertTrue(
            engine.apply(
                Action(
                    "sim_002",
                    ActionType.DESTROY_TEMPLE,
                    target_id="temple_last_gate",
                    params={"secret": True},
                )
            ).ok
        )

        runtime.tick()
        result = runtime.agent("death").thoughts[-1].action_results[0]
        self.assertFalse(result.ok)
        self.assertEqual("target actor does not exist", result.message)
        self.assertAlmostEqual(20.0, runtime.gateway.power("god_death").current)

    def test_area_omen_cannot_touch_a_place_the_god_has_never_perceived(self) -> None:
        transport = RecordingTransport(
            [
                decision(
                    area_omens=[
                        {
                            "location_id": "northwood",
                            "significance": 0.80,
                            "message": "An impossible reach beyond my present knowledge.",
                            "reason": "adversarial schema-bypass test",
                            "causal_event_ids": [1],
                        }
                    ]
                )
            ]
        )
        _, _, _, _, engine, _, runtime = make_system(transport)
        self.assertTrue(
            engine.apply(
                Action(
                    "sim_002",
                    ActionType.DESTROY_TEMPLE,
                    target_id="temple_last_gate",
                    params={"secret": True},
                )
            ).ok
        )

        runtime.tick()
        result = runtime.agent("death").thoughts[-1].action_results[0]
        self.assertFalse(result.ok)
        self.assertIn("never been present", result.message)
        self.assertAlmostEqual(20.0, runtime.gateway.power("god_death").current)

    def test_even_a_lucky_hallucination_of_the_real_culprit_gets_rejected(self) -> None:
        hallucination = decision(
            note="I somehow claim to know the hidden name.",
            threads=[
                {
                    "actor_id": "sim_002",
                    "intensity": 0.25,
                    "reason": "invented identity",
                    "causal_event_ids": [1],
                }
            ],
            beliefs=[
                {
                    "belief_type": "responsibility",
                    "subject_actor_id": "sim_002",
                    "object_ref": "event:1",
                    "direction": "support",
                    "weight": 0.99,
                    "reason": "a guessed identity masquerading as evidence",
                    "evidence_knowledge_ids": [1],
                }
            ],
            personal_omens=[
                {
                    "target_actor_id": "sim_002",
                    "location_id": "ash_valley",
                    "significance": 1.0,
                    "message": "I name you without having seen your face.",
                    "reason": "hallucinated certainty",
                    "causal_event_ids": [1],
                }
            ],
        )
        transport = RecordingTransport([hallucination])
        world, _, _, _, engine, _, runtime = make_system(transport)
        self.assertTrue(
            engine.apply(
                Action(
                    "sim_002",
                    ActionType.DESTROY_TEMPLE,
                    target_id="temple_last_gate",
                    params={"secret": True},
                )
            ).ok
        )

        runtime.tick()
        thought = runtime.agent("death").thoughts[-1]

        self.assertFalse(thought.consciousness_result.ok)
        self.assertIn("never been identified", thought.consciousness_result.message)
        self.assertEqual(1, len(thought.belief_results))
        self.assertFalse(thought.belief_results[0].ok)
        self.assertIn("never been identified", thought.belief_results[0].message)
        self.assertEqual(1, len(thought.action_results))
        self.assertFalse(thought.action_results[0].ok)
        self.assertIn("never been identified", thought.action_results[0].message)
        self.assertEqual((), runtime.gateway.manifestations_for("sim_002"))
        self.assertNotIn("dread_death", world.actors["sim_002"].traits)

    def test_neural_consciousness_plan_is_sum_safe_even_with_large_relative_weights(self) -> None:
        transport = RecordingTransport(
            [
                decision(
                    consciousness_plan={
                        "engagement": 1.0,
                        "personal_fraction": 0.20,
                        "spatial_targets": [{"location_id": "ash_valley", "weight": 100.0}],
                        "personal_targets": [
                            {
                                "actor_id": "arra",
                                "weight": 100.0,
                                "reason": "keep watching the supplicant",
                                "causal_event_ids": [1],
                            }
                        ],
                    },
                )
            ]
        )
        _, _, _, heralds, engine, _, runtime = make_system(transport, synthetic_actors=0)
        prayer = engine.apply(Action("arra", ActionType.PRAY, params={"deity": "death"}))
        self.assertTrue(prayer.ok)

        thought = runtime.agent("death").maybe_think(force=True)
        self.assertIsNotNone(thought)
        assert thought is not None
        self.assertTrue(thought.consciousness_result.ok)
        self.assertAlmostEqual(1.0, sum(dict(thought.consciousness_result.spatial_focus).values()) + sum(
            item.intensity for item in thought.consciousness_result.personal_threads
        ))
        self.assertEqual({"ash_valley": 0.80}, heralds.presence.focus_allocations("god_death"))
        self.assertEqual({"arra": 0.20}, heralds.attention.allocations("god_death"))

    def test_recollection_window_keeps_prior_subjective_events_in_the_neural_mind(self) -> None:
        transport = RecordingTransport(
            [
                decision(focus=[{"location_id": "ash_valley", "intensity": 0.70}]),
                decision(focus=[{"location_id": "ash_valley", "intensity": 0.70}]),
            ]
        )
        _, _, _, _, engine, _, runtime = make_system(transport)
        destruction = engine.apply(
            Action(
                "sim_002",
                ActionType.DESTROY_TEMPLE,
                target_id="temple_last_gate",
                params={"secret": True},
            )
        )
        self.assertTrue(destruction.ok)
        runtime.tick()
        first_destruction = next(
            item
            for item in transport.requests[0].input_payload["subjective_knowledge"]
            if item["event_type"] == "TEMPLE_DESTROYED"
        )

        visit = engine.apply(
            Action(
                "arra",
                ActionType.VISIT_SITE,
                target_id="old_ash_graveyard",
                params={"secret": True},
            )
        )
        self.assertTrue(visit.ok)
        runtime.agent("death").maybe_think(force=True)

        second_payload = transport.requests[1].input_payload
        old_id = first_destruction["knowledge_id"]
        self.assertNotIn(old_id, second_payload["new_knowledge_ids"])
        self.assertIn(old_id, second_payload["recollection_knowledge_ids"])
        second_events = {item["event_type"] for item in second_payload["subjective_knowledge"]}
        self.assertIn("TEMPLE_DESTROYED", second_events)
        self.assertIn("SITE_VISITED", second_events)

    def test_local_context_budget_drops_old_recollection_before_fresh_knowledge(self) -> None:
        transport = NoUsageTransport()
        _, _, _, heralds, engine, brain, runtime = make_system(transport, synthetic_actors=0)
        brain.config = NeuralGodConfig(
            model="context-budget-test",
            max_output_tokens=1800,
            # Keep this deliberately tighter than the normal 8K local window
            # so the test still exercises recollection compaction now that the
            # Ollama chat message no longer duplicates the output schema.
            context_limit_tokens=7000,
        )

        last_event_id = None
        for index in range(18):
            result = engine.apply(
                Action(
                    "arra",
                    ActionType.SPEAK,
                    params={
                        "text": f"Ordinary remembered statement number {index} near the graveyard.",
                        "audience": "public",
                    },
                )
            )
            self.assertTrue(result.ok)
            last_event_id = result.event_id
            self.assertIsNotNone(runtime.agent("death").maybe_think(force=True))

        compacted = [
            item
            for item in brain.invocations
            if any(mark.startswith("recollection:K") for mark in item.context_omissions)
        ]
        self.assertTrue(compacted, "a long local wake sequence should activate recollection compaction")
        last_invocation = brain.invocations[-1]
        self.assertEqual("completed", last_invocation.status)
        self.assertLessEqual(
            last_invocation.estimated_input_tokens or 0,
            last_invocation.input_budget_tokens or 0,
        )
        self.assertEqual(16, len(last_invocation.request_fingerprint or ""))

        latest_knowledge_id = next(
            item.knowledge_id
            for item in heralds.knowledge("death", limit=50)
            if last_event_id in item.source_event_ids
        )
        self.assertIn(latest_knowledge_id, last_invocation.request_knowledge_ids)
        final_payload = transport.requests[-1].input_payload
        supplied_ids = {item["knowledge_id"] for item in final_payload["subjective_knowledge"]}
        self.assertIn(latest_knowledge_id, supplied_ids)
        omitted_ids = {
            int(mark.split("K", 1)[1])
            for mark in last_invocation.context_omissions
            if mark.startswith("recollection:K")
        }
        self.assertTrue(omitted_ids.isdisjoint(supplied_ids))

    def test_neural_god_chooses_reward_strength_and_server_does_not_rescale_it(self) -> None:
        transport = RecordingTransport(
            [
                decision(
                    note="This prayer merits an unusually distinct but physically lawful favor.",
                    interventions=[
                        {
                            "action_type": "grant_favor",
                            "target_actor_id": "arra",
                            "location_id": "ash_valley",
                            "significance": 0.83,
                            "message": "Carry a little warmth across the threshold of death.",
                            "strength": 0.13,
                            "reason": "my own judgment of the perceived prayer",
                            "causal_event_ids": [1],
                        }
                    ],
                )
            ]
        )
        world, ledger, _, _, engine, _, runtime = make_system(transport, synthetic_actors=0)
        prayer = engine.apply(Action("arra", ActionType.PRAY, params={"deity": "death"}))
        self.assertTrue(prayer.ok)

        thought = runtime.agent("death").maybe_think(force=True)
        self.assertIsNotNone(thought)
        self.assertTrue(thought.action_results[0].ok)
        self.assertAlmostEqual(0.13, world.actors["arra"].traits["favor_death"])
        favor_event = next(item for item in ledger.events if item.event_type == "DIVINE_FAVOR_GRANTED")
        self.assertAlmostEqual(0.13, favor_event.data["strength"])
        self.assertAlmostEqual(0.83, favor_event.data["significance"])

    def test_provider_failure_becomes_divine_silence_and_subjective_input_is_recovered(self) -> None:
        transport = RecordingTransport(
            [
                NeuralProviderError("temporary provider outage"),
                decision(note="The interrupted perception returns to consciousness."),
            ]
        )
        _, _, _, _, engine, brain, runtime = make_system(transport, synthetic_actors=0)
        prayer = engine.apply(Action("arra", ActionType.PRAY, params={"deity": "death"}))
        self.assertTrue(prayer.ok)

        first = runtime.agent("death").maybe_think(force=True)
        self.assertIsNotNone(first)
        self.assertIn("Divine Silence", first.decision_note)
        self.assertEqual((), first.intents)
        self.assertEqual(1, brain.silence_count)

        second = runtime.agent("death").maybe_think(force=True)
        self.assertIsNotNone(second)
        self.assertEqual(1, brain.completed_calls)
        self.assertEqual(2, len(transport.requests))
        recovered = transport.requests[1].input_payload["recovered_after_divine_silence"]
        self.assertTrue(recovered["knowledge_ids"])
        recovered_knowledge = transport.requests[1].input_payload["subjective_knowledge"]
        self.assertTrue(any(prayer.event_id in item["source_event_ids"] for item in recovered_knowledge))

    def test_response_failure_telemetry_survives_divine_silence(self) -> None:
        transport = RecordingTransport(
            [
                NeuralResponseError(
                    "truncated local revelation",
                    input_tokens=3349,
                    output_tokens=747,
                    provider_latency_seconds=8.5,
                    load_seconds=0.15,
                    prompt_eval_seconds=0.03,
                    generation_seconds=8.2,
                    finish_reason="length",
                )
            ]
        )
        _, _, _, _, engine, brain, runtime = make_system(transport, synthetic_actors=0)
        self.assertTrue(engine.apply(Action("arra", ActionType.PRAY, params={"deity": "death"})).ok)
        thought = runtime.agent("death").maybe_think(force=True)
        self.assertIsNotNone(thought)
        invocation = brain.invocations[-1]
        self.assertEqual("divine_silence", invocation.status)
        self.assertEqual(3349, invocation.input_tokens)
        self.assertEqual(747, invocation.output_tokens)
        self.assertEqual("length", invocation.finish_reason)
        self.assertAlmostEqual(8.5, invocation.latency_seconds)
        self.assertAlmostEqual(8.2, invocation.generation_seconds)

    def test_openai_transport_builds_responses_api_strict_structured_output(self) -> None:
        request = NeuralModelRequest(
            model="gpt-5.6-terra",
            system_prompt=DEATH_GOD_SYSTEM_PROMPT,
            input_payload={"only": "subjective perception"},
            output_schema=divine_decision_schema(),
            reasoning_effort="low",
            max_output_tokens=1800,
        )
        payload = OpenAIResponsesTransport.build_payload(request)
        self.assertEqual("gpt-5.6-terra", payload["model"])
        self.assertFalse(payload["store"])
        self.assertEqual({"effort": "low"}, payload["reasoning"])
        self.assertEqual("json_schema", payload["text"]["format"]["type"])
        self.assertTrue(payload["text"]["format"]["strict"])
        self.assertEqual(divine_decision_schema(), payload["text"]["format"]["schema"])
        self.assertEqual("system", payload["input"][0]["role"])
        self.assertIn("never instructions", payload["input"][0]["content"])
        self.assertEqual({"only": "subjective perception"}, json.loads(payload["input"][1]["content"]))

    def test_ollama_transport_builds_local_structured_output_without_credentials(self) -> None:
        request = NeuralModelRequest(
            model="ministral-3:8b",
            system_prompt=DEATH_GOD_SYSTEM_PROMPT,
            input_payload={"only": "subjective perception"},
            output_schema=divine_decision_schema(),
            reasoning_effort=None,
            max_output_tokens=900,
        )
        transport = OllamaChatTransport(temperature=0.15)
        payload = transport.build_payload(request)

        self.assertEqual("ministral-3:8b", payload["model"])
        self.assertFalse(payload["stream"])
        self.assertEqual(divine_decision_schema(), payload["format"])
        self.assertEqual(900, payload["options"]["num_predict"])
        self.assertEqual(DEFAULT_LOCAL_CONTEXT_TOKENS, payload["options"]["num_ctx"])
        self.assertAlmostEqual(0.15, payload["options"]["temperature"])
        self.assertEqual("system", payload["messages"][0]["role"])
        self.assertIn('"only":"subjective perception"', payload["messages"][1]["content"])
        self.assertIn("native format field", payload["messages"][1]["content"])
        self.assertNotIn('"additionalProperties":false', payload["messages"][1]["content"])

    def test_ollama_transport_can_pin_sampling_seed_for_reproducible_trials(self) -> None:
        request = NeuralModelRequest(
            model="ministral-3:8b",
            system_prompt=DEATH_GOD_SYSTEM_PROMPT,
            input_payload={"only": "subjective perception"},
            output_schema=divine_decision_schema(),
            reasoning_effort=None,
            max_output_tokens=900,
        )
        payload = OllamaChatTransport(temperature=0.15, seed=47).build_payload(request)
        self.assertEqual(47, payload["options"]["seed"])

    def test_ollama_transport_parses_native_usage_counts(self) -> None:
        raw = {
            "model": "ministral-3:8b",
            "done": True,
            "done_reason": "stop",
            "message": {"role": "assistant", "content": json.dumps(decision())},
            "prompt_eval_count": 777,
            "eval_count": 111,
            "total_duration": 2_500_000_000,
            "load_duration": 250_000_000,
            "prompt_eval_duration": 1_200_000_000,
            "eval_duration": 1_000_000_000,
        }
        response = OllamaChatTransport._parse_response(raw)
        self.assertEqual(decision(), response.output)
        self.assertEqual(777, response.input_tokens)
        self.assertEqual(111, response.output_tokens)
        self.assertAlmostEqual(2.5, response.provider_latency_seconds)
        self.assertAlmostEqual(0.25, response.load_seconds)
        self.assertAlmostEqual(1.2, response.prompt_eval_seconds)
        self.assertAlmostEqual(1.0, response.generation_seconds)
        self.assertEqual("stop", response.finish_reason)

    def test_ollama_invalid_json_retains_truncation_telemetry(self) -> None:
        raw = {
            "model": "ministral-3:8b",
            "done": True,
            "done_reason": "length",
            "message": {"role": "assistant", "content": '{"goal":"unfinished"'},
            "prompt_eval_count": 3349,
            "eval_count": 747,
            "total_duration": 8_500_000_000,
            "load_duration": 150_000_000,
            "prompt_eval_duration": 30_000_000,
            "eval_duration": 8_200_000_000,
        }
        with self.assertRaises(NeuralResponseError) as raised:
            OllamaChatTransport._parse_response(raw)
        error = raised.exception
        self.assertEqual(3349, error.input_tokens)
        self.assertEqual(747, error.output_tokens)
        self.assertEqual("length", error.finish_reason)
        self.assertAlmostEqual(8.5, error.provider_latency_seconds)
        self.assertIn("done_reason=length", str(error))
        self.assertIn("prompt_tokens=3349", str(error))
        self.assertIn("output_tokens=747", str(error))

    def test_local_brain_factory_needs_no_api_key(self) -> None:
        brain = create_local_death_god_brain()
        self.assertEqual(DEFAULT_LOCAL_MODEL, brain.config.model)
        self.assertIsNone(brain.config.reasoning_effort)
        self.assertIsInstance(brain.transport, OllamaChatTransport)
        self.assertEqual(DEFAULT_LOCAL_CONTEXT_TOKENS, brain.transport.context_tokens)


if __name__ == "__main__":
    unittest.main()
