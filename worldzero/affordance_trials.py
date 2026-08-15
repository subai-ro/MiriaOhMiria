from __future__ import annotations

import json
from dataclasses import dataclass

from .affordances import (
    BANK_TARGET,
    GATE_SITE,
    GATE_TARGET,
    LocalSubjectState,
    PhysicalActionRequest,
    PhysicalActionType,
    PhysicalAffordanceBridge,
    SubjectiveWorldView,
    create_silver_thread_affordance_bridge,
)
from .ledger import EventLedger
from .processes import HydrologyProcess, WorldProcessRuntime, create_silver_thread_hydrology
from .seed import create_world


DAY_MINUTES = 24 * 60
FORBIDDEN_SUBJECTIVE_KEYS = (
    "sluice_position",
    "debris_load",
    "structure_integrity",
    "effective_opening",
    "gate_discharge",
    "aquatic_route_viable",
    "burial_shelf",
    "hydrology_tick",
    "state_hash",
)


@dataclass(frozen=True)
class AffordanceTrialCheck:
    name: str
    ok: bool
    detail: str


@dataclass(frozen=True)
class AffordanceAcceptanceResult:
    checks: tuple[AffordanceTrialCheck, ...]
    world: object
    ledger: EventLedger
    hydrology: HydrologyProcess
    process_runtime: WorldProcessRuntime
    bridge: PhysicalAffordanceBridge
    reinforced_hydrology: HydrologyProcess
    unreinforced_hydrology: HydrologyProcess

    @property
    def passed(self) -> bool:
        return all(check.ok for check in self.checks)


class P4LabNereidPolicy:
    """Acceptance double using only a SubjectiveWorldView, never HydrologyState."""

    def decide(self, view: SubjectiveWorldView) -> PhysicalActionRequest | None:
        gate_views = [item for item in view.percepts if item.target_ref == GATE_TARGET]
        if not gate_views:
            return PhysicalActionRequest(
                view.subject_id,
                PhysicalActionType.INSPECT_GATE,
                GATE_TARGET,
            )
        latest = gate_views[-1]
        if latest.cues.get("visible_debris") in {"moderate", "heavy"}:
            return PhysicalActionRequest(
                view.subject_id,
                PhysicalActionType.SHIFT_LOCAL_SILT,
                GATE_TARGET,
                params={"effort": 1.0},
                evidence_refs=(latest.ref,),
            )
        return None


class P4LabTradeGatePolicy:
    """Deterministic interface probe, not an autonomous institutional mind."""

    def decide(
        self,
        view: SubjectiveWorldView,
        *,
        requested_delta: float = 0.35,
    ) -> PhysicalActionRequest:
        gate_views = [item for item in view.percepts if item.target_ref == GATE_TARGET]
        if not gate_views:
            return PhysicalActionRequest(
                view.subject_id,
                PhysicalActionType.INSPECT_GATE,
                GATE_TARGET,
            )
        latest = gate_views[-1]
        if latest.cues.get("visible_debris") != "clear":
            return PhysicalActionRequest(
                view.subject_id,
                PhysicalActionType.CLEAR_GATE_DEBRIS,
                GATE_TARGET,
                params={"effort": 1.0},
                evidence_refs=(latest.ref,),
            )
        return PhysicalActionRequest(
            view.subject_id,
            PhysicalActionType.ADJUST_SLUICE,
            GATE_TARGET,
            params={"effort": 1.0, "delta": requested_delta},
            evidence_refs=(latest.ref,),
        )


def _fixture() -> tuple[object, EventLedger, HydrologyProcess, WorldProcessRuntime, PhysicalAffordanceBridge]:
    world = create_world(seed=42, synthetic_actors=0)
    ledger = EventLedger()
    hydrology = create_silver_thread_hydrology(world, ledger)
    runtime = WorldProcessRuntime(start_minute=world.game_minute)
    runtime.register(hydrology)
    runtime.attach(world)
    bridge = create_silver_thread_affordance_bridge(world, ledger, hydrology)
    return world, ledger, hydrology, runtime, bridge


