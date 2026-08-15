from __future__ import annotations

import unittest

from worldzero.hydrology_projects import AquaticPassageResolver
from worldzero.hydrology_trials import run_hydrology_acceptance
from worldzero.archive import Archive
from worldzero.heralds import HeraldSystem
from worldzero.ledger import EventLedger
from worldzero.processes import GalleryRouteState, WorldProcessRuntime, create_silver_thread_hydrology
from worldzero.seed import create_world


class WorldProcessRuntimeTests(unittest.TestCase):
    def test_large_world_advance_does_not_skip_six_hour_boundaries(self) -> None:
        world = create_world(synthetic_actors=0)
        ledger = EventLedger()
        hydrology = create_silver_thread_hydrology(world, ledger)
        runtime = WorldProcessRuntime(start_minute=world.game_minute)
        runtime.register(hydrology)
        runtime.attach(world)
        world.advance(30 * 24 * 60)
        self.assertEqual(120, len(hydrology.traces))
        self.assertEqual(360, hydrology.traces[0].game_minute)
        self.assertEqual(30 * 24 * 60, hydrology.traces[-1].game_minute)

    def test_process_failure_is_not_silently_swallowed(self) -> None:
        class BrokenProcess:
            process_id = "broken"
            tick_interval_minutes = 10

            def tick(self, game_minute: int) -> None:
                raise RuntimeError("physics failed")

        world = create_world(synthetic_actors=0)
        runtime = WorldProcessRuntime()
        runtime.register(BrokenProcess())
        runtime.attach(world)
        with self.assertRaisesRegex(RuntimeError, "physics failed"):
            world.advance(10)


