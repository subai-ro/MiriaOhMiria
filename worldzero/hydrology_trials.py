from __future__ import annotations

from dataclasses import dataclass

from .engine import WorldEngine
from .hydrology_projects import AquaticPassageResolver
from .ledger import EventLedger
from .project_runtime import ProjectDecision, ProjectIntent, ProjectMind, ProjectPercept, ProjectRuntime
from .projects import AttemptOutcome, ProjectStatus, seed_silver_thread_projects
from .provenance import CausalTrace
from .seed import create_world
from .simulation import Simulation
from .processes import GalleryRouteState, HydrologyProcess, WorldProcessRuntime, create_silver_thread_hydrology


DAY_MINUTES = 24 * 60
HYDRO_TICKS_PER_DAY = 4


@dataclass(frozen=True)
class HydrologyTrialCheck:
    name: str
    ok: bool
    detail: str


@dataclass(frozen=True)
class HydrologyAcceptanceResult:
    checks: tuple[HydrologyTrialCheck, ...]
    world: object
    ledger: EventLedger
    hydrology: HydrologyProcess
    process_runtime: WorldProcessRuntime
    projects: object
    project_runtime: ProjectRuntime
    project_trace: CausalTrace

    @property
    def passed(self) -> bool:
        return all(check.ok for check in self.checks)


class HydrologyLabNereidMind(ProjectMind):
    """Acceptance double: persistence test only, not canonical Nereid cognition."""

    def decide(self, percept: ProjectPercept) -> ProjectDecision:
        attempts = percept.project.attempt_history
        if not attempts:
            strategy = "test whether the remembered water route now carries through"
            constraints: tuple[str, ...] = ()
        elif len(attempts) == 1:
            strategy = "reconsider the route after direct physical failure"
            constraints = ("remembered_water_route_is_not_currently_continuous",)
        else:
            strategy = "retest only after allowing the shared world time to change"
            constraints = ("remembered_water_route_is_not_currently_continuous",)
        return ProjectDecision(
            strategy=strategy,
            subjective_evidence_refs=percept.available_evidence_refs,
            next_review_minute=percept.game_minute + 7 * DAY_MINUTES,
            intents=(
                ProjectIntent(
                    intent_type="attempt_aquatic_passage",
                    target_refs=("water:underpeak_deep_river",),
                ),
            ),
            known_constraints_add=constraints,
            hypotheses=percept.project.hypotheses,
        )


def _physical_fixture() -> tuple[object, EventLedger, HydrologyProcess, WorldProcessRuntime]:
    world = create_world(seed=42, synthetic_actors=0)
    ledger = EventLedger()
    hydrology = create_silver_thread_hydrology(world, ledger)
    runtime = WorldProcessRuntime(start_minute=world.game_minute)
    runtime.register(hydrology)
    runtime.attach(world)
    return world, ledger, hydrology, runtime


def _advance_days(world, days: int) -> None:
    world.advance(days * DAY_MINUTES)


