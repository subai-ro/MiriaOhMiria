from __future__ import annotations

from dataclasses import dataclass

from .engine import WorldEngine
from .ledger import EventLedger
from .project_runtime import (
    IntentResolution,
    ProjectDecision,
    ProjectIntent,
    ProjectMind,
    ProjectPercept,
    ProjectRuntime,
)
from .projects import AttemptOutcome, ProjectStatus, seed_silver_thread_projects
from .provenance import CausalEdgeKind, CausalTrace
from .seed import create_world
from .simulation import Simulation


DAY_MINUTES = 24 * 60


@dataclass(frozen=True)
class ProjectTrialCheck:
    name: str
    ok: bool
    detail: str


@dataclass(frozen=True)
class PrehistoryTrialResult:
    elapsed_days: int
    checks: tuple[ProjectTrialCheck, ...]
    projects: object
    trace: CausalTrace
    engine: WorldEngine
    runtime: ProjectRuntime

    @property
    def passed(self) -> bool:
        return all(check.ok for check in self.checks)


class LabNereidMind(ProjectMind):
    """Deterministic acceptance double. This is explicitly not canonical Nereid behavior."""

    def decide(self, percept: ProjectPercept) -> ProjectDecision:
        attempts = percept.project.attempt_history
        if not attempts:
            strategy = "test the remembered route without assuming it is still passable"
            approach = "remembered_route"
            constraints: tuple[str, ...] = ()
            hypotheses = percept.project.hypotheses
        elif len(attempts) == 1:
            strategy = "seek an alternate access hypothesis after the blocked remembered route"
            approach = "alternate_access_hypothesis"
            constraints = ("remembered_underpeak_access_is_currently_blocked",)
            hypotheses = ("present access requires a change in the shared world state",)
        else:
            strategy = "retest the blocked access only after allowing the world time to change"
            approach = "delayed_retest"
            constraints = ("remembered_underpeak_access_is_currently_blocked",)
            hypotheses = ("present access requires a change in the shared world state",)

        return ProjectDecision(
            strategy=strategy,
            subjective_evidence_refs=percept.available_evidence_refs,
            next_review_minute=percept.game_minute + 7 * DAY_MINUTES,
            intents=(
                ProjectIntent(
                    intent_type="lab_attempt_region_access",
                    target_refs=("region:underpeak",),
                    params={"approach": approach},
                ),
            ),
            known_constraints_add=constraints,
            hypotheses=hypotheses,
        )


class LegacyRegionAccessResolver:
    """Acceptance-only bridge to the pre-hydrology region accessibility predicate."""

    rule_id = "legacy.region_accessible.v1"

    def __init__(self, engine: WorldEngine) -> None:
        self.engine = engine

    def resolve(self, *, project, intent: ProjectIntent, game_minute: int) -> IntentResolution:
        if len(intent.target_refs) != 1 or not intent.target_refs[0].startswith("region:"):
            return IntentResolution(
                ok=False,
                outcome=AttemptOutcome.BLOCKED,
                message="resolver requires exactly one region target",
            )
        region_id = intent.target_refs[0].split(":", 1)[1]
        region = self.engine.world.regions.get(region_id)
        if region is None:
            return IntentResolution(
                ok=False,
                outcome=AttemptOutcome.BLOCKED,
                message="target region does not exist",
            )

        accessible = bool(region.accessible)
        event = self.engine.ledger.append(
            game_minute=game_minute,
            event_type="LAB_REGION_ACCESS_ATTEMPTED",
            actor_ids=(project.owner_id,),
            target_ids=(region_id,),
            location_id="northwood",
            tags=("lab", "project_attempt", "movement"),
            witness_ids=(),
            publicity=0.0,
            secrecy=1.0,
            data={"accessible": accessible, "project_ref": project.ref},
        )
        return IntentResolution(
            ok=accessible,
            outcome=AttemptOutcome.SUCCEEDED if accessible else AttemptOutcome.BLOCKED,
            message=(
                "authoritative region predicate allowed access"
                if accessible
                else "authoritative region predicate blocked access"
            ),
            result_event_ids=(event.event_id,),
        )


