from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .affordances import PhysicalAffordanceBridge, create_silver_thread_affordance_bridge
from .engine import WorldEngine
from .ledger import EventLedger
from .materials import (
    ItemMaterialProfile,
    MaterialConstituent,
    create_default_material_catalog,
)
from .models import Action, ActionType, WorldState
from .processes.aqueous_echo import (
    AqueousEchoSenseBridge,
    AqueousEchoState,
    AqueousSilverEchoProcess,
    EchoSenseRequest,
    create_silver_thread_aqueous_echo,
    create_silver_thread_echo_sense_bridge,
)
from .processes.hydrology import HydrologyProcess, create_silver_thread_hydrology
from .processes.runtime import WorldProcessRuntime
from .projects import PersistentProjectStore, seed_silver_thread_projects
from .seed import create_world


@dataclass(frozen=True)
class AqueousEchoTrialCheck:
    name: str
    ok: bool
    detail: str


@dataclass
class AqueousEchoAcceptanceResult:
    checks: tuple[AqueousEchoTrialCheck, ...]
    world: WorldState
    ledger: EventLedger
    hydrology: HydrologyProcess
    echo: AqueousSilverEchoProcess
    bridge: PhysicalAffordanceBridge
    sensing: AqueousEchoSenseBridge
    projects: PersistentProjectStore
    runtime: WorldProcessRuntime
    diagnostics: dict[str, Any]

    @property
    def passed(self) -> bool:
        return all(check.ok for check in self.checks)


@dataclass
class _System:
    world: WorldState
    ledger: EventLedger
    engine: WorldEngine
    hydrology: HydrologyProcess
    echo: AqueousSilverEchoProcess
    bridge: PhysicalAffordanceBridge
    sensing: AqueousEchoSenseBridge
    runtime: WorldProcessRuntime


def _make_system(
    *,
    seed: int,
    open_gate: bool = False,
    materials=None,
) -> _System:
    world = create_world(seed=seed, synthetic_actors=0)
    ledger = EventLedger()
    engine = WorldEngine(world, ledger, seed=seed + 1, materials=materials)
    hydrology = create_silver_thread_hydrology(world, ledger)
    if open_gate:
        hydrology.apply_sluice_position(0.80)
        hydrology.clear_gate_debris(0.30)
    bridge = create_silver_thread_affordance_bridge(world, ledger, hydrology)
    echo = create_silver_thread_aqueous_echo(world, ledger, hydrology)
    sensing = create_silver_thread_echo_sense_bridge(world, ledger, echo, bridge)
    runtime = WorldProcessRuntime()
    runtime.register(hydrology)
    runtime.register(echo)
    runtime.attach(world)
    return _System(world, ledger, engine, hydrology, echo, bridge, sensing, runtime)


def _fish(system: _System, lake: str = "lake_mirror", tool: str = "silver_rod") -> int:
    if system.world.actors["arra"].location_id != "northwood":
        travel = system.engine.apply(
            Action("arra", ActionType.TRAVEL, target_id="northwood")
        )
        if not travel.ok:
            raise AssertionError(travel.message)
    result = system.engine.apply(
        Action("arra", ActionType.FISH, target_id=lake, params={"tool": tool})
    )
    if not result.ok or result.event_id is None:
        raise AssertionError(result.message)
    return result.event_id


def _contact_branch(
    *,
    seed: int,
    lake: str = "lake_mirror",
    tool: str = "silver_rod",
    contacts: int = 1,
    ticks: int = 1,
    open_gate: bool = False,
    materials=None,
) -> _System:
    system = _make_system(
        seed=seed,
        open_gate=open_gate,
        materials=materials,
    )
    if tool != "hands":
        system.world.actors["arra"].inventory.setdefault(tool, 1)
    for _ in range(contacts):
        _fish(system, lake, tool)
    system.world.advance(ticks * 360)
    return system


def _generic_contact_branch(seed: int) -> _System:
    system = _make_system(seed=seed)
    contact = system.engine.materials.medium_contact(
        item_id="silver_rod",
        medium_kind="water",
        medium_ref="lake_mirror",
        base_contact_units=1.0,
    )
    system.ledger.append(
        game_minute=system.world.game_minute,
        event_type="BASIN_RINSED",
        actor_ids=("arra",),
        target_ids=("lake_mirror",),
        location_id="northwood",
        tags=("ordinary_test_action", "material_contact"),
        data={"material_contacts": [contact.as_dict()]},
    )
    system.world.advance(360)
    return system


