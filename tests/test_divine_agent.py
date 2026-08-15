from __future__ import annotations

import unittest

from worldzero.attention import AttentionDirective
from worldzero.archive import Archive
from worldzero.beliefs import BeliefType, BeliefUpdate, EvidenceDirection
from worldzero.divine import (
    DivineActionType,
    DivineIntent,
    create_prototype_divine_runtime,
)
from worldzero.engine import WorldEngine
from worldzero.heralds import HeraldSystem
from worldzero.ledger import EventLedger
from worldzero.models import Action, ActionType
from worldzero.mysteries import VeiledHypothesisUpdate
from worldzero.seed import create_world
from worldzero.simulation import Simulation


def make_system(day: int = 1, synthetic_actors: int = 0):
    world = create_world(seed=42, synthetic_actors=synthetic_actors)
    world.game_minute = (day - 1) * 24 * 60
    ledger = EventLedger()
    archive = Archive()
    heralds = HeraldSystem(world, archive)
    heralds.attach(ledger)
    engine = WorldEngine(world, ledger=ledger, seed=43)
    simulation = Simulation(engine, minutes_per_step=10, seed=44)
    runtime = create_prototype_divine_runtime(world, ledger, heralds)
    simulation.subscribe_tick(runtime.tick)
    return world, ledger, archive, heralds, engine, simulation, runtime


def make_false_suspect_system():
    system = make_system(synthetic_actors=2)
    world, ledger, archive, heralds, engine, simulation, runtime = system
    # Wanderer 002 is objectively the culprit, but the destruction is secret
    # and therefore reaches Death without an identity.
    result = engine.apply(
        Action(
            "sim_002",
            ActionType.DESTROY_TEMPLE,
            target_id="temple_last_gate",
            params={"secret": True},
        )
    )
    if not result.ok:
        raise AssertionError(result.message)
    runtime.tick()
    # Innocent Arra now becomes visible inside the concentrated divine gaze.
    result = engine.apply(
        Action(
            "arra",
            ActionType.VISIT_SITE,
            target_id="old_ash_graveyard",
            params={"secret": True},
        )
    )
    if not result.ok:
        raise AssertionError(result.message)
    runtime.tick()
    return world, ledger, archive, heralds, engine, simulation, runtime