def run_no_player_prehistory_trial(
    *, seed: int = 42, elapsed_days: int = 30
) -> PrehistoryTrialResult:
    if elapsed_days <= 0:
        raise ValueError("elapsed_days must be positive")

    world = create_world(seed=seed, synthetic_actors=0)
    engine = WorldEngine(world, EventLedger(), seed=seed + 1)
    projects = seed_silver_thread_projects(world.game_minute)
    trace = CausalTrace(engine.ledger)
    runtime = ProjectRuntime(projects, trace)
    runtime.register_mind("nereid_01", LabNereidMind())
    runtime.register_resolver("lab_attempt_region_access", LegacyRegionAccessResolver(engine))

    simulation = Simulation(engine, minutes_per_step=360, seed=seed + 2)
    simulation.subscribe_tick(lambda: runtime.tick(world.game_minute))
    simulation.run(elapsed_days * 4)

    nereid = projects.get("nereid_return_underpeak")
    trade = projects.get("trade_house_underpeak_route")
    player_events = [event for event in engine.ledger.events if "arra" in event.actor_ids]
    nereid_events = [event for event in engine.ledger.events if "nereid_01" in event.actor_ids]
    decisions = [decision for decision in trace.decisions if decision.subject_id == "nereid_01"]
    resolutions = trace.resolutions
    later_decisions_use_prior_result = all(
        resolutions[index - 1].ref in decisions[index].subjective_evidence_refs
        for index in range(1, min(len(decisions), len(resolutions)))
    )
    strategies = tuple(attempt.strategy for attempt in nereid.attempt_history)
    edge_kinds = {edge.kind for edge in trace.edges()}

    checks = (
        ProjectTrialCheck(
            "world advanced without player action",
            world.game_minute == elapsed_days * DAY_MINUTES and not player_events,
            f"minute={world.game_minute}; Arra-authored events={len(player_events)}",
        ),
        ProjectTrialCheck(
            "Nereid project predates player relevance",
            nereid.created_minute == 0 and nereid.created_minute < world.game_minute,
            f"created={nereid.created_minute}; now={world.game_minute}",
        ),
        ProjectTrialCheck(
            "unfinished desire survived repeated failure",
            nereid.status is ProjectStatus.ACTIVE and len(nereid.attempt_history) >= 3,
            f"status={nereid.status.value}; attempts={len(nereid.attempt_history)}",
        ),
        ProjectTrialCheck(
            "authoritative resolver, not the mind, decided passage failure",
            bool(nereid.attempt_history)
            and all(attempt.outcome is AttemptOutcome.BLOCKED for attempt in nereid.attempt_history)
            and not world.regions["underpeak"].accessible,
            "legacy underpeak accessibility remained false",
        ),
        ProjectTrialCheck(
            "failed attempt became later decision evidence",
            len(decisions) >= 2 and later_decisions_use_prior_result,
            f"decisions={len(decisions)}; resolutions={len(resolutions)}",
        ),
        ProjectTrialCheck(
            "strategy can change without replacing the underlying project",
            len(set(strategies)) >= 2 and nereid.desire.startswith("Regain meaningful water connectivity"),
            f"distinct strategies={len(set(strategies))}; project={nereid.project_id}",
        ),
        ProjectTrialCheck(
            "independent Trade House project also persists",
            trade.status is ProjectStatus.ACTIVE and trade.created_minute == 0,
            f"status={trade.status.value}; attempts={len(trade.attempt_history)}",
        ),
        ProjectTrialCheck(
            "forensic braid reaches objective results",
            {
                CausalEdgeKind.PROJECT_CONTEXT,
                CausalEdgeKind.DECISION_INPUT,
                CausalEdgeKind.AUTHORED_INTENT,
                CausalEdgeKind.ACTION_RESOLUTION,
                CausalEdgeKind.OBJECTIVE_RESULT,
            }.issubset(edge_kinds)
            and len(nereid_events) == len(nereid.attempt_history),
            f"trace edges={len(trace.edges())}; objective Nereid events={len(nereid_events)}",
        ),
        ProjectTrialCheck(
            "project schema has no mandatory player role",
            "player_id" not in nereid.as_dict() and "arra" not in nereid.as_dict().values(),
            "PersistentProject contains owner/desire/state, not an assigned player slot",
        ),
        ProjectTrialCheck(
            "project runtime stayed healthy",
            not runtime.errors and not simulation.tick_errors,
            f"runtime_errors={len(runtime.errors)}; tick_errors={len(simulation.tick_errors)}",
        ),
    )
    return PrehistoryTrialResult(
        elapsed_days=elapsed_days,
        checks=checks,
        projects=projects,
        trace=trace,
        engine=engine,
        runtime=runtime,
    )