def _deterministic_signature(seed: int) -> tuple[Any, ...]:
    system = _make_system(seed=seed)
    _fish(system, "lake_whisper")
    system.world.advance(720)
    _fish(system, "lake_mirror")
    system.world.advance(1440)
    sensed = system.sensing.sense(
        EchoSenseRequest("nereid_01", "northwood_junction")
    )
    return (
        system.echo.state.state_hash(),
        tuple(item.as_dict() for item in system.echo.traces),
        tuple(item.as_dict() for item in system.ledger.events),
        sensed.percept.as_dict() if sensed.percept is not None else None,
    )


def run_aqueous_echo_acceptance(
    *,
    elapsed_days: int = 30,
    seed: int = 42,
) -> AqueousEchoAcceptanceResult:
    if elapsed_days <= 0:
        raise ValueError("elapsed_days must be positive")

    checks: list[AqueousEchoTrialCheck] = []

    focal = _make_system(seed=seed)
    projects = seed_silver_thread_projects(focal.world.game_minute)
    projects_before = tuple(item.as_dict() for item in projects.projects)
    contact_event_ids = tuple(_fish(focal) for _ in range(3))
    first_contact_event = focal.ledger.events[contact_event_ids[0] - 1]
    first_contact = first_contact_event.data["material_contacts"][0]

    checks.append(
        AqueousEchoTrialCheck(
            "fishing records a general material-medium contract rather than a story trigger",
            first_contact_event.event_type == "FISHED"
            and first_contact["schema"] == "material_medium_contact.v1"
            and first_contact["medium_kind"] == "water"
            and "nereid" not in str(first_contact).lower()
            and "quest" not in str(first_contact).lower(),
            f"event={first_contact_event.event_type}; schema={first_contact['schema']}",
        )
    )

    generic = _generic_contact_branch(seed + 10)
    generic_impulse = generic.echo.last_trace.node_impulses["lake_mirror"]
    rod_single = _contact_branch(seed=seed + 11)
    rod_impulse = rod_single.echo.last_trace.node_impulses["lake_mirror"]
    checks.append(
        AqueousEchoTrialCheck(
            "echo consumes the contact schema without inspecting the gameplay verb",
            generic_impulse > 0.0
            and generic.ledger.events[0].event_type == "BASIN_RINSED"
            and generic_impulse == rod_impulse,
            f"generic_event=BASIN_RINSED; impulse={generic_impulse:.6f}",
        )
    )

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
    alternate = _contact_branch(
        seed=seed + 12,
        tool="silver_probe",
        materials=catalog,
    )
    alternate_impulse = alternate.echo.last_trace.node_impulses["lake_mirror"]
    checks.append(
        AqueousEchoTrialCheck(
            "a different silver object obeys the same material law",
            alternate_impulse == rod_impulse,
            f"silver_probe={alternate_impulse:.6f}; silver_rod={rod_impulse:.6f}",
        )
    )

    hands = _contact_branch(seed=seed + 13, tool="hands")
    iron = _contact_branch(seed=seed + 14, tool="iron_rod")
    hands_impulse = sum(hands.echo.last_trace.node_impulses.values())
    iron_impulse = sum(iron.echo.last_trace.node_impulses.values())
    checks.append(
        AqueousEchoTrialCheck(
            "non-silver water contact remains physically ordinary",
            hands_impulse == 0.0 and iron_impulse == 0.0,
            f"hands={hands_impulse:.6f}; iron={iron_impulse:.6f}",
        )
    )

    focal.world.advance(360)
    first_echo_total = sum(focal.echo.state.node_amounts.values())
    first_echo_trace = focal.echo.last_trace
    checks.append(
        AqueousEchoTrialCheck(
            "repeated contact accumulates as physical impulse with no count threshold",
            first_echo_trace.node_impulses["lake_mirror"]
            == 3.0 * rod_impulse
            and first_echo_total > 0.0,
            (
                f"contacts={len(first_echo_trace.resonant_contact_refs)}; "
                f"impulse={first_echo_trace.node_impulses['lake_mirror']:.6f}"
            ),
        )
    )
    focal_sensed = focal.sensing.sense(
        EchoSenseRequest("nereid_01", "northwood_junction")
    )
    if not focal_sensed.ok:
        raise AssertionError("focal aqueous echo sensing unexpectedly failed")

    single = _contact_branch(seed=seed + 15)
    single_total = sum(single.echo.state.node_amounts.values())
    single.world.advance(12 * 360)
    decayed_total = sum(single.echo.state.node_amounts.values())
    checks.append(
        AqueousEchoTrialCheck(
            "the weak echo decays when material contact stops",
            0.0 < decayed_total < single_total,
            f"after_contact={single_total:.6f}; after_3d={decayed_total:.6f}",
        )
    )

    total_minutes = elapsed_days * 24 * 60
    if focal.world.game_minute < total_minutes:
        focal.world.advance(total_minutes - focal.world.game_minute)
    ordered = all(
        focal.runtime.runs[index].process_id == "silver_thread_hydrology"
        and focal.runtime.runs[index + 1].process_id == "silver_thread_water_echo"
        and focal.runtime.runs[index].game_minute
        == focal.runtime.runs[index + 1].game_minute
        for index in range(0, len(focal.runtime.runs), 2)
    )
    checks.append(
        AqueousEchoTrialCheck(
            "fixed clocks run Hydrology before Echo across a large world-time jump",
            len(focal.hydrology.traces) == elapsed_days * 4
            and len(focal.echo.traces) == elapsed_days * 4
            and ordered,
            (
                f"hydrology_ticks={len(focal.hydrology.traces)}; "
                f"echo_ticks={len(focal.echo.traces)}"
            ),
        )
    )

    chain_ok = all(
        earlier.output_state_hash == later.input_state_hash
        for earlier, later in zip(focal.echo.traces, focal.echo.traces[1:])
    )
    checks.append(
        AqueousEchoTrialCheck(
            "echo forensic hashes form a continuous state chain",
            chain_ok,
            f"traces={len(focal.echo.traces)}; final={focal.echo.state.state_hash()[:16]}",
        )
    )
    max_residual = max(abs(item.balance_residual) for item in focal.echo.traces)
    checks.append(
        AqueousEchoTrialCheck(
            "decay transport and attenuation are explicitly balanced",
            max_residual <= 1e-10,
            f"max_abs_residual={max_residual:.3e}",
        )
    )

    mirror = _contact_branch(seed=seed + 16, lake="lake_mirror")
    whisper = _contact_branch(seed=seed + 16, lake="lake_whisper")
    mirror_junction = mirror.echo.state.node_amounts["northwood_junction"]
    whisper_junction = whisper.echo.state.node_amounts["northwood_junction"]
    checks.append(
        AqueousEchoTrialCheck(
            "Mirror and Whisper differ through actual water state rather than a lake-name branch",
            mirror_junction > 0.0
            and whisper_junction > 0.0
            and abs(mirror_junction - whisper_junction) > 1e-9,
            f"mirror={mirror_junction:.6f}; whisper={whisper_junction:.6f}",
        )
    )

    disconnected = _make_system(seed=seed + 17)
    disconnected.hydrology.state.nodes["lake_mirror"].storage = 0.0
    disconnected.hydrology.state.nodes["northwood_junction"].storage = (
        disconnected.hydrology.state.nodes["northwood_junction"].storage_capacity
    )
    _fish(disconnected)
    disconnected.world.advance(360)
    mirror_flow = disconnected.hydrology.last_trace.edge_flows["mirror_to_junction"]
    disconnected_junction = disconnected.echo.state.node_amounts["northwood_junction"]
    checks.append(
        AqueousEchoTrialCheck(
            "zero-flow water edges do not teleport the echo",
            mirror_flow == 0.0 and disconnected_junction == 0.0,
            f"flow={mirror_flow:.6f}; junction_echo={disconnected_junction:.6f}",
        )
    )

    closed = _contact_branch(
        seed=seed + 18,
        contacts=5,
        ticks=12,
        open_gate=False,
    )
    opened = _contact_branch(
        seed=seed + 18,
        contacts=5,
        ticks=12,
        open_gate=True,
    )
    closed_deep = closed.echo.state.node_amounts["underpeak_deep_river"]
    opened_deep = opened.echo.state.node_amounts["underpeak_deep_river"]
    checks.append(
        AqueousEchoTrialCheck(
            "the baseline closed Gate keeps the deep-river echo below perception",
            closed.echo.state.band_states["underpeak_deep_river"] == "silent",
            f"deep_concentration={closed.echo.concentration('underpeak_deep_river'):.6f}",
        )
    )
    checks.append(
        AqueousEchoTrialCheck(
            "opening the Gate changes downstream echo under identical contacts",
            opened_deep > closed_deep * 4.0,
            f"closed={closed_deep:.6f}; open={opened_deep:.6f}",
        )
    )

    pre_percepts = len(rod_single.bridge.perceptions.all_percepts)
    checks.append(
        AqueousEchoTrialCheck(
            "objective echo evolution does not manufacture subjective knowledge",
            pre_percepts == 0,
            f"echo_ticks={len(rod_single.echo.traces)}; private_percepts={pre_percepts}",
        )
    )

    before_remote = (
        rod_single.world.game_minute,
        rod_single.echo.state.state_hash(),
        len(rod_single.ledger.events),
    )
    remote = rod_single.sensing.sense(
        EchoSenseRequest("nereid_01", "lake_mirror")
    )
    after_remote = (
        rod_single.world.game_minute,
        rod_single.echo.state.state_hash(),
        len(rod_single.ledger.events),
    )
    checks.append(
        AqueousEchoTrialCheck(
            "remote echo sensing is rejected before time state or Ledger mutation",
            not remote.ok and before_remote == after_remote,
            f"outcome={remote.outcome.value}; minute={rod_single.world.game_minute}",
        )
    )

    no_faculty = rod_single.sensing.sense(
        EchoSenseRequest("trade_house_01", "underpeak_gate_forebay")
    )
    checks.append(
        AqueousEchoTrialCheck(
            "local presence alone does not grant the required water faculty",
            not no_faculty.ok
            and no_faculty.duration_minutes == 0
            and before_remote == (
                rod_single.world.game_minute,
                rod_single.echo.state.state_hash(),
                len(rod_single.ledger.events),
            ),
            f"subject=trade_house_01; outcome={no_faculty.outcome.value}",
        )
    )

    sensed = rod_single.sensing.sense(
        EchoSenseRequest("nereid_01", "northwood_junction")
    )
    percept = sensed.percept
    checks.append(
        AqueousEchoTrialCheck(
            "a local water faculty creates one private imperfect percept",
            sensed.ok
            and percept is not None
            and percept.subject_id == "nereid_01"
            and len(rod_single.bridge.subject_view("nereid_01").percepts) == 1,
            f"percept={percept.ref if percept else 'none'}; owner=nereid_01",
        )
    )

    percept_payload = percept.as_dict() if percept is not None else {}
    forbidden_percept_tokens = (
        "silver_rod",
        "arra",
        "contact_units",
        "mass_fraction",
        "node_amounts",
        "state_hash",
        "impulse",
    )
    checks.append(
        AqueousEchoTrialCheck(
            "the private percept exposes qualitative cues without source or formula",
            percept is not None
            and set(percept.cues)
            == {
                "echo_presence",
                "movement_cue",
                "source_identity",
                "water_borne_pattern",
            }
            and not any(
                token in str(percept_payload).lower()
                for token in forbidden_percept_tokens
            ),
            f"cues={','.join(sorted(percept.cues)) if percept else 'none'}",
        )
    )

    sense_event = (
        rod_single.ledger.events[sensed.event_id - 1]
        if sensed.event_id is not None
        else None
    )
    checks.append(
        AqueousEchoTrialCheck(
            "the objective sensing event withholds its private payload",
            sense_event is not None
            and sense_event.data.get("percept_payload_withheld_from_ledger") is True
            and "echo_presence" not in sense_event.data,
            f"event={sense_event.event_id if sense_event else 'none'}",
        )
    )

    private_guard = False
    if percept is not None:
        try:
            rod_single.bridge.perceptions.get_for_subject(
                "trade_house_01", percept.ref
            )
        except PermissionError:
            private_guard = True
    checks.append(
        AqueousEchoTrialCheck(
            "one subject cannot read another subject's aqueous percept",
            private_guard,
            f"private_guard={private_guard}",
        )
    )

    raw_transitions = [
        event
        for event in rod_single.ledger.events
        if event.event_type == "AQUEOUS_ECHO_BAND_CROSSED"
    ]
    raw_guarded = all(
        any(barrier.kind == "raw_world_process_state" for barrier in event.perceptual_barriers)
        for event in raw_transitions
    )
    checks.append(
        AqueousEchoTrialCheck(
            "raw hidden-metaphysics transitions remain barred from divine omniscience",
            bool(raw_transitions) and raw_guarded,
            f"guarded_transitions={len(raw_transitions)}",
        )
    )

    projects_after = tuple(item.as_dict() for item in projects.projects)
    forbidden_story_tokens = ("INTEREST", "CONTACT", "REQUEST", "QUEST")
    forbidden_events = [
        event.event_type
        for event in focal.ledger.events
        if any(token in event.event_type for token in forbidden_story_tokens)
    ]
    checks.append(
        AqueousEchoTrialCheck(
            "silver-water physics creates no attention contact request quest or Project mutation",
            not forbidden_events and projects_before == projects_after,
            f"forbidden_events={len(forbidden_events)}; project_revisions_unchanged=True",
        )
    )

    schema_fields = set(AqueousEchoState.__dataclass_fields__)
    checks.append(
        AqueousEchoTrialCheck(
            "the echo state schema has no actor entity or narrative slot",
            schema_fields == {"node_amounts", "band_states"},
            f"fields={','.join(sorted(schema_fields))}",
        )
    )

    graph = rod_single.sensing.forensic_graph()
    graph_kinds = {edge["kind"] for edge in graph["edges"]}
    required_graph_kinds = {
        "event_contact_record",
        "material_contact_input",
        "water_transport_input",
        "local_sensing_state_input",
        "perception_record",
    }
    checks.append(
        AqueousEchoTrialCheck(
            "Creator forensic braid reaches contact water transport echo and private perception",
            required_graph_kinds.issubset(graph_kinds),
            f"nodes={len(graph['nodes'])}; edges={len(graph['edges'])}",
        )
    )

    first_signature = _deterministic_signature(seed + 19)
    second_signature = _deterministic_signature(seed + 19)
    checks.append(
        AqueousEchoTrialCheck(
            "identical material water and sensing histories are deterministic",
            first_signature == second_signature,
            f"final_hash={first_signature[0][:16]}",
        )
    )

    all_residuals = [
        *focal.echo.traces,
        *rod_single.echo.traces,
        *opened.echo.traces,
        *closed.echo.traces,
    ]
    checks.append(
        AqueousEchoTrialCheck(
            "P4-B runtimes and Ledger listeners stayed healthy",
            not focal.ledger.listener_errors
            and not rod_single.ledger.listener_errors
            and all(abs(item.balance_residual) <= 1e-10 for item in all_residuals),
            (
                f"listener_errors={len(focal.ledger.listener_errors) + len(rod_single.ledger.listener_errors)}; "
                f"checked_echo_ticks={len(all_residuals)}"
            ),
        )
    )

    diagnostics = {
        "generic_impulse": generic_impulse,
        "rod_impulse": rod_impulse,
        "alternate_impulse": alternate_impulse,
        "mirror_junction": mirror_junction,
        "whisper_junction": whisper_junction,
        "closed_deep": closed_deep,
        "opened_deep": opened_deep,
        "max_balance_residual": max_residual,
        "forensic_nodes": len(graph["nodes"]),
        "forensic_edges": len(graph["edges"]),
    }
    return AqueousEchoAcceptanceResult(
        checks=tuple(checks),
        world=focal.world,
        ledger=focal.ledger,
        hydrology=focal.hydrology,
        echo=focal.echo,
        bridge=focal.bridge,
        sensing=focal.sensing,
        projects=projects,
        runtime=focal.runtime,
        diagnostics=diagnostics,
    )