def _register_remote_arra(bridge: PhysicalAffordanceBridge) -> None:
    bridge.register_subject(
        LocalSubjectState(
            subject_id="arra",
            subject_kind="mortal",
            present_site_ids=("lake_mirror",),
            faculties=("sight",),
            capability_levels={
                PhysicalActionType.INSPECT_GATE.value: 0.70,
                PhysicalActionType.INSPECT_WATER_STATE.value: 0.70,
                PhysicalActionType.ADJUST_SLUICE.value: 0.60,
            },
            resources={"effort": 2.0},
        )
    )


def _register_bank_crew(bridge: PhysicalAffordanceBridge, *, materials: float = 2.0) -> None:
    bridge.register_subject(
        LocalSubjectState(
            subject_id="bank_crew_01",
            subject_kind="mortal_engineering_crew",
            present_site_ids=("underpeak_upper_reach",),
            faculties=("sight", "engineering"),
            capability_levels={
                PhysicalActionType.INSPECT_BANK.value: 1.0,
                PhysicalActionType.REINFORCE_BANK.value: 1.0,
            },
            resources={"effort": 3.0, "materials": materials},
        )
    )


def _collaboration_fixture(*, with_nereid_silt: bool):
    world, ledger, hydrology, runtime, bridge = _fixture()
    nereid_policy = P4LabNereidPolicy()
    if with_nereid_silt:
        first = bridge.perform(nereid_policy.decide(bridge.subject_view("nereid_01")))
        assert first.percept is not None
        shifted = bridge.perform(nereid_policy.decide(bridge.subject_view("nereid_01")))
        assert shifted.ok
    else:
        world.advance(45 + 180)

    trade_policy = P4LabTradeGatePolicy()
    inspected = bridge.perform(trade_policy.decide(bridge.subject_view("trade_house_01")))
    assert inspected.percept is not None
    adjusted = bridge.perform(
        PhysicalActionRequest(
            "trade_house_01",
            PhysicalActionType.ADJUST_SLUICE,
            GATE_TARGET,
            params={"effort": 1.0, "delta": 0.35},
            evidence_refs=(inspected.percept.ref,),
        )
    )
    return world, ledger, hydrology, runtime, bridge, adjusted


def _bank_fixture(*, reinforced: bool, elapsed_days: int):
    world, ledger, hydrology, runtime, bridge = _fixture()
    _register_bank_crew(bridge)
    inspection = bridge.perform(
        PhysicalActionRequest(
            "bank_crew_01",
            PhysicalActionType.INSPECT_BANK,
            BANK_TARGET,
        )
    )
    assert inspection.percept is not None
    reinforcement = None
    if reinforced:
        reinforcement = bridge.perform(
            PhysicalActionRequest(
                "bank_crew_01",
                PhysicalActionType.REINFORCE_BANK,
                BANK_TARGET,
                params={"effort": 1.0},
                evidence_refs=(inspection.percept.ref,),
            )
        )
    else:
        world.advance(720)
    hydrology.apply_sluice_position(0.60)
    world.advance(elapsed_days * DAY_MINUTES)
    return world, ledger, hydrology, runtime, bridge, inspection, reinforcement


