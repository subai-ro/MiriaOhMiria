from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Callable, Protocol, TypeVar

from .affordances import (
    BANK_TARGET,
    LocalSubjectState,
    PhysicalActionRequest,
    PhysicalActionResult,
    PhysicalActionType,
    PhysicalAffordanceBridge,
    create_silver_thread_affordance_bridge,
)
from .archive import Archive
from .attention import AttentionDirective
from .divine import (
    DeathGodPrototypeBrain,
    DivineActionType,
    DivineCognitivePosture,
    DivineDecision,
    DivineIntent,
    DivineMindState,
    DivinePercept,
    DivineRuntime,
    create_prototype_divine_runtime,
)
from .engine import WorldEngine
from .heralds import HeraldSystem
from .ledger import EventLedger
from .models import Action, ActionResult, WorldState
from .project_runtime import ProjectRuntime
from .projects import PersistentProjectStore, seed_silver_thread_projects
from .processes import HydrologyProcess, WorldProcessRuntime, create_silver_thread_hydrology
from .processes.aqueous_echo import (
    AqueousEchoSenseBridge,
    AqueousSilverEchoProcess,
    EchoSenseRequest,
    EchoSenseResult,
    create_silver_thread_aqueous_echo,
    create_silver_thread_echo_sense_bridge,
)
from .provenance import CausalTrace
from .seed import create_world


DEATH_PROJECT_ID = "death_preserve_truthful_memory"


class _ActionResult(Protocol):
    @property
    def ok(self) -> bool: ...


_Result = TypeVar("_Result", bound=_ActionResult)


class AshValleyDeathBrain:
    """Pilot policy layered over the frozen D.1.4.2 reference brain.

    A direct prayer can justify a question. It cannot reveal why the mortal
    prayed, whether a burial exists, or what objective hydrology did nearby.
    """

    def __init__(self) -> None:
        self._base = DeathGodPrototypeBrain()

    def decide(self, percept: DivinePercept, state: DivineMindState) -> DivineDecision:
        decision = self._base.decide(percept, state)
        if decision.intents:
            return decision

        prayers = tuple(
            item
            for item in percept.knowledge
            if item.event_type == "PRAYER_OFFERED"
            and "death" in item.tags
            and item.location_id == "underpeak"
            and item.known_actor_ids
        )
        if not prayers:
            return decision

        prayer = min(prayers, key=lambda item: item.knowledge_id)
        actor_id = prayer.known_actor_ids[0]
        causal_event_ids = prayer.source_event_ids
        state.actor_interest[actor_id] = max(0.25, state.actor_interest.get(actor_id, 0.0))

        threads = {item.actor_id: item for item in decision.attention_threads}
        other_thread_total = sum(
            item.intensity for key, item in threads.items() if key != actor_id
        )
        remaining = max(
            0.0,
            percept.consciousness_budget
            - sum(intensity for _, intensity in decision.focus_allocations)
            - other_thread_total,
        )
        prior_intensity = threads.get(actor_id).intensity if actor_id in threads else 0.0
        thread_intensity = min(max(0.25, prior_intensity), remaining)
        if thread_intensity > 0.0:
            threads[actor_id] = AttentionDirective(
                actor_id=actor_id,
                intensity=thread_intensity,
                reason="identified mortal directly addressed Death from Underpeak",
                causal_event_ids=causal_event_ids,
            )

        probe = DivineIntent(
            action_type=DivineActionType.SEND_PROBE,
            target_actor_id=actor_id,
            location_id=prayer.location_id,
            significance=0.52,
            message=(
                "You called upon Death from beneath the mountain. "
                "What did you witness, and why did you call?"
            ),
            reason=(
                "an identified mortal directly addressed this deity from Underpeak; "
                "inquiry only, not proof of burial or danger"
            ),
            causal_event_ids=causal_event_ids,
            observation_minutes=60,
        )
        note = (
            "A direct address from Underpeak intersects the concern for death and truthful "
            "remembrance, but supplies no fact about what happened there. Ask once before judging."
        )
        return replace(
            decision,
            goal=(
                "Learn why an identified mortal addressed Death from Underpeak without "
                "assuming what happened there."
            ),
            decision_note=f"{decision.decision_note} {note}".strip(),
            cognitive_posture=DivineCognitivePosture.INVESTIGATE,
            significance=max(decision.significance, probe.significance),
            attention_threads=tuple(sorted(threads.values(), key=lambda item: item.actor_id)),
            intents=(probe,),
        )


