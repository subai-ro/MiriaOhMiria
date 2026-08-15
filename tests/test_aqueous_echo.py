from __future__ import annotations

import unittest

from worldzero.affordances import create_silver_thread_affordance_bridge
from worldzero.engine import WorldEngine
from worldzero.ledger import EventLedger
from worldzero.materials import (
    ItemMaterialProfile,
    MaterialConstituent,
    create_default_material_catalog,
)
from worldzero.models import Action, ActionType
from worldzero.processes.aqueous_echo import (
    EchoSenseOutcome,
    EchoSenseRequest,
    create_silver_thread_aqueous_echo,
    create_silver_thread_echo_sense_bridge,
)
from worldzero.processes.hydrology import create_silver_thread_hydrology
from worldzero.processes.runtime import WorldProcessRuntime
from worldzero.projects import seed_silver_thread_projects
from worldzero.seed import create_world


def make_system(*, seed: int = 42, materials=None, open_gate: bool = False):
    world = create_world(seed=seed, synthetic_actors=0)
    ledger = EventLedger()
    engine = WorldEngine(world, ledger, seed=seed + 1, materials=materials)
    hydrology = create_silver_thread_hydrology(world, ledger)
    if open_gate:
        hydrology.apply_sluice_position(0.80)
        hydrology.clear_gate_debris(0.30)
    affordances = create_silver_thread_affordance_bridge(world, ledger, hydrology)
    echo = create_silver_thread_aqueous_echo(world, ledger, hydrology)
    sensing = create_silver_thread_echo_sense_bridge(
        world, ledger, echo, affordances
    )
    runtime = WorldProcessRuntime()
    runtime.register(hydrology)
    runtime.register(echo)
    runtime.attach(world)
    return world, ledger, engine, hydrology, echo, affordances, sensing, runtime


def fish(engine: WorldEngine, lake: str = "lake_mirror", tool: str = "silver_rod") -> int:
    if engine.world.actors["arra"].location_id != "northwood":
        result = engine.apply(Action("arra", ActionType.TRAVEL, target_id="northwood"))
        if not result.ok:
            raise AssertionError(result.message)
    result = engine.apply(
        Action("arra", ActionType.FISH, target_id=lake, params={"tool": tool})
    )
    if not result.ok or result.event_id is None:
        raise AssertionError(result.message)
    return result.event_id


class MaterialContactContractTests(unittest.TestCase):
    def test_fishing_records_general_material_medium_contact(self) -> None:
        _, ledger, engine, *_ = make_system()
        event_id = fish(engine)
        event = ledger.events[event_id - 1]
        self.assertEqual("FISHED", event.event_type)
        self.assertEqual(event_id, ledger.events[-1].event_id)
        contact = event.data["material_contacts"][0]
        self.assertEqual("material_medium_contact.v1", contact["schema"])
        self.assertEqual("water", contact["medium_kind"])
        self.assertEqual("lake_mirror", contact["medium_ref"])
        self.assertEqual(0.925, contact["material_fractions"]["silver"])

    def test_any_inventory_tool_requires_a_material_profile_and_possession(self) -> None:
        world, ledger, engine, *_ = make_system()
        before = len(ledger.events)
        engine.apply(Action("arra", ActionType.TRAVEL, target_id="northwood"))
        before = len(ledger.events)
        unknown = engine.apply(
            Action("arra", ActionType.FISH, target_id="lake_mirror", params={"tool": "mystery_rod"})
        )
        self.assertFalse(unknown.ok)
        self.assertEqual(before, len(ledger.events))
        world.actors["arra"].inventory["iron_rod"] = 0
        missing = engine.apply(
            Action("arra", ActionType.FISH, target_id="lake_mirror", params={"tool": "iron_rod"})
        )
        self.assertFalse(missing.ok)
        self.assertEqual(before, len(ledger.events))

    def test_alternate_silver_item_obeys_same_material_law(self) -> None:
        catalog = create_default_material_catalog()
        catalog.register(
            ItemMaterialProfile(
                "silver_probe",
                (
                    MaterialConstituent("silver", 0.925),
                    MaterialConstituent("hardwood", 0.075),
                ),
                aqueous_contact_factor=0.60,
            )
        )
        world, _, engine, _, echo, *_ = make_system(materials=catalog)
        world.actors["arra"].inventory["silver_probe"] = 1
        fish(engine, tool="silver_probe")
        world.advance(360)
        alternate_impulse = echo.last_trace.node_impulses["lake_mirror"]

        world2, _, engine2, _, echo2, *_ = make_system()
        fish(engine2, tool="silver_rod")
        world2.advance(360)
        self.assertEqual(
            alternate_impulse,
            echo2.last_trace.node_impulses["lake_mirror"],
        )