class HydrologyTests(unittest.TestCase):
    def fixture(self):
        world = create_world(synthetic_actors=0)
        ledger = EventLedger()
        hydrology = create_silver_thread_hydrology(world, ledger)
        runtime = WorldProcessRuntime()
        runtime.register(hydrology)
        runtime.attach(world)
        return world, ledger, hydrology

    def test_seed_contains_exactly_seven_focal_nodes_and_hidden_burial_exists(self) -> None:
        world, _, hydrology = self.fixture()
        self.assertEqual(7, len(hydrology.state.nodes))
        self.assertIn("underpeak_burial_shelf", world.objects)
        self.assertEqual("buried", world.objects["underpeak_burial_shelf"].condition)

    def test_baseline_30_day_calibration_conserves_mass_and_stays_blocked(self) -> None:
        world, ledger, hydrology = self.fixture()
        world.advance(30 * 24 * 60)
        self.assertLessEqual(
            max(abs(trace.mass_balance_residual) for trace in hydrology.traces),
            1e-10,
        )
        self.assertFalse(hydrology.state.aquatic_route_viable)
        self.assertEqual(0.0, hydrology.state.burial_bank.exposure_fraction)
        self.assertFalse(any(e.event_type == "BURIAL_COVER_BECAME_EXPOSED" for e in ledger.events))

    def test_aquatic_route_requires_two_consecutive_viable_ticks(self) -> None:
        world, _, hydrology = self.fixture()
        hydrology.apply_sluice_position(0.70)
        world.advance(360)
        self.assertFalse(hydrology.state.aquatic_route_viable)
        world.advance(360)
        self.assertTrue(hydrology.state.aquatic_route_viable)

    def test_moderate_opening_and_gallery_work_do_not_imply_nereid_passage(self) -> None:
        world, _, hydrology = self.fixture()
        hydrology.apply_sluice_position(0.40)
        hydrology.clear_gallery_rubble(0.70)
        world.advance(30 * 24 * 60)
        self.assertEqual(GalleryRouteState.PASSABLE, hydrology.state.gallery.route_state)
        self.assertTrue(world.regions["underpeak"].accessible)
        self.assertFalse(hydrology.state.aquatic_route_viable)

    def test_bank_reinforcement_changes_exposure_under_same_gate_regime(self) -> None:
        world_a, ledger_a, a = self.fixture()
        a.apply_sluice_position(0.60)
        world_a.advance(30 * 24 * 60)

        world_b, ledger_b, b = self.fixture()
        b.apply_sluice_position(0.60)
        b.reinforce_bank(0.50)
        world_b.advance(30 * 24 * 60)

        self.assertGreater(a.state.burial_bank.exposure_fraction, 0.0)
        self.assertEqual(0.0, b.state.burial_bank.exposure_fraction)
        self.assertTrue(any(e.event_type == "BURIAL_COVER_BECAME_EXPOSED" for e in ledger_a.events))
        self.assertFalse(any(e.event_type == "BURIAL_COVER_BECAME_EXPOSED" for e in ledger_b.events))

    def test_brief_high_flow_is_not_a_burial_story_trigger(self) -> None:
        world, ledger, hydrology = self.fixture()
        hydrology.apply_sluice_position(0.80)
        world.advance(2 * 360)
        hydrology.apply_sluice_position(0.0)
        world.advance(30 * 24 * 60 - 2 * 360)
        self.assertEqual(0.0, hydrology.state.burial_bank.exposure_fraction)
        self.assertFalse(any(e.event_type == "BURIAL_COVER_BECAME_EXPOSED" for e in ledger.events))

    def test_gate_action_provenance_reaches_threshold_event_and_process_trace(self) -> None:
        world, ledger, hydrology = self.fixture()
        action = ledger.append(
            game_minute=0,
            event_type="LAB_GATE_ADJUSTED",
            actor_ids=("lab_operator",),
            target_ids=("underpeak_river_gate",),
            location_id="underpeak",
            tags=("lab",),
            witness_ids=(),
            publicity=0.0,
            secrecy=1.0,
            data={"sluice_position": 0.70},
        )
        hydrology.apply_sluice_position(0.70, causal_action_event_id=action.event_id)
        world.advance(2 * 360)
        self.assertIn(action.event_id, hydrology.last_trace.causal_action_event_ids)
        route_event = next(e for e in ledger.events if e.event_type == "AQUATIC_ROUTE_BECAME_VIABLE")
        self.assertIn(action.event_id, route_event.causal_parent_ids)

    def test_raw_process_transition_enters_archive_without_becoming_divine_knowledge(self) -> None:
        world = create_world(synthetic_actors=0)
        ledger = EventLedger()
        archive = Archive()
        heralds = HeraldSystem(world, archive)
        heralds.attach(ledger)
        heralds.presence.set_focus("god_death", "underpeak", 1.0)
        heralds.presence.set_focus("god_nature", "underpeak", 1.0)
        hydrology = create_silver_thread_hydrology(world, ledger)
        runtime = WorldProcessRuntime()
        runtime.register(hydrology)
        runtime.attach(world)
        hydrology.apply_sluice_position(0.60)
        world.advance(30 * 24 * 60)
        self.assertTrue(any(e.event_type == "BURIAL_COVER_BECAME_EXPOSED" for e in ledger.events))
        self.assertTrue(any(e.event_type == "BURIAL_COVER_BECAME_EXPOSED" for e in archive.entries))
        for deity in ("god_death", "god_nature", "god_trade"):
            self.assertFalse(
                any(k.event_type == "BURIAL_COVER_BECAME_EXPOSED" for k in heralds.knowledge(deity))
            )

    def test_full_p3_acceptance(self) -> None:
        result = run_hydrology_acceptance(elapsed_days=30)
        self.assertTrue(result.passed, [check for check in result.checks if not check.ok])
        self.assertFalse(result.project_runtime.errors)


class HydrologyProjectAdapterTests(unittest.TestCase):
    def test_adapter_exposes_outcome_not_hidden_hydrology_state(self) -> None:
        world = create_world(synthetic_actors=0)
        ledger = EventLedger()
        hydrology = create_silver_thread_hydrology(world, ledger)
        resolver = AquaticPassageResolver(hydrology)
        self.assertEqual("hydrology.aquatic_passage.v1", resolver.rule_id)


if __name__ == "__main__":
    unittest.main()