class PilotClock:
    """Orchestration facade over the one authoritative WorldState clock."""

    def __init__(
        self,
        world: WorldState,
        project_runtime: ProjectRuntime,
        divine_runtime: DivineRuntime,
        *,
        serial_actions: bool = False,
    ) -> None:
        self.world = world
        self.project_runtime = project_runtime
        self.divine_runtime = divine_runtime
        self._errors: list[str] = []
        self._serial_actions = serial_actions
        self._action_depth = 0
        self._dispatching = False
        self._advance_failure: Exception | None = None

    @property
    def serial_actions(self) -> bool:
        return self._serial_actions

    @property
    def _busy(self) -> bool:
        return self._action_depth > 0 or self._dispatching

    @property
    def game_minute(self) -> int:
        if self.serial_actions:
            self._raise_if_failed()
        return self.world.game_minute

    @property
    def errors(self) -> tuple[str, ...]:
        return tuple(self._errors)

    def advance(self, minutes: int) -> None:
        if not self.serial_actions:
            self.world.advance(minutes)
            self.project_runtime.tick(self.world.game_minute)
            self._tick_divine()
            return
        self._raise_if_failed()
        if isinstance(minutes, bool) or not isinstance(minutes, int) or minutes <= 0:
            raise ValueError("World clock requires a positive integer interval")
        if self._busy:
            self._advance_world(minutes)
            return

        target_minute = self.world.game_minute + minutes
        while self.world.game_minute < target_minute:
            due = self.project_runtime.next_review_minute
            if due is not None and due <= self.world.game_minute:
                self._drain_ready()
                # Timed work belongs inside the requested elapsed interval.
                # Already-started work may finish beyond its target, exactly once.
                if self.world.game_minute >= target_minute:
                    break
                due = self.project_runtime.next_review_minute
                if due is not None and due <= self.world.game_minute:
                    continue
            stop = target_minute if due is None else min(target_minute, due)
            self._advance_world(stop - self.world.game_minute)
            self._drain_ready()

    def advance_action_time(self, minutes: int) -> None:
        if self.serial_actions and not self._busy:
            raise RuntimeError("Timed pilot work requires a PilotSession action boundary")
        self.advance(minutes)

    def run_action(self, operation: Callable[[], _Result]) -> _Result:
        """Serialize a whole commit, not just its internal duration callback."""
        if not self.serial_actions:
            return operation()
        self._raise_if_failed()
        outermost = not self._busy
        before = self.world.game_minute
        self._action_depth += 1
        try:
            result = operation()
        finally:
            self._action_depth -= 1
        # Exceptions do not dispatch minds into a possibly incomplete commit.
        # A completed-but-blocked action may have spent time despite ok=False.
        if outermost and (result.ok or self.world.game_minute > before):
            self._drain_ready()
        return result

    def _advance_world(self, minutes: int) -> None:
        try:
            self.world.advance(minutes)
        except Exception as exc:
            self._advance_failure = exc
            self._errors.append(f"authoritative advance failed: {type(exc).__name__}: {exc}")
            raise

    def _raise_if_failed(self) -> None:
        if self._advance_failure is not None:
            raise RuntimeError("Pilot stopped after an authoritative world advance failure") from self._advance_failure

    def _drain_ready(self) -> None:
        if self._busy:
            return
        self._dispatching = True
        try:
            self.project_runtime.tick(self.world.game_minute)
            # ProjectRuntime tolerates mind/resolver errors; an authoritative
            # physics failure must still stop this session, not become a retry.
            self._raise_if_failed()
            self._tick_divine()
        finally:
            self._dispatching = False

    def _tick_divine(self) -> None:
        try:
            self.divine_runtime.tick()
        except Exception as exc:
            self._errors.append(
                f"minute {self.world.game_minute}: {type(exc).__name__}: {exc}"
            )


@dataclass(frozen=True)
class PilotSession:
    """Thin composition root; all authority remains in the existing runtimes."""

    world: WorldState
    ledger: EventLedger
    archive: Archive
    heralds: HeraldSystem
    engine: WorldEngine
    hydrology: HydrologyProcess
    aqueous_echo: AqueousSilverEchoProcess
    world_process_runtime: WorldProcessRuntime
    projects: PersistentProjectStore
    project_trace: CausalTrace
    project_runtime: ProjectRuntime
    divine_runtime: DivineRuntime
    clock: PilotClock
    affordances: PhysicalAffordanceBridge
    aqueous_echo_sensing: AqueousEchoSenseBridge

    def apply(self, action: Action) -> ActionResult:
        return self.clock.run_action(lambda: self.engine.apply(action))

    def perform(self, request: PhysicalActionRequest) -> PhysicalActionResult:
        return self.clock.run_action(lambda: self.affordances.perform(request))

    def sense_echo(self, request: EchoSenseRequest) -> EchoSenseResult:
        return self.clock.run_action(lambda: self.aqueous_echo_sensing.sense(request))

    def advance(self, minutes: int) -> None:
        self.clock.advance(minutes)