class AqueousEchoProcessTests(unittest.TestCase):
    def test_runtime_runs_hydrology_before_echo_at_every_boundary(self) -> None:
        world, _, _, _, echo, _, _, runtime = make_system()
        world.advance(30 * 24 * 60)
        self.assertEqual(120, len(echo.traces))
        for index in range(0, len(runtime.runs), 2):
            self.assertEqual("silver_thread_hydrology", runtime.runs[index].process_id)
            self.assertEqual("silver_thread_water_echo", runtime.runs[index + 1].process_id)
            self.assertEqual(runtime.runs[index].game_minute, runtime.runs[index + 1].game_minute)

    def test_echo_tick_rejects_missing_same_boundary_hydrology(self) -> None:
        world = create_world(synthetic_actors=0)
        ledger = EventLedger()
        hydrology = create_silver_thread_hydrology(world, ledger)
        echo = create_silver_thread_aqueous_echo(world, ledger, hydrology)
        with self.assertRaises(RuntimeError):
            echo.tick(360)

    def test_hands_and_iron_contact_create_no_silver_impulse(self) -> None:
        for tool in ("hands", "iron_rod"):
            with self.subTest(tool=tool):
                world, _, engine, _, echo, *_ = make_system()
                if tool == "iron_rod":
                    world.actors["arra"].inventory[tool] = 1
                fish(engine, tool=tool)
                world.advance(360)
                self.assertEqual(0.0, sum(echo.last_trace.node_impulses.values()))
                self.assertEqual((), echo.last_trace.resonant_contact_refs)
                self.assertEqual(1, len(echo.last_trace.material_contact_refs))

    def test_repeated_contact_accumulates_without_a_count_trigger(self) -> None:
        world, _, engine, _, echo, *_ = make_system()
        for _ in range(3):
            fish(engine)
        world.advance(360)
        triple = echo.state.node_amounts["lake_mirror"]

        world2, _, engine2, _, echo2, *_ = make_system()
        fish(engine2)
        world2.advance(360)
        single = echo2.state.node_amounts["lake_mirror"]
        self.assertAlmostEqual(3.0 * single, triple, places=10)
        forbidden = {"NEREID_INTEREST", "CONTACT_CREATED", "QUEST_CREATED"}
        self.assertTrue(forbidden.isdisjoint(event.event_type for event in echo.ledger.events))

    def test_echo_decays_after_contact_stops(self) -> None:
        world, _, engine, _, echo, *_ = make_system()
        fish(engine)
        world.advance(360)
        after_contact = sum(echo.state.node_amounts.values())
        world.advance(12 * 360)
        self.assertLess(sum(echo.state.node_amounts.values()), after_contact)
        self.assertGreater(echo.traces[-1].decay_loss, 0.0)

    def test_equal_contacts_in_mirror_and_whisper_propagate_differently(self) -> None:
        junction_amounts = []
        for lake in ("lake_mirror", "lake_whisper"):
            world, _, engine, _, echo, *_ = make_system(seed=8)
            fish(engine, lake=lake)
            world.advance(360)
            junction_amounts.append(echo.state.node_amounts["northwood_junction"])
        self.assertNotAlmostEqual(junction_amounts[0], junction_amounts[1], places=10)

    def test_open_gate_changes_downstream_transport_under_same_contact_history(self) -> None:
        downstream = []
        for opened in (False, True):
            world, _, engine, _, echo, *_ = make_system(open_gate=opened)
            for _ in range(5):
                fish(engine)
            world.advance(12 * 360)
            downstream.append(echo.state.node_amounts["underpeak_deep_river"])
        self.assertGreater(downstream[1], downstream[0] * 4.0)

    def test_baseline_closed_gate_keeps_deep_echo_below_perceptible_band(self) -> None:
        world, _, engine, _, echo, *_ = make_system()
        for _ in range(5):
            fish(engine)
        world.advance(12 * 360)
        self.assertEqual("silent", echo.state.band_states["underpeak_deep_river"])

    def test_echo_trace_has_continuous_hash_chain_and_zero_balance_residual(self) -> None:
        world, _, engine, _, echo, *_ = make_system()
        fish(engine)
        world.advance(8 * 360)
        self.assertTrue(
            all(
                earlier.output_state_hash == later.input_state_hash
                for earlier, later in zip(echo.traces, echo.traces[1:])
            )
        )
        self.assertTrue(all(trace.balance_residual == 0.0 for trace in echo.traces))

    def test_identical_material_and_water_histories_are_deterministic(self) -> None:
        def run():
            world, ledger, engine, _, echo, *_ = make_system(seed=91)
            fish(engine, "lake_whisper")
            world.advance(720)
            fish(engine, "lake_mirror")
            world.advance(1440)
            return (
                echo.state.state_hash(),
                [item.as_dict() for item in echo.traces],
                [event.as_dict() for event in ledger.events],
            )

        self.assertEqual(run(), run())

    def test_raw_echo_transitions_are_guarded_objective_state_not_percepts(self) -> None:
        world, ledger, engine, _, echo, affordances, *_ = make_system()
        fish(engine)
        world.advance(360)
        transitions = [
            event for event in ledger.events if event.event_type == "AQUEOUS_ECHO_BAND_CROSSED"
        ]
        self.assertGreaterEqual(len(transitions), 1)
        self.assertTrue(
            all(
                any(barrier.kind == "raw_world_process_state" for barrier in event.perceptual_barriers)
                for event in transitions
            )
        )
        self.assertEqual((), affordances.subject_view("nereid_01").percepts)

    def test_echo_does_not_mutate_projects_or_create_story_events(self) -> None:
        projects = seed_silver_thread_projects()
        before = [item.as_dict() for item in projects.projects]
        world, ledger, engine, _, _, *_ = make_system()
        for _ in range(4):
            fish(engine)
        world.advance(30 * 24 * 60)
        self.assertEqual(before, [item.as_dict() for item in projects.projects])
        forbidden_tokens = ("INTEREST", "CONTACT", "REQUEST", "QUEST")
        self.assertFalse(
            any(
                any(token in event.event_type for token in forbidden_tokens)
                for event in ledger.events
            )
        )