def run_affordance_acceptance(*, elapsed_days: int = 30) -> AffordanceAcceptanceResult:
    if elapsed_days < 30:
        raise ValueError("P4 acceptance requires at least 30 counterfactual days")

    world, ledger, hydrology, process_runtime, bridge = _fixture()
    _register_remote_arra(bridge)
    nereid_policy = P4LabNereidPolicy()
    trade_policy = P4LabTradeGatePolicy()

    baseline_hash = hydrology.state.state_hash()
    baseline_minute = world.game_minute
    remote = bridge.perform(
        PhysicalActionRequest("arra", PhysicalActionType.INSPECT_GATE, GATE_TARGET)
    )
    remote_unchanged = (
        hydrology.state.state_hash() == baseline_hash
        and world.game_minute == baseline_minute
        and not bridge.perceptions.for_subject("arra")
    )

    nereid_inspection = bridge.perform(nereid_policy.decide(bridge.subject_view("nereid_01")))
    if nereid_inspection.percept is None:
        raise AssertionError("P4 fixture failed to form Nereid gate percept")
    initial_nereid_percept = nereid_inspection.percept
    initial_subjective_payload = json.dumps(
        initial_nereid_percept.as_dict(), ensure_ascii=False, sort_keys=True
    ).lower()
    initial_ledger_event = next(
        event for event in ledger.events if event.event_id == nereid_inspection.event_id
    )

    before_silt = hydrology.state.gate.debris_load
    before_position = hydrology.state.gate.sluice_position
    silt_request = nereid_policy.decide(bridge.subject_view("nereid_01"))
    if silt_request is None:
        raise AssertionError("P4 Nereid policy did not act on its coarse percept")
    silt = bridge.perform(silt_request)
    after_silt = hydrology.state.gate.debris_load
    after_silt_position = hydrology.state.gate.sluice_position
    nereid_percepts_after_action = len(bridge.perceptions.for_subject("nereid_01"))
    silt_event = next(event for event in ledger.events if event.event_id == silt.event_id)
    world.advance(360)
    perceptions_after_tick = len(bridge.perceptions.for_subject("nereid_01"))
    first_post_silt_trace = hydrology.last_trace
    post_silt_inspection = bridge.perform(
        PhysicalActionRequest(
            "nereid_01",
            PhysicalActionType.INSPECT_GATE,
            GATE_TARGET,
        )
    )
    if post_silt_inspection.percept is None:
        raise AssertionError("P4 fixture failed to form post-silt percept")

    trade_inspection = bridge.perform(trade_policy.decide(bridge.subject_view("trade_house_01")))
    if trade_inspection.percept is None:
        raise AssertionError("P4 fixture failed to form Trade gate percept")
    stolen_before_hash = hydrology.state.state_hash()
    stolen_before_minute = world.game_minute
    stolen = bridge.perform(
        PhysicalActionRequest(
            "trade_house_01",
            PhysicalActionType.ADJUST_SLUICE,
            GATE_TARGET,
            params={"effort": 1.0, "delta": 0.20},
            evidence_refs=(post_silt_inspection.percept.ref,),
        )
    )
    stolen_atomic = (
        hydrology.state.state_hash() == stolen_before_hash
        and world.game_minute == stolen_before_minute
    )

    clear = bridge.perform(trade_policy.decide(bridge.subject_view("trade_house_01")))
    trade_after_clear = bridge.perform(
        PhysicalActionRequest(
            "trade_house_01",
            PhysicalActionType.INSPECT_GATE,
            GATE_TARGET,
        )
    )
    if trade_after_clear.percept is None:
        raise AssertionError("P4 fixture failed to inspect after debris work")

    adjust_results = []
    for delta in (0.35, 0.35, 0.15):
        adjustment = bridge.perform(
            PhysicalActionRequest(
                "trade_house_01",
                PhysicalActionType.ADJUST_SLUICE,
                GATE_TARGET,
                params={"effort": 1.0, "delta": delta},
                evidence_refs=(trade_after_clear.percept.ref,),
            )
        )
        adjust_results.append(adjustment)
    final_adjust_event_id = adjust_results[-1].event_id

    pre_consequence_nereid_percepts = len(bridge.perceptions.for_subject("nereid_01"))
    world.advance(720)
    post_consequence_nereid_percepts = len(bridge.perceptions.for_subject("nereid_01"))
    route_events = [event for event in ledger.events if event.event_type == "AQUATIC_ROUTE_BECAME_VIABLE"]
    post_route_water = bridge.perform(
        PhysicalActionRequest(
            "nereid_01",
            PhysicalActionType.INSPECT_WATER_STATE,
            "underpeak_gate_forebay",
        )
    )
    if post_route_water.percept is None:
        raise AssertionError("P4 fixture failed to form post-route water percept")
    post_route_payload = json.dumps(
        post_route_water.percept.as_dict(), ensure_ascii=False, sort_keys=True
    ).lower()

    poor_world, _, poor_hydrology, _, poor_bridge = _fixture()
    _register_bank_crew(poor_bridge, materials=0.0)
    poor_inspection = poor_bridge.perform(
        PhysicalActionRequest(
            "bank_crew_01",
            PhysicalActionType.INSPECT_BANK,
            BANK_TARGET,
        )
    )
    if poor_inspection.percept is None:
        raise AssertionError("P4 fixture failed to form poor crew bank percept")
    poor_hash = poor_hydrology.state.state_hash()
    poor_minute = poor_world.game_minute
    poor_reinforcement = poor_bridge.perform(
        PhysicalActionRequest(
            "bank_crew_01",
            PhysicalActionType.REINFORCE_BANK,
            BANK_TARGET,
            params={"effort": 1.0},
            evidence_refs=(poor_inspection.percept.ref,),
        )
    )
    poor_atomic = (
        poor_hydrology.state.state_hash() == poor_hash
        and poor_world.game_minute == poor_minute
    )

    collaborative = _collaboration_fixture(with_nereid_silt=True)
    solo = _collaboration_fixture(with_nereid_silt=False)
    collaborative_twin = _collaboration_fixture(with_nereid_silt=True)
    collaborative_delta = collaborative[4].action_traces[-1].effect.get("applied_delta", 0.0)
    solo_delta = solo[4].action_traces[-1].effect.get("applied_delta", 0.0)
    deterministic_collaboration = (
        collaborative[2].state.state_hash() == collaborative_twin[2].state.state_hash()
        and [item.as_dict() for item in collaborative[4].action_traces]
        == [item.as_dict() for item in collaborative_twin[4].action_traces]
        and [item.as_dict() for item in collaborative[4].perceptions.all_percepts]
        == [item.as_dict() for item in collaborative_twin[4].perceptions.all_percepts]
    )

    reinforced = _bank_fixture(reinforced=True, elapsed_days=elapsed_days)
    unreinforced = _bank_fixture(reinforced=False, elapsed_days=elapsed_days)
    reinforced_hydrology = reinforced[2]
    unreinforced_hydrology = unreinforced[2]
    reinforced_percept_payload = json.dumps(
        reinforced[5].percept.as_dict(), ensure_ascii=False, sort_keys=True
    ).lower()

    physical_events = [
        event for event in ledger.events if "physical_affordance" in event.tags
    ]
    inspection_events = [
        event for event in ledger.events if event.event_type == "LOCAL_INSPECTION_PERFORMED"
    ]
    raw_transitions = [event for event in ledger.events if "world_process" in event.tags]
    action_event_ids = {
        item.event_id for item in bridge.action_traces if item.event_id is not None
    }
    traced_action_ids = {
        event_id
        for trace in hydrology.traces
        for event_id in trace.causal_action_event_ids
    }
    forbidden_events = [
        event
        for event in ledger.events
        if "QUEST" in event.event_type or "PROJECT_COMPLETED" in event.event_type
    ]

    checks = (
        AffordanceTrialCheck(
            "remote inspection is rejected without touching time or physics",
            not remote.ok and remote_unchanged,
            f"outcome={remote.outcome.value}; minute={world.game_minute if not remote_unchanged else baseline_minute}",
        ),
        AffordanceTrialCheck(
            "local inspection creates one private percept",
            nereid_inspection.ok
            and len([p for p in bridge.perceptions.all_percepts if p.ref == initial_nereid_percept.ref]) == 1,
            f"percept={initial_nereid_percept.ref}; owner={initial_nereid_percept.subject_id}",
        ),
        AffordanceTrialCheck(
            "subjective gate view is qualitative and contains no hydrology answer key",
            all(token not in initial_subjective_payload for token in FORBIDDEN_SUBJECTIVE_KEYS)
            and all(isinstance(value, str) for value in initial_nereid_percept.cues.values()),
            f"cues={','.join(sorted(initial_nereid_percept.cues))}",
        ),
        AffordanceTrialCheck(
            "objective inspection event withholds the private percept payload",
            initial_ledger_event.data.get("percept_payload_withheld_from_ledger") is True
            and not any(key in initial_ledger_event.data for key in initial_nereid_percept.cues),
            f"event={initial_ledger_event.event_id}; ledger_keys={','.join(sorted(initial_ledger_event.data))}",
        ),
        AffordanceTrialCheck(
            "lab Nereid acts only from its own SubjectiveWorldView",
            silt_request.evidence_refs == (initial_nereid_percept.ref,)
            and silt_request.subject_id == "nereid_01",
            f"evidence={','.join(silt_request.evidence_refs)}",
        ),
        AffordanceTrialCheck(
            "lesser-entity silt influence is bounded and physically narrow",
            silt.ok
            and 0.0 < before_silt - after_silt <= 0.08
            and after_silt_position == before_position,
            f"removed={before_silt-after_silt:.4f}; initial_sluice={before_position:.3f}",
        ),
        AffordanceTrialCheck(
            "silt influence cannot declare passage or move the sluice",
            after_silt_position == before_position == 0.0
            and silt_event.event_type == "LOCAL_SILT_SHIFTED"
            and not any(event.event_type == "AQUATIC_ROUTE_BECAME_VIABLE" for event in ledger.events if event.event_id <= silt_event.event_id),
            f"sluice_after_silt={after_silt_position:.3f}; event={silt_event.event_id}",
        ),
        AffordanceTrialCheck(
            "physical action does not manufacture a new observation",
            nereid_percepts_after_action == 1 and perceptions_after_tick == 1,
            f"after_action={nereid_percepts_after_action}; after_tick={perceptions_after_tick}",
        ),
        AffordanceTrialCheck(
            "a later local inspection can perceive a coarse physical change",
            post_silt_inspection.percept.cues.get("visible_debris")
            != initial_nereid_percept.cues.get("visible_debris"),
            f"before={initial_nereid_percept.cues.get('visible_debris')}; after={post_silt_inspection.percept.cues.get('visible_debris')}",
        ),
        AffordanceTrialCheck(
            "one subject cannot cite another subject's private percept",
            not stolen.ok and stolen_atomic,
            f"outcome={stolen.outcome.value}; state_unchanged={stolen_atomic}",
        ),
        AffordanceTrialCheck(
            "resources are enforced before time or state mutation",
            not poor_reinforcement.ok and poor_atomic,
            f"outcome={poor_reinforcement.outcome.value}; state_unchanged={poor_atomic}",
        ),
        AffordanceTrialCheck(
            "Trade clears debris through the production physical resolver",
            clear.ok
            and clear.event_id in action_event_ids
            and hydrology.state.gate.debris_load < after_silt,
            f"event={clear.event_id}; current_debris={hydrology.state.gate.debris_load:.4f}",
        ),
        AffordanceTrialCheck(
            "ordinary sluice work can be partial rather than magic success",
            any(item.outcome.value == "partial" for item in adjust_results)
            and all(item.ok for item in adjust_results),
            "outcomes=" + ",".join(item.outcome.value for item in adjust_results),
        ),
        AffordanceTrialCheck(
            "production actions are causally parented by owned observations",
            bool(physical_events)
            and all(event.causal_parent_ids for event in physical_events),
            f"physical_events={len(physical_events)}; parented={sum(bool(e.causal_parent_ids) for e in physical_events)}",
        ),
        AffordanceTrialCheck(
            "hydrology process traces retain physical action provenance",
            bool(action_event_ids & traced_action_ids)
            and silt.event_id in traced_action_ids,
            f"action_events_in_ticks={len(action_event_ids & traced_action_ids)}",
        ),
        AffordanceTrialCheck(
            "two authoritative hydrology ticks—not action prose—make the water route viable",
            hydrology.state.aquatic_route_viable
            and bool(route_events)
            and final_adjust_event_id in route_events[-1].causal_parent_ids,
            f"route={hydrology.state.aquatic_route_viable}; transition_events={len(route_events)}",
        ),
        AffordanceTrialCheck(
            "a viable route neither creates a quest nor moves Nereid automatically",
            not forbidden_events
            and not any(event.event_type == "AQUATIC_PASSAGE_ATTEMPTED" for event in ledger.events),
            f"forbidden_events={len(forbidden_events)}; passage_attempts={sum(e.event_type == 'AQUATIC_PASSAGE_ATTEMPTED' for e in ledger.events)}",
        ),
        AffordanceTrialCheck(
            "physical consequence is not delivered until a new observation",
            pre_consequence_nereid_percepts == post_consequence_nereid_percepts
            and post_route_water.percept.ref
            == bridge.perceptions.for_subject("nereid_01")[-1].ref,
            f"before_observe={pre_consequence_nereid_percepts}; after_physics={post_consequence_nereid_percepts}; after_observe={len(bridge.perceptions.for_subject('nereid_01'))}",
        ),
        AffordanceTrialCheck(
            "post-change water percept still exposes cues rather than route truth",
            all(token not in post_route_payload for token in FORBIDDEN_SUBJECTIVE_KEYS)
            and "felt_current" in post_route_water.percept.cues,
            f"felt_current={post_route_water.percept.cues.get('felt_current')}",
        ),
        AffordanceTrialCheck(
            "Nereid's bounded silt action changes a later actor's real affordance",
            collaborative_delta > solo_delta,
            f"with_silt={collaborative_delta:.4f}; without_silt={solo_delta:.4f}",
        ),
        AffordanceTrialCheck(
            "identical local action histories remain deterministic",
            deterministic_collaboration,
            f"final_hash={collaborative[2].state.state_hash()[:16]}",
        ),
        AffordanceTrialCheck(
            "bank reinforcement through the bridge changes the hidden physical outcome",
            reinforced[6] is not None
            and reinforced[6].ok
            and reinforced_hydrology.state.burial_bank.exposure_fraction == 0.0
            and unreinforced_hydrology.state.burial_bank.exposure_fraction > 0.0,
            f"reinforced_exposure={reinforced_hydrology.state.burial_bank.exposure_fraction:.3f}; unreinforced_exposure={unreinforced_hydrology.state.burial_bank.exposure_fraction:.3f}",
        ),
        AffordanceTrialCheck(
            "bank workers can protect a hidden site without learning that it exists",
            all(token not in reinforced_percept_payload for token in ("burial", "tomb", "remains", "burial_shelf")),
            f"visible_cues={','.join(sorted(reinforced[5].percept.cues))}",
        ),
        AffordanceTrialCheck(
            "raw hydrology transitions remain guarded after P4",
            bool(raw_transitions)
            and all(
                any(barrier.kind == "raw_world_process_state" for barrier in event.perceptual_barriers)
                for event in raw_transitions
            ),
            f"guarded_transitions={len(raw_transitions)}",
        ),
        AffordanceTrialCheck(
            "action durations advance the same fixed-clock world process",
            len(hydrology.traces) == len(process_runtime.runs)
            and all(run.process_id == hydrology.process_id for run in process_runtime.runs),
            f"hydrology_ticks={len(hydrology.traces)}; process_runs={len(process_runtime.runs)}",
        ),
        AffordanceTrialCheck(
            "P4 never bypasses the objective Ledger for successful world-facing actions",
            bool(inspection_events)
            and all(
                trace.event_id is None or any(event.event_id == trace.event_id for event in ledger.events)
                for trace in bridge.action_traces
            ),
            f"actions={len(bridge.action_traces)}; ledger_events={len(ledger.events)}",
        ),
    )
    return AffordanceAcceptanceResult(
        checks=checks,
        world=world,
        ledger=ledger,
        hydrology=hydrology,
        process_runtime=process_runtime,
        bridge=bridge,
        reinforced_hydrology=reinforced_hydrology,
        unreinforced_hydrology=unreinforced_hydrology,
    )