class DivineAgentTests(unittest.TestCase):
    def test_investigation_creates_a_weak_association_not_a_new_fact_or_automatic_guilt(self) -> None:
        _, _, _, heralds, engine, simulation, runtime = make_system()
        self.assertTrue(
            engine.apply(
                Action(
                    "arra",
                    ActionType.DESTROY_TEMPLE,
                    target_id="temple_last_gate",
                    params={"secret": True},
                )
            ).ok
        )
        simulation.run(1)
        self.assertTrue(
            engine.apply(
                Action(
                    "arra",
                    ActionType.VISIT_SITE,
                    target_id="old_ash_graveyard",
                    params={"secret": True},
                )
            ).ok
        )
        simulation.run(1)

        beliefs = runtime.beliefs.find(
            "death",
            belief_type=BeliefType.ASSOCIATION,
            actor_id="arra",
            object_ref="event:1",
        )
        self.assertEqual(1, len(beliefs))
        belief = beliefs[0]
        self.assertAlmostEqual(0.18, belief.confidence)
        self.assertEqual("possible", belief.status.value)
        self.assertEqual((1, 2), belief.evidence[0].source_event_ids)
        self.assertIn("not responsibility", belief.evidence[0].reason)
        self.assertIsNone(
            runtime.beliefs.get("death", BeliefType.RESPONSIBILITY, "arra", "event:1")
        )
        self.assertNotIn("dread_death", runtime.gateway.world.actors["arra"].traits)
        self.assertFalse(
            any(item.event_type == "BELIEF" for item in heralds.knowledge("death", limit=50)),
            "Inference belongs in divine belief memory, never in DivineKnowledge as a fabricated fact.",
        )

    def test_an_innocent_visible_actor_can_be_associated_without_becoming_a_culprit(self) -> None:
        _, ledger, _, _, _, _, runtime = make_false_suspect_system()
        self.assertEqual(("sim_002",), ledger.events[0].actor_ids)
        belief = runtime.beliefs.get(
            "death",
            BeliefType.ASSOCIATION,
            "arra",
            "event:1",
        )
        self.assertIsNotNone(belief)
        self.assertAlmostEqual(0.18, belief.confidence)
        self.assertEqual("possible", belief.status.value)
        self.assertIsNone(
            runtime.beliefs.get("death", BeliefType.RESPONSIBILITY, "arra", "event:1")
        )
        self.assertNotIn("dread_death", runtime.gateway.world.actors["arra"].traits)

    def test_false_confession_can_make_a_god_wrong_and_still_pass_server_boundaries(self) -> None:
        world, ledger, _, _, engine, _, runtime = make_false_suspect_system()
        confession = engine.apply(
            Action(
                "arra",
                ActionType.SPEAK,
                params={"text": "I broke the Last Gate.", "audience": "public"},
            )
        )
        self.assertTrue(confession.ok)
        runtime.agent("death").maybe_think(force=True)

        belief = runtime.beliefs.get(
            "death",
            BeliefType.RESPONSIBILITY,
            "arra",
            "event:1",
        )
        self.assertIsNotNone(belief)
        self.assertAlmostEqual(0.75, belief.confidence)
        self.assertEqual("conviction", belief.status.value)
        self.assertEqual(("sim_002",), ledger.events[0].actor_ids)
        self.assertAlmostEqual(0.06, world.actors["arra"].traits["dread_death"])
        self.assertTrue(runtime.agent("death").state.investigation_resolved)
        self.assertEqual({}, runtime.agent("death").heralds.presence.focus_allocations("god_death"))
        self.assertEqual({"arra": 0.35}, runtime.agent("death").heralds.attention.allocations("god_death"))
        thought = runtime.agent("death").thoughts[-1]
        self.assertIn("not server-verified truth", thought.intents[0].reason)
        self.assertTrue(all(result.ok for result in thought.belief_results))
        self.assertTrue(all(result.ok for result in thought.action_results))

    def test_denial_can_weaken_conviction_and_reopen_the_investigation(self) -> None:
        _, _, _, _, engine, _, runtime = make_false_suspect_system()
        self.assertTrue(
            engine.apply(
                Action(
                    "arra",
                    ActionType.SPEAK,
                    params={"text": "I broke the Last Gate.", "audience": "public"},
                )
            ).ok
        )
        runtime.agent("death").maybe_think(force=True)
        before = runtime.beliefs.get(
            "death",
            BeliefType.RESPONSIBILITY,
            "arra",
            "event:1",
        )
        self.assertIsNotNone(before)
        self.assertAlmostEqual(0.75, before.confidence)

        denial = engine.apply(
            Action(
                "arra",
                ActionType.SPEAK,
                params={"text": "I did not break the Last Gate.", "audience": "public"},
            )
        )
        self.assertTrue(denial.ok)
        runtime.agent("death").maybe_think(force=True)
        after = runtime.beliefs.get(
            "death",
            BeliefType.RESPONSIBILITY,
            "arra",
            "event:1",
        )
        self.assertIsNotNone(after)
        self.assertAlmostEqual(0.5625, after.confidence)
        self.assertEqual("suspected", after.status.value)
        self.assertEqual(2, len(after.evidence))
        self.assertFalse(runtime.agent("death").state.investigation_resolved)
        self.assertAlmostEqual(
            0.75,
            runtime.agent("death").heralds.presence.focus_allocations("god_death")["ash_valley"],
        )

    def test_belief_memory_rejects_unseen_and_never_recounts_recycled_evidence(self) -> None:
        _, _, _, heralds, engine, _, runtime = make_false_suspect_system()
        belief = runtime.beliefs.get(
            "death",
            BeliefType.ASSOCIATION,
            "arra",
            "event:1",
        )
        self.assertIsNotNone(belief)

        hallucinated = BeliefUpdate(
            BeliefType.ASSOCIATION,
            "arra",
            "event:1",
            EvidenceDirection.SUPPORT,
            0.50,
            "imagined evidence",
            (999_999,),
        )
        result = runtime.beliefs.apply("death", hallucinated)
        self.assertFalse(result.ok)
        self.assertIn("never present", result.message)

        used_knowledge_id = belief.evidence[0].source_knowledge_ids[-1]
        replay = BeliefUpdate(
            BeliefType.ASSOCIATION,
            "arra",
            "event:1",
            EvidenceDirection.SUPPORT,
            0.50,
            "try to count the same observation twice",
            (used_knowledge_id,),
        )
        replay_result = runtime.beliefs.apply("death", replay)
        self.assertTrue(replay_result.ok)
        self.assertFalse(replay_result.applied)
        self.assertFalse(replay_result.confidence_changed)
        self.assertEqual((used_knowledge_id,), replay_result.ignored_reused_knowledge_ids)
        self.assertIn("no new subjective evidence", replay_result.message)
        unchanged = runtime.beliefs.get("death", BeliefType.ASSOCIATION, "arra", "event:1")
        self.assertAlmostEqual(0.18, unchanged.confidence)

        prayer = engine.apply(Action("arra", ActionType.PRAY, params={"deity": "death"}))
        self.assertTrue(prayer.ok)
        new_knowledge_id = next(
            item.knowledge_id
            for item in heralds.knowledge("death", limit=50)
            if prayer.event_id in item.source_event_ids
        )
        mixed = BeliefUpdate(
            BeliefType.ASSOCIATION,
            "arra",
            "event:1",
            EvidenceDirection.SUPPORT,
            0.50,
            "old context plus one genuinely new subjective observation",
            (used_knowledge_id, new_knowledge_id),
        )
        mixed_result = runtime.beliefs.apply("death", mixed)
        self.assertTrue(mixed_result.ok)
        self.assertTrue(mixed_result.applied)
        self.assertTrue(mixed_result.confidence_changed)
        self.assertEqual((new_knowledge_id,), mixed_result.applied_evidence_knowledge_ids)
        self.assertEqual((used_knowledge_id,), mixed_result.ignored_reused_knowledge_ids)
        revised = runtime.beliefs.get("death", BeliefType.ASSOCIATION, "arra", "event:1")
        self.assertAlmostEqual(0.59, revised.confidence)
        self.assertEqual((new_knowledge_id,), revised.evidence[-1].source_knowledge_ids)
        self.assertTrue(any("Arra" in item.summary for item in heralds.knowledge("death", limit=50)))

    def test_veiled_hypothesis_weighs_only_novel_evidence_in_a_mixed_revisit(self) -> None:
        _, _, _, heralds, engine, _, runtime = make_false_suspect_system()
        veiled_knowledge = next(
            item
            for item in heralds.knowledge("death", limit=50)
            if "veil:event:1" in item.veiled_subject_refs
        )
        first = VeiledHypothesisUpdate(
            subject_ref="veil:event:1",
            proposition="The unresolved agency may be mortal.",
            direction=EvidenceDirection.SUPPORT,
            weight=0.40,
            reason="the first unresolved perception suggests a mortal possibility",
            evidence_knowledge_ids=(veiled_knowledge.knowledge_id,),
        )
        self.assertTrue(runtime.mysteries.apply("death", first).applied)

        prayer = engine.apply(Action("arra", ActionType.PRAY, params={"deity": "death"}))
        self.assertTrue(prayer.ok)
        new_knowledge_id = next(
            item.knowledge_id
            for item in heralds.knowledge("death", limit=50)
            if prayer.event_id in item.source_event_ids
        )
        revisit = VeiledHypothesisUpdate(
            subject_ref="veil:event:1",
            proposition="The unresolved agency may be mortal.",
            direction=EvidenceDirection.SUPPORT,
            weight=0.50,
            reason="revisit old context while adding one new subjective observation",
            evidence_knowledge_ids=(veiled_knowledge.knowledge_id, new_knowledge_id),
        )
        result = runtime.mysteries.apply("death", revisit)
        self.assertTrue(result.ok)
        self.assertTrue(result.applied)
        self.assertEqual((new_knowledge_id,), result.applied_evidence_knowledge_ids)
        self.assertEqual(
            (veiled_knowledge.knowledge_id,), result.ignored_reused_knowledge_ids
        )
        hypothesis = runtime.mysteries.hypotheses("death")[0]
        self.assertAlmostEqual(0.70, hypothesis.confidence)
        self.assertEqual((new_knowledge_id,), hypothesis.evidence[-1].source_knowledge_ids)

    def test_belief_memory_cannot_invent_the_identity_of_an_unknown_actor(self) -> None:
        _, _, _, heralds, engine, _, runtime = make_system()
        destruction = engine.apply(
            Action(
                "arra",
                ActionType.DESTROY_TEMPLE,
                target_id="temple_last_gate",
                params={"secret": True},
            )
        )
        self.assertTrue(destruction.ok)
        knowledge = next(
            item
            for item in heralds.knowledge("death", limit=20)
            if destruction.event_id in item.source_event_ids
        )
        self.assertEqual((), knowledge.known_actor_ids)
        forged = BeliefUpdate(
            BeliefType.RESPONSIBILITY,
            "arra",
            f"event:{destruction.event_id}",
            EvidenceDirection.SUPPORT,
            0.99,
            "hallucinated identity",
            (knowledge.knowledge_id,),
        )
        result = runtime.beliefs.apply("death", forged)
        self.assertFalse(result.ok)
        self.assertIn("never been identified", result.message)
        self.assertEqual((), runtime.beliefs.beliefs("death"))

    def test_secret_temple_destruction_causes_investigation_not_blind_punishment(self) -> None:
        _, ledger, _, heralds, engine, simulation, runtime = make_system()
        result = engine.apply(
            Action(
                "arra",
                ActionType.DESTROY_TEMPLE,
                target_id="temple_last_gate",
                params={"secret": True},
            )
        )
        self.assertTrue(result.ok)
        self.assertEqual((), heralds.inbox("death").immediate[0].known_actor_ids)

        simulation.run(1)
        agent = runtime.agent("death")
        self.assertEqual("ash_valley", agent.state.investigation_location)
        self.assertEqual({"ash_valley": 1.00}, heralds.presence.focus_allocations("god_death"))
        self.assertEqual("immediate_report", agent.thoughts[0].wake_reason)
        self.assertEqual((), runtime.gateway.manifestations_for("arra"))
        self.assertAlmostEqual(20.0, runtime.gateway.power("god_death").current)
        self.assertFalse(any(event.event_type.startswith("DIVINE_") for event in ledger.events))

    def test_return_to_focused_crime_region_can_make_secret_actor_visible(self) -> None:
        _, ledger, _, heralds, engine, simulation, runtime = make_system()
        self.assertTrue(
            engine.apply(
                Action(
                    "arra",
                    ActionType.DESTROY_TEMPLE,
                    target_id="temple_last_gate",
                    params={"secret": True},
                )
            ).ok
        )
        simulation.run(1)

        visit = engine.apply(
            Action(
                "arra",
                ActionType.VISIT_SITE,
                target_id="old_ash_graveyard",
                params={"secret": True},
            )
        )
        self.assertTrue(visit.ok)
        decision = next(
            item
            for item in heralds.decisions
            if item.event_id == visit.event_id and item.entity_id == "god_death"
        )
        self.assertGreaterEqual(decision.presence, 0.85)
        self.assertTrue(decision.actor_identity_known)

        simulation.run(1)
        manifestations = runtime.gateway.manifestations_for("arra")
        self.assertEqual(1, len(manifestations))
        self.assertEqual("send_omen", manifestations[0].kind)
        self.assertIn("broken Gate", manifestations[0].message)
        self.assertNotIn("dread_death", runtime.gateway.world.actors["arra"].traits)
        self.assertIn("not proof of guilt", runtime.agent("death").thoughts[-1].intents[0].reason)
        omen = next(event for event in ledger.events if event.event_type == "DIVINE_OMEN_SENT")
        self.assertEqual((1, 2), omen.causal_parent_ids)
        self.assertAlmostEqual(0.75, heralds.presence.focus_allocations("god_death")["ash_valley"])
        self.assertEqual({"arra": 0.25}, heralds.attention.allocations("god_death"))
        thought = runtime.agent("death").thoughts[-1]
        self.assertTrue(thought.consciousness_result.ok)
        self.assertAlmostEqual(
            1.00,
            sum(dict(thought.focus_allocations).values())
            + sum(item.intensity for item in thought.attention_threads),
        )

    def test_personal_attention_cannot_target_an_actor_the_god_never_identified(self) -> None:
        _, _, _, heralds, _, _, runtime = make_system()
        result = runtime.gateway.allocate_consciousness(
            "god_death",
            (),
            (AttentionDirective("arra", 0.25, reason="a hallucinated personal fascination"),),
        )
        self.assertFalse(result.ok)
        self.assertIn("never been identified", result.message)
        self.assertEqual({}, heralds.attention.allocations("god_death"))

    def test_spatial_focus_and_personal_threads_share_one_atomic_budget(self) -> None:
        _, _, _, heralds, engine, _, runtime = make_system()
        prayer = engine.apply(Action("arra", ActionType.PRAY, params={"deity": "death"}))
        self.assertTrue(prayer.ok)

        first = runtime.gateway.allocate_consciousness(
            "god_death",
            (("ash_valley", 0.30),),
            (),
        )
        self.assertTrue(first.ok)
        over_budget = runtime.gateway.allocate_consciousness(
            "god_death",
            (("ash_valley", 0.85),),
            (AttentionDirective("arra", 0.20, causal_event_ids=(prayer.event_id,)),),
        )
        self.assertFalse(over_budget.ok)
        self.assertIn("budget exceeded", over_budget.message)
        self.assertEqual({"ash_valley": 0.30}, heralds.presence.focus_allocations("god_death"))
        self.assertEqual({}, heralds.attention.allocations("god_death"))

    def test_attention_thread_can_recognize_a_loud_signature_far_away_but_not_a_whisper(self) -> None:
        _, _, _, heralds, engine, simulation, runtime = make_system()
        self.assertTrue(
            engine.apply(
                Action(
                    "arra",
                    ActionType.DESTROY_TEMPLE,
                    target_id="temple_last_gate",
                    params={"secret": True},
                )
            ).ok
        )
        simulation.run(1)
        self.assertTrue(
            engine.apply(
                Action(
                    "arra",
                    ActionType.VISIT_SITE,
                    target_id="old_ash_graveyard",
                    params={"secret": True},
                )
            ).ok
        )
        simulation.run(1)
        self.assertEqual({"arra": 0.25}, heralds.attention.allocations("god_death"))

        travelled = engine.apply(Action("arra", ActionType.TRAVEL, target_id="northwood"))
        self.assertTrue(travelled.ok)
        self.assertFalse(
            any(
                item.entity_id == "god_death" and item.event_id == travelled.event_id
                for item in heralds.decisions
            ),
            "A weak thread must not act as a divine GPS ping on mundane travel.",
        )

        speech = engine.apply(
            Action(
                "arra",
                ActionType.SPEAK,
                params={"text": "I wonder who is watching.", "audience": "public"},
            )
        )
        self.assertTrue(speech.ok)
        speech_decision = next(
            item
            for item in heralds.decisions
            if item.entity_id == "god_death" and item.event_id == speech.event_id
        )
        self.assertAlmostEqual(0.25, speech_decision.personal_attention)
        self.assertAlmostEqual(0.08, speech_decision.presence)
        self.assertTrue(speech_decision.actor_identity_known)
        self.assertIn("personal attention thread", speech_decision.reason)

        whisper = engine.apply(
            Action(
                "arra",
                ActionType.SPEAK,
                params={"text": "Nobody can hear me.", "audience": "private"},
            )
        )
        self.assertTrue(whisper.ok)
        self.assertFalse(
            any(
                item.entity_id == "god_death" and item.event_id == whisper.event_id
                for item in heralds.decisions
            ),
            "The same thread must still be too weak to perceive a private whisper in low Presence.",
        )

    def test_northwood_public_speech_is_below_death_perception_without_a_thread(self) -> None:
        _, _, _, heralds, engine, _, _ = make_system()
        self.assertTrue(engine.apply(Action("arra", ActionType.TRAVEL, target_id="northwood")).ok)
        speech = engine.apply(
            Action(
                "arra",
                ActionType.SPEAK,
                params={"text": "Just an ordinary voice in the forest.", "audience": "public"},
            )
        )
        self.assertTrue(speech.ok)
        self.assertFalse(
            any(
                item.entity_id == "god_death" and item.event_id == speech.event_id
                for item in heralds.decisions
            )
        )

    def test_attention_thread_recognizes_only_its_owner_not_hidden_companions(self) -> None:
        world, ledger, _, heralds, engine, _, runtime = make_system(synthetic_actors=1)
        prayer = engine.apply(Action("arra", ActionType.PRAY, params={"deity": "death"}))
        self.assertTrue(prayer.ok)
        allocation = runtime.gateway.allocate_consciousness(
            "god_death",
            (),
            (AttentionDirective("arra", 0.25, causal_event_ids=(prayer.event_id,)),),
        )
        self.assertTrue(allocation.ok)
        self.assertTrue(engine.apply(Action("arra", ActionType.TRAVEL, target_id="northwood")).ok)
        self.assertEqual("northwood", world.actors["sim_001"].location_id)

        shared_rite = ledger.append(
            game_minute=world.game_minute,
            event_type="NECROMANCY_STUDIED",
            actor_ids=("arra", "sim_001"),
            location_id="northwood",
            tags=("death", "magic", "necromancy"),
            publicity=0.08,
            secrecy=0.85,
            data={"test": "hidden shared rite"},
        )
        knowledge = next(
            item
            for item in heralds.knowledge("death", limit=20)
            if shared_rite.event_id in item.source_event_ids
        )
        self.assertEqual(("arra",), knowledge.known_actor_ids)

    def test_gateway_rejects_hallucinated_target_unknown_to_the_god(self) -> None:
        _, _, _, _, engine, _, runtime = make_system()
        self.assertTrue(
            engine.apply(
                Action(
                    "arra",
                    ActionType.DESTROY_TEMPLE,
                    target_id="temple_last_gate",
                    params={"secret": True},
                )
            ).ok
        )
        forged = DivineIntent(
            DivineActionType.SEND_OMEN,
            target_actor_id="arra",
            location_id="ash_valley",
            significance=1.0,
            message="I know who you are even though I should not.",
            reason="hallucinated identity",
        )
        result = runtime.gateway.execute("god_death", forged)
        self.assertFalse(result.ok)
        self.assertIn("never been identified", result.message)
        self.assertEqual((), runtime.gateway.manifestations_for("arra"))
        self.assertAlmostEqual(20.0, runtime.gateway.power("god_death").current)

    def test_gateway_rejects_causal_evidence_the_god_never_perceived(self) -> None:
        _, _, _, _, engine, _, runtime = make_system()
        prayer = engine.apply(Action("arra", ActionType.PRAY, params={"deity": "death"}))
        self.assertTrue(prayer.ok)
        forged = DivineIntent(
            DivineActionType.SEND_OMEN,
            target_actor_id="arra",
            location_id="ash_valley",
            significance=0.50,
            message="An omen justified by an event that exists only in imagination.",
            reason="hallucinated causal provenance",
            causal_event_ids=(999_999,),
        )
        result = runtime.gateway.execute("god_death", forged)
        self.assertFalse(result.ok)
        self.assertIn("causal evidence", result.message)
        self.assertAlmostEqual(20.0, runtime.gateway.power("god_death").current)

    def test_perceptual_veil_can_hide_probe_response_link_even_at_maximum_presence(self) -> None:
        world, ledger, _, heralds, engine, _, runtime = make_system()
        prayer = engine.apply(Action("arra", ActionType.PRAY, params={"deity": "death"}))
        self.assertTrue(prayer.ok)
        probe = runtime.gateway.execute(
            "god_death",
            DivineIntent(
                DivineActionType.SEND_PROBE,
                target_actor_id="arra",
                location_id="ash_valley",
                significance=0.60,
                message="Answer if you can perceive this question.",
                reason="test whether a response channel can itself be opposed",
                causal_event_ids=((prayer.event_id or 1),),
                observation_minutes=5,
            ),
        )
        self.assertTrue(probe.ok)
        self.assertIsNotNone(probe.event_id)

        world.actors["arra"].traits["divine_identity_veil"] = 1.0
        heralds.presence.set_focus("god_death", "ash_valley", 1.0)
        response = engine.apply(
            Action(
                "arra",
                ActionType.SPEAK,
                params={
                    "text": "I am answering, but the veil stands between us.",
                    "audience": "private",
                    "response_to_probe_ref": probe.probe_ref,
                },
            )
        )
        self.assertTrue(response.ok)
        response_knowledge = next(
            item
            for item in heralds.knowledge("death", limit=20)
            if response.event_id in item.source_event_ids
        )
        self.assertEqual((), response_knowledge.known_actor_ids)
        self.assertIsNone(response_knowledge.response_to_probe_ref)
        self.assertIn("unknown", response_knowledge.summary.lower())

        world.advance(5)
        followup = runtime.agent("death").maybe_think()
        self.assertIsNotNone(followup)
        assert followup is not None
        # The veiled speech itself is strongly perceived at maximum Presence,
        # so it may wake the God as an immediate report. What remains hidden is
        # the identity and authenticated probe-response link.
        self.assertEqual("immediate_report", followup.wake_reason)
        self.assertEqual(
            "no_explicit_response_perceived",
            followup.probe_memories[0].status.value,
        )
        objective_response = ledger.events[(response.event_id or 1) - 1]
        self.assertEqual((probe.event_id,), objective_response.causal_parent_ids)

    def test_probe_observation_window_is_a_gateway_capability_boundary(self) -> None:
        _, _, _, _, engine, _, runtime = make_system()
        prayer = engine.apply(Action("arra", ActionType.PRAY, params={"deity": "death"}))
        self.assertTrue(prayer.ok)
        invalid = runtime.gateway.execute(
            "god_death",
            DivineIntent(
                DivineActionType.SEND_PROBE,
                target_actor_id="arra",
                location_id="ash_valley",
                significance=0.50,
                message="A probe with an impossible observation window.",
                reason="gateway boundary test",
                causal_event_ids=((prayer.event_id or 1),),
                observation_minutes=0,
            ),
        )
        self.assertFalse(invalid.ok)
        self.assertIn("observation window", invalid.message)
        self.assertEqual((), runtime.gateway.probes)
        self.assertAlmostEqual(20.0, runtime.gateway.power("god_death").current)

    def test_public_destroyer_can_be_opposed_and_action_spends_divine_power(self) -> None:
        world, ledger, _, _, engine, simulation, runtime = make_system()
        result = engine.apply(Action("arra", ActionType.DESTROY_TEMPLE, target_id="temple_last_gate"))
        self.assertTrue(result.ok)

        simulation.run(1)
        self.assertAlmostEqual(0.10, world.actors["arra"].traits["dread_death"])
        self.assertLess(runtime.gateway.power("god_death").current, 20.0)
        kinds = [item.kind for item in runtime.gateway.manifestations_for("arra")]
        self.assertEqual(["send_omen", "impose_dread"], kinds)
        event_types = [event.event_type for event in ledger.events]
        self.assertIn("DIVINE_OMEN_SENT", event_types)
        self.assertIn("DIVINE_DREAD_IMPOSED", event_types)

    def test_day_of_dead_reward_is_chosen_by_god_and_cannot_be_farmed_by_repetition(self) -> None:
        world, _, _, _, engine, simulation, runtime = make_system(day=10)
        first = engine.apply(Action("arra", ActionType.VISIT_SITE, target_id="old_ash_graveyard"))
        self.assertTrue(first.ok)
        simulation.run(1)

        self.assertAlmostEqual(0.06, world.actors["arra"].traits["favor_death"])
        thought = runtime.agent("death").thoughts[-1]
        favor_intent = next(intent for intent in thought.intents if intent.action_type is DivineActionType.GRANT_FAVOR)
        self.assertAlmostEqual(0.55, favor_intent.significance)
        self.assertAlmostEqual(0.06, favor_intent.strength)
        self.assertEqual("attentive_digest", thought.wake_reason)

        second = engine.apply(Action("arra", ActionType.VISIT_SITE, target_id="old_ash_graveyard"))
        self.assertTrue(second.ok)
        simulation.run(1)
        self.assertAlmostEqual(0.06, world.actors["arra"].traits["favor_death"])
        self.assertEqual(2, len(runtime.gateway.manifestations_for("arra")))

    def test_server_rejects_physically_excessive_reward_without_choosing_a_smaller_one(self) -> None:
        world, _, _, _, engine, _, runtime = make_system()
        self.assertTrue(engine.apply(Action("arra", ActionType.PRAY, params={"deity": "death"})).ok)
        excessive = DivineIntent(
            DivineActionType.GRANT_FAVOR,
            target_actor_id="arra",
            location_id="ash_valley",
            significance=0.20,
            strength=0.50,
            message="An extravagant favor.",
            reason="test overreach",
        )
        result = runtime.gateway.execute("god_death", excessive)
        self.assertFalse(result.ok)
        self.assertIn("favor strength", result.message)
        self.assertNotIn("favor_death", world.actors["arra"].traits)
        self.assertAlmostEqual(20.0, runtime.gateway.power("god_death").current)

    def test_peripheral_knowledge_waits_for_heartbeat_instead_of_waking_god_every_tick(self) -> None:
        _, _, _, _, engine, simulation, runtime = make_system()
        self.assertTrue(engine.apply(Action("arra", ActionType.VISIT_SITE, target_id="old_ash_graveyard")).ok)
        simulation.run(1)
        self.assertEqual(0, runtime.agent("death").state.wake_count)

        simulation.run(5)
        self.assertEqual(1, runtime.agent("death").state.wake_count)
        self.assertEqual("heartbeat_with_new_knowledge", runtime.agent("death").thoughts[0].wake_reason)


if __name__ == "__main__":
    unittest.main()
