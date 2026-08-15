from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from worldzero.affordance_trials import run_affordance_acceptance
from worldzero.affordances import (
    BANK_TARGET,
    GATE_TARGET,
    LocalSubjectState,
    PhysicalActionRequest,
    PhysicalActionType,
    PhysicalAffordanceBridge,
    create_silver_thread_affordance_bridge,
)
from worldzero.ledger import EventLedger
from worldzero.processes import WorldProcessRuntime, create_silver_thread_hydrology
from worldzero.seed import create_world


class PhysicalAffordanceTests(unittest.TestCase):
    def fixture(self):
        world = create_world(synthetic_actors=0)
        ledger = EventLedger()
        hydrology = create_silver_thread_hydrology(world, ledger)
        runtime = WorldProcessRuntime()
        runtime.register(hydrology)
        runtime.attach(world)
        bridge = create_silver_thread_affordance_bridge(world, ledger, hydrology)
        return world, ledger, hydrology, runtime, bridge

    def test_factory_registers_bodies_without_waking_minds_or_creating_events(self) -> None:
        _, ledger, _, _, bridge = self.fixture()
        self.assertEqual(("nereid_01", "trade_house_01"), tuple(item.subject_id for item in bridge.subjects))
        self.assertEqual((), ledger.events)
        self.assertEqual((), bridge.perceptions.all_percepts)
        self.assertEqual((), bridge.action_traces)

    def test_remote_inspection_is_rejected_atomically(self) -> None:
        world, _, hydrology, _, bridge = self.fixture()
        bridge.register_subject(
            LocalSubjectState(
                "remote",
                "mortal",
                ("lake_mirror",),
                capability_levels={PhysicalActionType.INSPECT_GATE.value: 1.0},
            )
        )
        before = hydrology.state.state_hash()
        result = bridge.perform(
            PhysicalActionRequest("remote", PhysicalActionType.INSPECT_GATE, GATE_TARGET)
        )
        self.assertFalse(result.ok)
        self.assertEqual(0, world.game_minute)
        self.assertEqual(before, hydrology.state.state_hash())
        self.assertFalse(bridge.perceptions.for_subject("remote"))

    def test_gate_inspection_returns_coarse_private_cues_not_exact_state(self) -> None:
        _, ledger, _, _, bridge = self.fixture()
        result = bridge.perform(
            PhysicalActionRequest("nereid_01", PhysicalActionType.INSPECT_GATE, GATE_TARGET)
        )
        self.assertTrue(result.ok)
        self.assertIsNotNone(result.percept)
        payload = json.dumps(result.percept.as_dict(), sort_keys=True).lower()
        for forbidden in (
            "sluice_position",
            "debris_load",
            "structure_integrity",
            "effective_opening",
            "gate_discharge",
            "aquatic_route_viable",
            "state_hash",
        ):
            self.assertNotIn(forbidden, payload)
        event = ledger.events[-1]
        self.assertTrue(event.data["percept_payload_withheld_from_ledger"])
        self.assertNotIn("visible_debris", event.data)

    def test_private_percept_cannot_be_used_by_another_subject(self) -> None:
        world, _, hydrology, _, bridge = self.fixture()
        percept = bridge.perform(
            PhysicalActionRequest("nereid_01", PhysicalActionType.INSPECT_GATE, GATE_TARGET)
        ).percept
        self.assertIsNotNone(percept)
        before_hash = hydrology.state.state_hash()
        before_minute = world.game_minute
        result = bridge.perform(
            PhysicalActionRequest(
                "trade_house_01",
                PhysicalActionType.ADJUST_SLUICE,
                GATE_TARGET,
                params={"delta": 0.2},
                evidence_refs=(percept.ref,),
            )
        )
        self.assertFalse(result.ok)
        self.assertEqual(before_minute, world.game_minute)
        self.assertEqual(before_hash, hydrology.state.state_hash())

    def test_nereid_silt_influence_is_bounded_and_does_not_move_sluice(self) -> None:
        _, _, hydrology, _, bridge = self.fixture()
        percept = bridge.perform(
            PhysicalActionRequest("nereid_01", PhysicalActionType.INSPECT_GATE, GATE_TARGET)
        ).percept
        before = hydrology.state.gate.debris_load
        result = bridge.perform(
            PhysicalActionRequest(
                "nereid_01",
                PhysicalActionType.SHIFT_LOCAL_SILT,
                GATE_TARGET,
                params={"effort": 1.0},
                evidence_refs=(percept.ref,),
            )
        )
        self.assertTrue(result.ok)
        self.assertGreater(before, hydrology.state.gate.debris_load)
        self.assertLessEqual(before - hydrology.state.gate.debris_load, 0.08)
        self.assertEqual(0.0, hydrology.state.gate.sluice_position)
        self.assertFalse(hydrology.state.aquatic_route_viable)

    def test_action_and_physics_do_not_push_perception(self) -> None:
        world, _, _, _, bridge = self.fixture()
        percept = bridge.perform(
            PhysicalActionRequest("nereid_01", PhysicalActionType.INSPECT_GATE, GATE_TARGET)
        ).percept
        bridge.perform(
            PhysicalActionRequest(
                "nereid_01",
                PhysicalActionType.SHIFT_LOCAL_SILT,
                GATE_TARGET,
                evidence_refs=(percept.ref,),
            )
        )
        self.assertEqual(1, len(bridge.perceptions.for_subject("nereid_01")))
        world.advance(360)
        self.assertEqual(1, len(bridge.perceptions.for_subject("nereid_01")))

    def test_resource_failure_does_not_advance_time_or_mutate_bank(self) -> None:
        world, ledger, hydrology, _, bridge = self.fixture()
        bridge.register_subject(
            LocalSubjectState(
                "poor_crew",
                "mortal",
                ("underpeak_upper_reach",),
                faculties=("engineering",),
                capability_levels={
                    PhysicalActionType.INSPECT_BANK.value: 1.0,
                    PhysicalActionType.REINFORCE_BANK.value: 1.0,
                },
                resources={"effort": 2.0, "materials": 0.0},
            )
        )
        percept = bridge.perform(
            PhysicalActionRequest("poor_crew", PhysicalActionType.INSPECT_BANK, BANK_TARGET)
        ).percept
        before_hash = hydrology.state.state_hash()
        before_minute = world.game_minute
        before_events = len(ledger.events)
        result = bridge.perform(
            PhysicalActionRequest(
                "poor_crew",
                PhysicalActionType.REINFORCE_BANK,
                BANK_TARGET,
                evidence_refs=(percept.ref,),
            )
        )
        self.assertFalse(result.ok)
        self.assertEqual(before_hash, hydrology.state.state_hash())
        self.assertEqual(before_minute, world.game_minute)
        self.assertEqual(before_events, len(ledger.events))

    def test_sluice_adjustment_can_be_partial_and_has_observation_parent(self) -> None:
        _, ledger, hydrology, _, bridge = self.fixture()
        percept = bridge.perform(
            PhysicalActionRequest("trade_house_01", PhysicalActionType.INSPECT_GATE, GATE_TARGET)
        ).percept
        inspection_event_id = ledger.events[-1].event_id
        result = bridge.perform(
            PhysicalActionRequest(
                "trade_house_01",
                PhysicalActionType.ADJUST_SLUICE,
                GATE_TARGET,
                params={"delta": 0.9, "effort": 1.0},
                evidence_refs=(percept.ref,),
            )
        )
        self.assertTrue(result.ok)
        self.assertEqual("partial", result.outcome.value)
        self.assertGreater(hydrology.state.gate.sluice_position, 0.0)
        action_event = next(event for event in ledger.events if event.event_id == result.event_id)
        self.assertEqual((inspection_event_id,), action_event.causal_parent_ids)

    def test_physical_action_enters_next_hydrology_trace(self) -> None:
        world, _, hydrology, _, bridge = self.fixture()
        percept = bridge.perform(
            PhysicalActionRequest("nereid_01", PhysicalActionType.INSPECT_GATE, GATE_TARGET)
        ).percept
        result = bridge.perform(
            PhysicalActionRequest(
                "nereid_01",
                PhysicalActionType.SHIFT_LOCAL_SILT,
                GATE_TARGET,
                evidence_refs=(percept.ref,),
            )
        )
        world.advance(360)
        self.assertIn(result.event_id, hydrology.last_trace.causal_action_event_ids)

    def test_force_then_repair_changes_integrity_through_authoritative_methods(self) -> None:
        _, _, hydrology, _, bridge = self.fixture()
        percept = bridge.perform(
            PhysicalActionRequest("trade_house_01", PhysicalActionType.INSPECT_GATE, GATE_TARGET)
        ).percept
        forced = bridge.perform(
            PhysicalActionRequest(
                "trade_house_01",
                PhysicalActionType.FORCE_SLUICE,
                GATE_TARGET,
                params={"delta": 0.5},
                evidence_refs=(percept.ref,),
            )
        )
        damaged = hydrology.state.gate.structure_integrity
        repaired = bridge.perform(
            PhysicalActionRequest(
                "trade_house_01",
                PhysicalActionType.REPAIR_GATE,
                GATE_TARGET,
                evidence_refs=(percept.ref,),
            )
        )
        self.assertTrue(forced.ok)
        self.assertTrue(repaired.ok)
        self.assertGreater(hydrology.state.gate.structure_integrity, damaged)

    def test_subject_view_contains_only_private_percepts(self) -> None:
        _, _, _, _, bridge = self.fixture()
        bridge.perform(
            PhysicalActionRequest("nereid_01", PhysicalActionType.INSPECT_GATE, GATE_TARGET)
        )
        bridge.perform(
            PhysicalActionRequest("trade_house_01", PhysicalActionType.INSPECT_GATE, GATE_TARGET)
        )
        nereid_view = bridge.subject_view("nereid_01")
        self.assertEqual(1, len(nereid_view.percepts))
        self.assertTrue(all(item.subject_id == "nereid_01" for item in nereid_view.percepts))
        self.assertNotIn("hydrology", json.dumps(nereid_view.as_dict()).lower())

    def test_creator_trace_and_subjective_percepts_export_separately(self) -> None:
        _, _, _, _, bridge = self.fixture()
        bridge.perform(
            PhysicalActionRequest("nereid_01", PhysicalActionType.INSPECT_GATE, GATE_TARGET)
        )
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            percepts = root / "percepts.jsonl"
            provenance = root / "provenance.jsonl"
            actions = root / "actions.jsonl"
            graph_path = root / "graph.json"
            bridge.perceptions.export_percepts_jsonl(percepts)
            bridge.perceptions.export_provenance_jsonl(provenance)
            bridge.export_action_trace_jsonl(actions)
            bridge.export_forensic_graph_json(graph_path)
            self.assertNotIn("source_state_hash", percepts.read_text(encoding="utf-8"))
            self.assertIn("source_state_hash", provenance.read_text(encoding="utf-8"))
            self.assertIn("input_state_hash", actions.read_text(encoding="utf-8"))
            graph = json.loads(graph_path.read_text(encoding="utf-8"))
            self.assertIn("perception_record", {edge["kind"] for edge in graph["edges"]})
            self.assertIn("action_resolution", {edge["kind"] for edge in graph["edges"]})

    def test_full_p4_acceptance(self) -> None:
        result = run_affordance_acceptance(elapsed_days=30)
        self.assertTrue(result.passed, [check for check in result.checks if not check.ok])
        self.assertEqual(26, len(result.checks))


if __name__ == "__main__":
    unittest.main()