def create_pilot_i0_session(
    *,
    seed: int = 42,
    synthetic_actors: int = 0,
    serial_actions: bool = False,
) -> PilotSession:
    """Compose the smallest D.1.4.2 -> D.2.x Ash Valley pilot seam."""

    if not isinstance(serial_actions, bool):
        raise ValueError("serial_actions must be boolean")
    world = create_world(seed=seed, synthetic_actors=synthetic_actors)
    # Authored T0 placement is setup, not a forced outcome. Underpeak remains
    # sealed to ordinary travel and every later consequence uses its resolver.
    world.actors["arra"].location_id = "underpeak"

    ledger = EventLedger()
    archive = Archive()
    heralds = HeraldSystem(world, archive)
    heralds.attach(ledger)
    engine = WorldEngine(world, ledger=ledger, seed=seed + 1)

    hydrology = create_silver_thread_hydrology(world, ledger)
    aqueous_echo = create_silver_thread_aqueous_echo(world, ledger, hydrology)
    world_process_runtime = WorldProcessRuntime(start_minute=world.game_minute)
    world_process_runtime.register(hydrology)
    world_process_runtime.register(aqueous_echo)
    world_process_runtime.attach(world)

    projects = seed_silver_thread_projects(world.game_minute)
    projects.create(
        project_id=DEATH_PROJECT_ID,
        owner_id="god_death",
        desire="Preserve truthful memory and attribution where the living disturb the dead.",
        motivation=(
            "Death is responsible for boundaries, memory, and burial, but must not judge "
            "from facts that never reached it."
        ),
        commitment=0.74,
        known_constraints=(
            "direct address and domain resonance do not reveal objective events",
            "mortal testimony may be incomplete, mistaken, or false",
        ),
        hypotheses=("an apparent disturbance near a death threshold may merit inquiry",),
        current_strategy="wait for lawfully perceived signs or testimony, then ask before judging",
        subjective_evidence_refs=(),
        created_minute=world.game_minute,
        next_review_minute=world.game_minute + 24 * 60,
    )
    project_trace = CausalTrace(ledger)
    project_runtime = ProjectRuntime(
        projects, project_trace,
        # Read only after composition is complete. The facade also prevents a
        # second project review after a fatal physical listener failure.
        clock=(lambda: clock.game_minute) if serial_actions else None,
    )

    divine_runtime = create_prototype_divine_runtime(
        world,
        ledger,
        heralds,
        death_brain=AshValleyDeathBrain(),
    )
    clock = PilotClock(world, project_runtime, divine_runtime, serial_actions=serial_actions)

    affordances = create_silver_thread_affordance_bridge(
        world,
        ledger,
        hydrology,
        advance_time=clock.advance_action_time,
    )
    affordances.register_subject(
        LocalSubjectState(
            subject_id="arra",
            subject_kind="mortal_player",
            present_site_ids=("underpeak_upper_reach",),
            faculties=("sight",),
            capability_levels={PhysicalActionType.INSPECT_BANK.value: 0.62},
            resources={"effort": 2.0},
        )
    )
    aqueous_echo_sensing = create_silver_thread_echo_sense_bridge(
        world,
        ledger,
        aqueous_echo,
        affordances,
        advance_time=clock.advance_action_time,
    )

    return PilotSession(
        world=world,
        ledger=ledger,
        archive=archive,
        heralds=heralds,
        engine=engine,
        hydrology=hydrology,
        aqueous_echo=aqueous_echo,
        world_process_runtime=world_process_runtime,
        projects=projects,
        project_trace=project_trace,
        project_runtime=project_runtime,
        divine_runtime=divine_runtime,
        clock=clock,
        affordances=affordances,
        aqueous_echo_sensing=aqueous_echo_sensing,
    )


def inspect_arra_bank(session: PilotSession) -> PhysicalActionResult:
    """Convenience for the I0 proof; resolution remains in the D.2.2 bridge."""

    return session.perform(
        PhysicalActionRequest(
            subject_id="arra",
            action_type=PhysicalActionType.INSPECT_BANK,
            target_ref=BANK_TARGET,
        )
    )