def run_hydrology_acceptance(*, elapsed_days: int = 30) -> HydrologyAcceptanceResult:
    if elapsed_days < 30:
        raise ValueError("hydrology acceptance requires at least 30 days")

    world = create_world(seed=42, synthetic_actors=0)
    ledger = EventLedger()
    engine = WorldEngine(world, ledger=ledger, seed=43)
    hydrology = create_silver_thread_hydrology(world, ledger)
    process_runtime = WorldProcessRuntime(start_minute=world.game_minute)
    process_runtime.register(hydrology)
    process_runtime.attach(world)

    projects = seed_silver_thread_projects(world.game_minute)
    project_trace = CausalTrace(ledger)
    project_runtime = ProjectRuntime(projects, project_trace)
    project_runtime.register_mind("nereid_01", HydrologyLabNereidMind())
    project_runtime.register_resolver(
        "attempt_aquatic_passage", AquaticPassageResolver(hydrology)
    )
    simulation = Simulation(engine, minutes_per_step=360, seed=44)
    simulation.subscribe_tick(lambda: project_runtime.tick(world.game_minute))
    simulation.run(elapsed_days * HYDRO_TICKS_PER_DAY)

    nereid = projects.get("nereid_return_underpeak")
    player_events = [event for event in ledger.events if "arra" in event.actor_ids]
    hydrology_events = [event for event in ledger.events if "world_process" in event.tags]
    passage_events = [event for event in ledger.events if event.event_type == "AQUATIC_PASSAGE_ATTEMPTED"]
    mass_max = max(abs(trace.mass_balance_residual) for trace in hydrology.traces)
    hash_chain_ok = all(
        hydrology.traces[index - 1].output_state_hash == hydrology.traces[index].input_state_hash
        for index in range(1, len(hydrology.traces))
    )
    decisions = [d for d in project_trace.decisions if d.subject_id == "nereid_01"]
    prior_result_reused = all(
        project_trace.resolutions[index - 1].ref in decisions[index].subjective_evidence_refs
        for index in range(1, min(len(decisions), len(project_trace.resolutions)))
    )

    # Counterfactual 1: a moderate opening plus mundane route work can help Trade
    # without satisfying the Nereid's stricter aquatic predicate.
    moderate_world, _, moderate, _ = _physical_fixture()
    moderate.apply_sluice_position(0.40)
    moderate.clear_gallery_rubble(0.70)
    _advance_days(moderate_world, 30)

    # Counterfactual 2: sustained higher flow can satisfy the water route while
    # an uncleared gallery floods and the vulnerable bank erodes.
    high_world, high_ledger, high, _ = _physical_fixture()
    high.apply_sluice_position(0.60)
    _advance_days(high_world, 30)

    twin_world, _, twin, _ = _physical_fixture()
    twin.apply_sluice_position(0.60)
    _advance_days(twin_world, 30)

    # Counterfactual 3: identical flow history, different bank history.
    reinforced_world, reinforced_ledger, reinforced, _ = _physical_fixture()
    reinforced.apply_sluice_position(0.60)
    reinforced.reinforce_bank(0.50)
    _advance_days(reinforced_world, 30)

    # Counterfactual 4: a short high-flow intervention ends before burial exposure.
    brief_world, brief_ledger, brief, _ = _physical_fixture()
    brief.apply_sluice_position(0.80)
    brief_world.advance(2 * 360)
    brief.apply_sluice_position(0.0)
    brief_world.advance(30 * DAY_MINUTES - 2 * 360)

    # Counterfactual 5: route engineering can create a genuine, temporary overlap
    # rather than a scripted compromise flag.
    overlap_world, _, overlap, _ = _physical_fixture()
    overlap.apply_sluice_position(0.70)
    overlap.clear_gallery_rubble(0.70)
    overlap_world.advance(2 * 360)

    # Counterfactual 6: a damaged nominally closed gate leaks persistently but
    # does not become a magic open/closed switch.
    damaged_world, _, damaged, _ = _physical_fixture()
    damaged.damage_gate(0.70)
    damaged_world.advance(10 * 360)

    # Scheduler falsification: one 30-day clock jump still executes all 120 six-hour ticks.
    jump_world, _, jump, jump_runtime = _physical_fixture()
    jump_world.advance(30 * DAY_MINUTES)

    checks = (
        HydrologyTrialCheck(
            "fixed process clock survives a large world-time jump",
            len(jump.traces) == 120 and len(jump_runtime.runs) == 120,
            f"hydrology_ticks={len(jump.traces)}; runtime_runs={len(jump_runtime.runs)}",
        ),
        HydrologyTrialCheck(
            "baseline water mass is conserved with explicit sources sinks and spill",
            mass_max <= 1e-10,
            f"max_abs_residual={mass_max:.3e}",
        ),
        HydrologyTrialCheck(
            "hydrology forensic hashes form a continuous state chain",
            hash_chain_ok,
            f"traces={len(hydrology.traces)}",
        ),
        HydrologyTrialCheck(
            "baseline ancient gate does not create Nereid passage",
            not hydrology.state.aquatic_route_viable,
            f"effective_opening={hydrology.state.gate.effective_opening:.4f}",
        ),
        HydrologyTrialCheck(
            "baseline burial remains covered without a story trigger",
            hydrology.state.burial_bank.exposure_fraction == 0.0
            and not any(event.event_type == "BURIAL_COVER_BECAME_EXPOSED" for event in hydrology_events),
            f"cover={hydrology.state.burial_bank.cover_depth_equiv:.4f}",
        ),
        HydrologyTrialCheck(
            "player absence does not pause hydrology or Projects",
            len(hydrology.traces) == elapsed_days * 4 and not player_events and len(nereid.attempt_history) >= 3,
            f"ticks={len(hydrology.traces)}; player_events={len(player_events)}; attempts={len(nereid.attempt_history)}",
        ),
        HydrologyTrialCheck(
            "Nereid attempt is resolved by physical water continuity",
            passage_events
            and all(not event.data.get("route_viable") for event in passage_events)
            and all(attempt.outcome is AttemptOutcome.BLOCKED for attempt in nereid.attempt_history),
            f"passage_attempts={len(passage_events)}; project_status={nereid.status.value}",
        ),
        HydrologyTrialCheck(
            "physical failure becomes later subjective Project evidence",
            len(decisions) >= 2 and prior_result_reused,
            f"decisions={len(decisions)}; resolutions={len(project_trace.resolutions)}",
        ),
        HydrologyTrialCheck(
            "physical resolver does not leak the hydrology answer key into Project state",
            not any(
                token in " ".join(nereid.subjective_evidence_refs)
                for token in ("gate_discharge", "debris_load", "burial_shelf", "hydrology_tick")
            ),
            f"subjective_evidence_refs={len(nereid.subjective_evidence_refs)}",
        ),
        HydrologyTrialCheck(
            "moderate regime can help mortal route without satisfying Nereid",
            moderate.state.gallery.route_state is GalleryRouteState.PASSABLE
            and moderate_world.regions["underpeak"].accessible
            and not moderate.state.aquatic_route_viable,
            f"gallery={moderate.state.gallery.route_state.value}; aquatic={moderate.state.aquatic_route_viable}",
        ),
        HydrologyTrialCheck(
            "sustained higher flow can help Nereid while harming Trade and burial bank",
            high.state.aquatic_route_viable
            and high.state.nodes["underpeak_gallery_sump"].level >= 0.45
            and high.state.burial_bank.exposure_fraction > 0.0,
            f"aquatic={high.state.aquatic_route_viable}; gallery_level={high.state.nodes['underpeak_gallery_sump'].level:.3f}; exposure={high.state.burial_bank.exposure_fraction:.3f}",
        ),
        HydrologyTrialCheck(
            "identical physical history is deterministic",
            high.state.state_hash() == twin.state.state_hash()
            and [trace.output_state_hash for trace in high.traces]
            == [trace.output_state_hash for trace in twin.traces],
            f"final_hash={high.state.state_hash()[:16]}",
        ),
        HydrologyTrialCheck(
            "capacity spill is explicit rather than silently clamped away",
            sum(sum(trace.spill_totals.values()) for trace in high.traces) > 0.0
            and max(abs(trace.mass_balance_residual) for trace in high.traces) <= 1e-10,
            f"recorded_spill={sum(sum(trace.spill_totals.values()) for trace in high.traces):.4f}",
        ),
        HydrologyTrialCheck(
            "raw physical transitions do not masquerade as divine percepts",
            bool([e for e in high_ledger.events if "world_process" in e.tags])
            and all(
                any(barrier.kind == "raw_world_process_state" for barrier in event.perceptual_barriers)
                for event in high_ledger.events
                if "world_process" in event.tags
            ),
            f"guarded_transitions={len([e for e in high_ledger.events if 'world_process' in e.tags])}",
        ),
        HydrologyTrialCheck(
            "bank reinforcement changes burial outcome under the same gate regime",
            high.state.burial_bank.exposure_fraction > 0.0
            and reinforced.state.burial_bank.exposure_fraction == 0.0
            and any(e.event_type == "BURIAL_COVER_BECAME_EXPOSED" for e in high_ledger.events)
            and not any(e.event_type == "BURIAL_COVER_BECAME_EXPOSED" for e in reinforced_ledger.events),
            f"unreinforced_cover={high.state.burial_bank.cover_depth_equiv:.3f}; reinforced_cover={reinforced.state.burial_bank.cover_depth_equiv:.3f}",
        ),
        HydrologyTrialCheck(
            "brief high flow can end without exposing the burial",
            brief.state.burial_bank.exposure_fraction == 0.0
            and not any(e.event_type == "BURIAL_COVER_BECAME_EXPOSED" for e in brief_ledger.events),
            f"cover_after_30d={brief.state.burial_bank.cover_depth_equiv:.3f}",
        ),
        HydrologyTrialCheck(
            "gallery work can create a real temporary Nereid-Trade overlap",
            overlap.state.aquatic_route_viable
            and overlap.state.gallery.route_state in {GalleryRouteState.PASSABLE, GalleryRouteState.RISKY},
            f"aquatic={overlap.state.aquatic_route_viable}; gallery={overlap.state.gallery.route_state.value}",
        ),
        HydrologyTrialCheck(
            "damaged closed gate leaks without becoming passable",
            damaged.state.gate.sluice_position == 0.0
            and damaged.last_trace is not None
            and damaged.last_trace.edge_flows["gate_discharge"] > hydrology.last_trace.edge_flows["gate_discharge"]
            and not damaged.state.aquatic_route_viable,
            f"integrity={damaged.state.gate.structure_integrity:.2f}; discharge={damaged.last_trace.edge_flows['gate_discharge']:.4f}",
        ),
        HydrologyTrialCheck(
            "P3 runtimes stayed healthy",
            not project_runtime.errors and not simulation.tick_errors and nereid.status is ProjectStatus.ACTIVE,
            f"project_errors={len(project_runtime.errors)}; simulation_errors={len(simulation.tick_errors)}",
        ),
    )
    return HydrologyAcceptanceResult(
        checks=checks,
        world=world,
        ledger=ledger,
        hydrology=hydrology,
        process_runtime=process_runtime,
        projects=projects,
        project_runtime=project_runtime,
        project_trace=project_trace,
    )