class AqueousEchoSensingTests(unittest.TestCase):
    def test_physical_echo_does_not_manufacture_perception(self) -> None:
        world, _, engine, _, _, affordances, *_ = make_system()
        fish(engine)
        world.advance(720)
        self.assertEqual((), affordances.subject_view("nereid_01").percepts)

    def test_local_water_sense_forms_private_qualitative_percept(self) -> None:
        world, ledger, engine, _, echo, affordances, sensing, _ = make_system()
        fish(engine)
        world.advance(360)
        result = sensing.sense(EchoSenseRequest("nereid_01", "northwood_junction"))
        self.assertTrue(result.ok)
        self.assertEqual(EchoSenseOutcome.SENSED, result.outcome)
        self.assertIsNotNone(result.percept)
        percept = result.percept
        self.assertEqual("nereid_01", percept.subject_id)
        self.assertEqual("sense_aqueous_echo", percept.observation_type)
        self.assertEqual(
            {"echo_presence", "movement_cue", "source_identity", "water_borne_pattern"},
            set(percept.cues),
        )
        serialized = str(percept.as_dict())
        self.assertNotIn(str(echo.state.node_amounts["northwood_junction"]), serialized)
        self.assertNotIn("silver_rod", serialized)
        self.assertNotIn("arra", serialized)
        event = ledger.events[result.event_id - 1]
        self.assertTrue(event.data["percept_payload_withheld_from_ledger"])
        self.assertNotIn("echo_presence", event.data)
        self.assertEqual(1, len(affordances.subject_view("nereid_01").percepts))

    def test_remote_and_faculty_invalid_sensing_reject_before_time_or_state(self) -> None:
        world, ledger, _, _, echo, _, sensing, _ = make_system()
        before = (world.game_minute, echo.state.state_hash(), len(ledger.events))
        remote = sensing.sense(EchoSenseRequest("nereid_01", "lake_mirror"))
        self.assertFalse(remote.ok)
        self.assertEqual(before, (world.game_minute, echo.state.state_hash(), len(ledger.events)))
        no_faculty = sensing.sense(
            EchoSenseRequest("trade_house_01", "underpeak_gate_forebay")
        )
        self.assertFalse(no_faculty.ok)
        self.assertEqual(before, (world.game_minute, echo.state.state_hash(), len(ledger.events)))

    def test_echo_percept_remains_private_to_its_owner(self) -> None:
        world, _, engine, _, _, affordances, sensing, _ = make_system()
        fish(engine)
        world.advance(360)
        result = sensing.sense(EchoSenseRequest("nereid_01", "northwood_junction"))
        with self.assertRaises(PermissionError):
            affordances.perceptions.get_for_subject(
                "trade_house_01", result.percept.ref
            )

    def test_forensic_graph_braids_contact_water_echo_and_private_percept(self) -> None:
        world, _, engine, _, _, _, sensing, _ = make_system()
        fish(engine)
        world.advance(360)
        sensing.sense(EchoSenseRequest("nereid_01", "northwood_junction"))
        kinds = {edge["kind"] for edge in sensing.forensic_graph()["edges"]}
        self.assertTrue(
            {
                "event_contact_record",
                "material_contact_input",
                "water_transport_input",
                "local_sensing_state_input",
                "perception_record",
            }.issubset(kinds)
        )


if __name__ == "__main__":
    unittest.main()
