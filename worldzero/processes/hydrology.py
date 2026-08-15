from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from ..ledger import EventLedger
from ..models import WorldState
from ..perception import PerceptualAspect, PerceptualBarrier


HYDROLOGY_TICK_MINUTES = 6 * 60
MASS_TOLERANCE = 1e-10


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def _round(value: float) -> float:
    return round(float(value), 12)


@dataclass
class WaterNodeState:
    node_id: str
    storage: float
    storage_capacity: float
    base_head: float
    external_inflow: float = 0.0
    water_tags: tuple[str, ...] = ()

    @property
    def level(self) -> float:
        return self.storage / self.storage_capacity

    @property
    def head(self) -> float:
        return self.base_head + self.level

    def as_dict(self) -> dict:
        return {
            "node_id": self.node_id,
            "storage": _round(self.storage),
            "storage_capacity": _round(self.storage_capacity),
            "level": _round(self.level),
            "base_head": _round(self.base_head),
            "head": _round(self.head),
            "external_inflow": _round(self.external_inflow),
            "water_tags": list(self.water_tags),
        }


@dataclass(frozen=True)
class WaterEdgeState:
    edge_id: str
    source_id: str
    target_id: str
    capacity: float
    head_scale: float

    def as_dict(self) -> dict:
        return {
            "edge_id": self.edge_id,
            "source_id": self.source_id,
            "target_id": self.target_id,
            "capacity": self.capacity,
            "head_scale": self.head_scale,
        }


@dataclass
class GateHydraulicState:
    object_id: str = "underpeak_river_gate"
    sluice_position: float = 0.0
    debris_load: float = 0.35
    structure_integrity: float = 0.82
    last_change_event_id: int | None = None

    @property
    def effective_opening(self) -> float:
        return _clamp(
            self.sluice_position * (1.0 - self.debris_load)
            + 0.03 * (1.0 - self.structure_integrity)
        )

    def as_dict(self) -> dict:
        return {
            "object_id": self.object_id,
            "sluice_position": _round(self.sluice_position),
            "debris_load": _round(self.debris_load),
            "structure_integrity": _round(self.structure_integrity),
            "effective_opening": _round(self.effective_opening),
            "last_change_event_id": self.last_change_event_id,
        }


class GalleryRouteState(str, Enum):
    BLOCKED = "blocked_by_rubble"
    PASSABLE = "passable"
    RISKY = "wet_risky"
    IMPASSABLE = "flooded_impassable"


@dataclass
class GalleryState:
    node_id: str = "underpeak_gallery_sump"
    rubble_obstruction: float = 0.70
    route_state: GalleryRouteState = GalleryRouteState.BLOCKED
    last_change_event_id: int | None = None

    def as_dict(self) -> dict:
        return {
            "node_id": self.node_id,
            "rubble_obstruction": _round(self.rubble_obstruction),
            "route_state": self.route_state.value,
            "last_change_event_id": self.last_change_event_id,
        }


@dataclass
class BurialBankState:
    object_id: str = "underpeak_burial_shelf"
    cover_depth_equiv: float = 0.55
    sediment_mobility: float = 1.0
    exposure_fraction: float = 0.0
    disturbance: float = 0.0
    remains_displaced: bool = False
    last_change_event_id: int | None = None

    def as_dict(self) -> dict:
        return {
            "object_id": self.object_id,
            "cover_depth_equiv": _round(self.cover_depth_equiv),
            "sediment_mobility": _round(self.sediment_mobility),
            "exposure_fraction": _round(self.exposure_fraction),
            "disturbance": _round(self.disturbance),
            "remains_displaced": self.remains_displaced,
            "last_change_event_id": self.last_change_event_id,
        }


@dataclass
class HydrologyState:
    nodes: dict[str, WaterNodeState]
    edges: tuple[WaterEdgeState, ...]
    gate: GateHydraulicState
    gallery: GalleryState
    burial_bank: BurialBankState
    aquatic_viable_streak: int = 0
    aquatic_route_viable: bool = False
    lake_band_states: dict[str, str] = field(default_factory=dict)

    def as_dict(self) -> dict:
        return {
            "nodes": {key: self.nodes[key].as_dict() for key in sorted(self.nodes)},
            "edges": [edge.as_dict() for edge in self.edges],
            "gate": self.gate.as_dict(),
            "gallery": self.gallery.as_dict(),
            "burial_bank": self.burial_bank.as_dict(),
            "aquatic_viable_streak": self.aquatic_viable_streak,
            "aquatic_route_viable": self.aquatic_route_viable,
            "lake_band_states": dict(sorted(self.lake_band_states.items())),
        }

    def state_hash(self) -> str:
        payload = json.dumps(
            self.as_dict(),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()

    def validate_invariants(self) -> None:
        if set(self.nodes) != {
            "lake_mirror",
            "lake_whisper",
            "northwood_junction",
            "underpeak_gate_forebay",
            "underpeak_gallery_sump",
            "underpeak_upper_reach",
            "underpeak_deep_river",
        }:
            raise AssertionError("Silver Thread hydrology must contain exactly seven focal nodes")
        for node in self.nodes.values():
            if not math.isfinite(node.storage):
                raise AssertionError(f"{node.node_id} storage is not finite")
            if node.storage < -MASS_TOLERANCE or node.storage > node.storage_capacity + MASS_TOLERANCE:
                raise AssertionError(f"{node.node_id} storage escaped physical capacity")
        for value, label in (
            (self.gate.sluice_position, "gate.sluice_position"),
            (self.gate.debris_load, "gate.debris_load"),
            (self.gate.structure_integrity, "gate.structure_integrity"),
            (self.gallery.rubble_obstruction, "gallery.rubble_obstruction"),
            (self.burial_bank.sediment_mobility, "burial.sediment_mobility"),
            (self.burial_bank.exposure_fraction, "burial.exposure_fraction"),
            (self.burial_bank.disturbance, "burial.disturbance"),
        ):
            if not 0.0 <= value <= 1.0:
                raise AssertionError(f"{label} escaped [0, 1]")
        if not 0.0 <= self.burial_bank.cover_depth_equiv <= 0.75:
            raise AssertionError("burial cover escaped [0, 0.75]")


@dataclass(frozen=True)
class HydrologyTickTrace:
    hydrology_tick_id: int
    game_minute: int
    input_state_hash: str
    external_source_totals: dict[str, float]
    edge_flows: dict[str, float]
    external_sink_totals: dict[str, float]
    spill_totals: dict[str, float]
    output_state_hash: str
    causal_action_event_ids: tuple[int, ...]
    emitted_event_ids: tuple[int, ...]
    mass_balance_residual: float

    @property
    def ref(self) -> str:
        return f"hydrology_tick:{self.hydrology_tick_id}"

    def as_dict(self) -> dict:
        return {
            "hydrology_tick_id": self.hydrology_tick_id,
            "ref": self.ref,
            "game_minute": self.game_minute,
            "input_state_hash": self.input_state_hash,
            "external_source_totals": self.external_source_totals,
            "edge_flows": self.edge_flows,
            "external_sink_totals": self.external_sink_totals,
            "spill_totals": self.spill_totals,
            "output_state_hash": self.output_state_hash,
            "causal_action_event_ids": list(self.causal_action_event_ids),
            "emitted_event_ids": list(self.emitted_event_ids),
            "mass_balance_residual": self.mass_balance_residual,
        }


class HydrologyProcess:
    """The authoritative seven-node Silver Thread water machine.

    This subsystem computes only physical state and objective threshold changes.
    It has no reference to quests, Projects, gods, or agent beliefs.
    """

    process_id = "silver_thread_hydrology"
    tick_interval_minutes = HYDROLOGY_TICK_MINUTES

    def __init__(self, world: WorldState, ledger: EventLedger, state: HydrologyState) -> None:
        self.world = world
        self.ledger = ledger
        self.state = state
        self._traces: list[HydrologyTickTrace] = []
        self._erosion_window_start_tick: int | None = None
        self.state.validate_invariants()

    @property
    def traces(self) -> tuple[HydrologyTickTrace, ...]:
        return tuple(self._traces)

    @property
    def last_trace(self) -> HydrologyTickTrace | None:
        return self._traces[-1] if self._traces else None

    def apply_sluice_position(
        self,
        position: float,
        *,
        causal_action_event_id: int | None = None,
    ) -> None:
        self.state.gate.sluice_position = _clamp(float(position))
        self.state.gate.last_change_event_id = self._clean_event_id(causal_action_event_id)

    def clear_gate_debris(
        self,
        amount: float,
        *,
        causal_action_event_id: int | None = None,
    ) -> None:
        if amount < 0.0:
            raise ValueError("debris clearing amount cannot be negative")
        self.state.gate.debris_load = _clamp(self.state.gate.debris_load - amount)
        self.state.gate.last_change_event_id = self._clean_event_id(causal_action_event_id)

    def damage_gate(
        self,
        amount: float,
        *,
        causal_action_event_id: int | None = None,
    ) -> None:
        if amount < 0.0:
            raise ValueError("gate damage amount cannot be negative")
        self.state.gate.structure_integrity = _clamp(self.state.gate.structure_integrity - amount)
        self.state.gate.last_change_event_id = self._clean_event_id(causal_action_event_id)

    def repair_gate(
        self,
        amount: float,
        *,
        causal_action_event_id: int | None = None,
    ) -> None:
        if amount < 0.0:
            raise ValueError("gate repair amount cannot be negative")
        self.state.gate.structure_integrity = _clamp(self.state.gate.structure_integrity + amount)
        self.state.gate.last_change_event_id = self._clean_event_id(causal_action_event_id)

    def clear_gallery_rubble(
        self,
        amount: float,
        *,
        causal_action_event_id: int | None = None,
    ) -> None:
        if amount < 0.0:
            raise ValueError("rubble clearing amount cannot be negative")
        self.state.gallery.rubble_obstruction = _clamp(
            self.state.gallery.rubble_obstruction - amount
        )
        self.state.gallery.last_change_event_id = self._clean_event_id(causal_action_event_id)

    def reinforce_bank(
        self,
        fractional_reduction: float,
        *,
        causal_action_event_id: int | None = None,
    ) -> None:
        if not 0.0 <= fractional_reduction <= 1.0:
            raise ValueError("bank reinforcement reduction must be in [0, 1]")
        self.state.burial_bank.sediment_mobility = _clamp(
            self.state.burial_bank.sediment_mobility * (1.0 - fractional_reduction)
        )
        self.state.burial_bank.last_change_event_id = self._clean_event_id(
            causal_action_event_id
        )

    @staticmethod
    def _clean_event_id(event_id: int | None) -> int | None:
        if event_id is not None and event_id <= 0:
            raise ValueError("causal action event id must be positive")
        return event_id

    def tick(self, game_minute: int) -> None:
        if self._traces and game_minute <= self._traces[-1].game_minute:
            raise ValueError("hydrology ticks must move forward in time")
        tick_id = len(self._traces) + 1
        input_hash = self.state.state_hash()
        start_storage = {key: node.storage for key, node in self.state.nodes.items()}
        start_total = sum(start_storage.values())
        heads = {key: node.head for key, node in self.state.nodes.items()}
        levels = {key: node.level for key, node in self.state.nodes.items()}
        sources = {key: node.external_inflow for key, node in self.state.nodes.items()}

        requested: dict[str, float] = {}
        for edge in self.state.edges:
            delta = heads[edge.source_id] - heads[edge.target_id]
            requested[edge.edge_id] = edge.capacity * _clamp(delta / edge.head_scale)

        delta_gate_head = max(
            0.0,
            heads["underpeak_gate_forebay"] - heads["underpeak_upper_reach"],
        )
        effective_opening = self.state.gate.effective_opening
        q_gate_requested = min(
            0.180,
            0.140
            * effective_opening
            * math.sqrt(delta_gate_head / 0.50)
            if delta_gate_head > 0.0
            else 0.0,
        )
        requested["gate_discharge"] = q_gate_requested
        requested["forebay_to_gallery_backwater"] = min(
            0.055,
            0.018
            * (1.0 - self.state.gate.structure_integrity)
            * _clamp(delta_gate_head / 0.50)
            + 0.075 * max(0.0, levels["underpeak_gate_forebay"] - 0.80),
        )
        requested["gallery_drain_to_upper"] = (
            0.015 + 0.025 * (1.0 - self.state.gallery.rubble_obstruction)
        ) * _clamp((levels["underpeak_gallery_sump"] - 0.05) / 0.40)

        boundary_requested = {
            "lake_mirror": 0.008 * levels["lake_mirror"],
            "lake_whisper": 0.007 * levels["lake_whisper"],
            "northwood_junction": 0.042
            * _clamp((levels["northwood_junction"] - 0.52) / 0.26),
            "underpeak_deep_river": 0.090
            * _clamp(levels["underpeak_deep_river"] / 0.65),
        }

        flow: dict[str, float] = {}
        sinks: dict[str, float] = {key: 0.0 for key in self.state.nodes}

        self._allocate_source(
            "lake_mirror",
            {
                "mirror_to_junction": requested["mirror_to_junction"],
                "boundary": boundary_requested["lake_mirror"],
            },
            start_storage,
            sources,
            flow,
            sinks,
        )
        self._allocate_source(
            "lake_whisper",
            {
                "whisper_to_junction": requested["whisper_to_junction"],
                "boundary": boundary_requested["lake_whisper"],
            },
            start_storage,
            sources,
            flow,
            sinks,
        )
        self._allocate_source(
            "northwood_junction",
            {
                "junction_to_forebay": requested["junction_to_forebay"],
                "boundary": boundary_requested["northwood_junction"],
            },
            start_storage,
            sources,
            flow,
            sinks,
        )
        self._allocate_source(
            "underpeak_gate_forebay",
            {
                "gate_discharge": requested["gate_discharge"],
                "forebay_to_gallery_backwater": requested["forebay_to_gallery_backwater"],
            },
            start_storage,
            sources,
            flow,
            sinks,
        )

        q_gate = flow.get("gate_discharge", 0.0)
        requested["upper_to_gallery_inundation"] = min(
            0.050,
            4.0 * max(0.0, q_gate - 0.038),
        )
        self._allocate_source(
            "underpeak_upper_reach",
            {
                "upper_to_deep": requested["upper_to_deep"],
                "upper_to_gallery_inundation": requested["upper_to_gallery_inundation"],
            },
            start_storage,
            sources,
            flow,
            sinks,
        )
        self._allocate_source(
            "underpeak_gallery_sump",
            {"gallery_drain_to_upper": requested["gallery_drain_to_upper"]},
            start_storage,
            sources,
            flow,
            sinks,
        )
        self._allocate_source(
            "underpeak_deep_river",
            {"boundary": boundary_requested["underpeak_deep_river"]},
            start_storage,
            sources,
            flow,
            sinks,
        )

        internal_routes = {
            edge.edge_id: (edge.source_id, edge.target_id) for edge in self.state.edges
        }
        internal_routes.update(
            {
                "gate_discharge": ("underpeak_gate_forebay", "underpeak_upper_reach"),
                "forebay_to_gallery_backwater": (
                    "underpeak_gate_forebay",
                    "underpeak_gallery_sump",
                ),
                "upper_to_gallery_inundation": (
                    "underpeak_upper_reach",
                    "underpeak_gallery_sump",
                ),
                "gallery_drain_to_upper": (
                    "underpeak_gallery_sump",
                    "underpeak_upper_reach",
                ),
            }
        )
        incoming = {key: 0.0 for key in self.state.nodes}
        outgoing = {key: 0.0 for key in self.state.nodes}
        for edge_id, (source_id, target_id) in internal_routes.items():
            amount = flow.get(edge_id, 0.0)
            outgoing[source_id] += amount
            incoming[target_id] += amount

        spills: dict[str, float] = {}
        for node_id, node in self.state.nodes.items():
            raw = (
                start_storage[node_id]
                + sources[node_id]
                + incoming[node_id]
                - outgoing[node_id]
                - sinks[node_id]
            )
            if raw < -MASS_TOLERANCE:
                raise AssertionError(f"negative raw storage at {node_id}: {raw}")
            spill = max(0.0, raw - node.storage_capacity)
            spills[node_id] = spill
            node.storage = _clamp(raw, 0.0, node.storage_capacity)

        q_upper_total = q_gate + sources["underpeak_upper_reach"]
        previous_exposure = self.state.burial_bank.exposure_fraction
        previous_displaced = self.state.burial_bank.remains_displaced
        erosion_load = max(0.0, (q_upper_total - 0.070) / 0.010)
        cover_loss = (
            0.004
            * (erosion_load**1.5)
            * self.state.burial_bank.sediment_mobility
        )
        deposition = 0.00025 * max(0.0, (0.050 - q_upper_total) / 0.010)
        self.state.burial_bank.cover_depth_equiv = _clamp(
            self.state.burial_bank.cover_depth_equiv - cover_loss + deposition,
            0.0,
            0.75,
        )
        self.state.burial_bank.exposure_fraction = _clamp(
            (0.12 - self.state.burial_bank.cover_depth_equiv) / 0.12
        )
        if cover_loss > 0.0:
            if self._erosion_window_start_tick is None:
                self._erosion_window_start_tick = tick_id
        else:
            self._erosion_window_start_tick = None

        if self.state.burial_bank.exposure_fraction > 0.0 and q_upper_total > 0.095:
            disturbance_gain = (
                0.025
                * ((q_upper_total - 0.095) / 0.025)
                * self.state.burial_bank.exposure_fraction
            )
            self.state.burial_bank.disturbance = _clamp(
                self.state.burial_bank.disturbance + disturbance_gain
            )
        if self.state.burial_bank.disturbance >= 1.0:
            self.state.burial_bank.remains_displaced = True

        path_connected = (
            flow.get("junction_to_forebay", 0.0) > 1e-9
            and q_gate > 1e-9
            and flow.get("upper_to_deep", 0.0) > 1e-9
        )
        aquatic_condition = (
            effective_opening >= 0.28
            and q_gate >= 0.045
            and path_connected
        )
        previous_aquatic = self.state.aquatic_route_viable
        if aquatic_condition:
            self.state.aquatic_viable_streak += 1
        else:
            self.state.aquatic_viable_streak = 0
        self.state.aquatic_route_viable = self.state.aquatic_viable_streak >= 2

        previous_gallery = self.state.gallery.route_state
        self.state.gallery.route_state = self._gallery_route_state(
            self.state.gallery.rubble_obstruction,
            self.state.nodes["underpeak_gallery_sump"].level,
        )
        self.world.regions["underpeak"].accessible = self.state.gallery.route_state in {
            GalleryRouteState.PASSABLE,
            GalleryRouteState.RISKY,
        }

        previous_lake_bands = dict(self.state.lake_band_states)
        self.state.lake_band_states = {
            "lake_mirror": self._lake_band("lake_mirror"),
            "lake_whisper": self._lake_band("lake_whisper"),
        }

        event_ids: list[int] = []
        causal_action_event_ids = self._active_causal_event_ids()
        if not previous_aquatic and self.state.aquatic_route_viable:
            event_ids.append(
                self._objective_event(
                    game_minute,
                    "AQUATIC_ROUTE_BECAME_VIABLE",
                    target_ids=("underpeak_river_gate",),
                    data={
                        "hydrology_tick_id": tick_id,
                        "stable_ticks": self.state.aquatic_viable_streak,
                    },
                    causal_parent_ids=causal_action_event_ids,
                )
            )
        elif previous_aquatic and not self.state.aquatic_route_viable:
            event_ids.append(
                self._objective_event(
                    game_minute,
                    "AQUATIC_ROUTE_BECAME_NONVIABLE",
                    target_ids=("underpeak_river_gate",),
                    data={"hydrology_tick_id": tick_id},
                    causal_parent_ids=causal_action_event_ids,
                )
            )

        was_gallery_accessible = previous_gallery in {
            GalleryRouteState.PASSABLE,
            GalleryRouteState.RISKY,
        }
        gallery_accessible = self.state.gallery.route_state in {
            GalleryRouteState.PASSABLE,
            GalleryRouteState.RISKY,
        }
        if not was_gallery_accessible and gallery_accessible:
            event_ids.append(
                self._objective_event(
                    game_minute,
                    "GALLERY_ROUTE_BECAME_PASSABLE",
                    target_ids=("underpeak_gallery_sump",),
                    data={
                        "hydrology_tick_id": tick_id,
                        "route_state": self.state.gallery.route_state.value,
                    },
                    causal_parent_ids=causal_action_event_ids,
                )
            )
        elif was_gallery_accessible and not gallery_accessible:
            event_ids.append(
                self._objective_event(
                    game_minute,
                    "GALLERY_ROUTE_BECAME_IMPASSABLE",
                    target_ids=("underpeak_gallery_sump",),
                    data={
                        "hydrology_tick_id": tick_id,
                        "route_state": self.state.gallery.route_state.value,
                    },
                    causal_parent_ids=causal_action_event_ids,
                )
            )

        for lake_id in ("lake_mirror", "lake_whisper"):
            before = previous_lake_bands.get(lake_id, "normal")
            after = self.state.lake_band_states[lake_id]
            if before != after:
                event_ids.append(
                    self._objective_event(
                        game_minute,
                        "LAKE_LEVEL_BAND_CROSSED",
                        target_ids=(lake_id,),
                        location_id="northwood",
                        data={
                            "hydrology_tick_id": tick_id,
                            "from_band": before,
                            "to_band": after,
                        },
                        causal_parent_ids=causal_action_event_ids,
                    )
                )

        if previous_exposure <= 0.0 < self.state.burial_bank.exposure_fraction:
            burial_object = self.world.objects.get("underpeak_burial_shelf")
            if burial_object is not None:
                burial_object.condition = "partially_exposed"
            event_ids.append(
                self._objective_event(
                    game_minute,
                    "BURIAL_COVER_BECAME_EXPOSED",
                    target_ids=("underpeak_burial_shelf",),
                    data={
                        "hydrology_tick_id": tick_id,
                        "process_window": {
                            "first_tick_id": self._erosion_window_start_tick or tick_id,
                            "last_tick_id": tick_id,
                        },
                    },
                    causal_parent_ids=causal_action_event_ids,
                )
            )
        if not previous_displaced and self.state.burial_bank.remains_displaced:
            burial_object = self.world.objects.get("underpeak_burial_shelf")
            if burial_object is not None:
                burial_object.condition = "disturbed"
            event_ids.append(
                self._objective_event(
                    game_minute,
                    "REMAINS_DISPLACED",
                    target_ids=("underpeak_burial_shelf",),
                    data={"hydrology_tick_id": tick_id},
                    causal_parent_ids=causal_action_event_ids,
                )
            )

        self.state.validate_invariants()
        final_total = sum(node.storage for node in self.state.nodes.values())
        source_total = sum(sources.values())
        sink_total = sum(sinks.values())
        spill_total = sum(spills.values())
        residual = final_total - (start_total + source_total - sink_total - spill_total)
        if abs(residual) > MASS_TOLERANCE:
            raise AssertionError(f"hydrology mass balance residual {residual} exceeds tolerance")

        output_hash = self.state.state_hash()
        self._traces.append(
            HydrologyTickTrace(
                hydrology_tick_id=tick_id,
                game_minute=game_minute,
                input_state_hash=input_hash,
                external_source_totals={key: _round(value) for key, value in sorted(sources.items())},
                edge_flows={key: _round(value) for key, value in sorted(flow.items())},
                external_sink_totals={key: _round(value) for key, value in sorted(sinks.items())},
                spill_totals={key: _round(value) for key, value in sorted(spills.items())},
                output_state_hash=output_hash,
                causal_action_event_ids=causal_action_event_ids,
                emitted_event_ids=tuple(event_ids),
                mass_balance_residual=_round(residual),
            )
        )

    @staticmethod
    def _allocate_source(
        source_id: str,
        demands: dict[str, float],
        start_storage: dict[str, float],
        sources: dict[str, float],
        flow: dict[str, float],
        sinks: dict[str, float],
    ) -> None:
        positive = {key: max(0.0, value) for key, value in demands.items()}
        requested_total = sum(positive.values())
        available = start_storage[source_id] + sources[source_id]
        scale = 1.0 if requested_total <= available or requested_total == 0.0 else available / requested_total
        for key, value in positive.items():
            actual = value * scale
            if key == "boundary":
                sinks[source_id] += actual
            else:
                flow[key] = actual

    def _lake_band(self, lake_id: str) -> str:
        level = self.state.nodes[lake_id].level
        low, high = (0.48, 0.80) if lake_id == "lake_mirror" else (0.52, 0.82)
        if level < low:
            return "low"
        if level > high:
            return "high"
        return "normal"

    @staticmethod
    def _gallery_route_state(rubble_obstruction: float, level: float) -> GalleryRouteState:
        if rubble_obstruction > 0.35:
            return GalleryRouteState.BLOCKED
        if level < 0.18:
            return GalleryRouteState.PASSABLE
        if level < 0.45:
            return GalleryRouteState.RISKY
        return GalleryRouteState.IMPASSABLE

    def _active_causal_event_ids(self) -> tuple[int, ...]:
        ids = (
            self.state.gate.last_change_event_id,
            self.state.gallery.last_change_event_id,
            self.state.burial_bank.last_change_event_id,
        )
        return tuple(sorted({event_id for event_id in ids if event_id is not None}))

    def _objective_event(
        self,
        game_minute: int,
        event_type: str,
        *,
        target_ids: tuple[str, ...],
        data: dict,
        causal_parent_ids: tuple[int, ...] = (),
        location_id: str = "underpeak",
    ) -> int:
        event = self.ledger.append(
            game_minute=game_minute,
            event_type=event_type,
            actor_ids=(),
            target_ids=target_ids,
            location_id=location_id,
            tags=("world_process", "hydrology", "objective_transition"),
            witness_ids=(),
            publicity=0.0,
            secrecy=1.0,
            data=data,
            causal_parent_ids=causal_parent_ids,
            perceptual_barriers=(
                PerceptualBarrier(
                    kind="raw_world_process_state",
                    strength=1.0,
                    aspects=(
                        PerceptualAspect.EVENT,
                        PerceptualAspect.IDENTITY,
                        PerceptualAspect.CAUSAL_LINK,
                    ),
                ),
            ),
        )
        return event.event_id

    def export_trace_jsonl(self, path: str | Path) -> None:
        destination = Path(path)
        with destination.open("w", encoding="utf-8") as handle:
            for trace in self._traces:
                handle.write(json.dumps(trace.as_dict(), ensure_ascii=False, sort_keys=True) + "\n")

    def export_state_json(self, path: str | Path) -> None:
        Path(path).write_text(
            json.dumps(self.state.as_dict(), ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )


def create_silver_thread_hydrology(world: WorldState, ledger: EventLedger) -> HydrologyProcess:
    required_objects = {"lake_mirror", "lake_whisper", "underpeak_river_gate", "underpeak_burial_shelf"}
    missing_objects = required_objects - set(world.objects)
    if missing_objects:
        raise ValueError(
            "Silver Thread hydrology requires world objects: " + ", ".join(sorted(missing_objects))
        )
    if "underpeak" not in world.regions:
        raise ValueError("Silver Thread hydrology requires the Underpeak region")

    nodes = {
        "lake_mirror": WaterNodeState(
            "lake_mirror", 0.78, 1.20, 3.00, 0.034, ("fresh", "surface", "silver_thread")
        ),
        "lake_whisper": WaterNodeState(
            "lake_whisper", 0.68, 1.00, 2.90, 0.030, ("fresh", "surface", "silver_thread")
        ),
        "northwood_junction": WaterNodeState(
            "northwood_junction", 0.40, 0.55, 2.55, 0.0, ("fresh", "junction")
        ),
        "underpeak_gate_forebay": WaterNodeState(
            "underpeak_gate_forebay", 0.38, 0.45, 2.25, 0.0, ("fresh", "waterworks")
        ),
        "underpeak_gallery_sump": WaterNodeState(
            "underpeak_gallery_sump", 0.015, 0.30, 2.05, 0.0, ("fresh", "gallery")
        ),
        "underpeak_upper_reach": WaterNodeState(
            "underpeak_upper_reach", 0.33, 0.60, 1.85, 0.030, ("fresh", "underground")
        ),
        "underpeak_deep_river": WaterNodeState(
            "underpeak_deep_river", 0.53, 0.85, 1.45, 0.020, ("fresh", "underground", "native_nereid")
        ),
    }
    edges = (
        WaterEdgeState("mirror_to_junction", "lake_mirror", "northwood_junction", 0.065, 0.75),
        WaterEdgeState("whisper_to_junction", "lake_whisper", "northwood_junction", 0.060, 0.75),
        WaterEdgeState(
            "junction_to_forebay", "northwood_junction", "underpeak_gate_forebay", 0.115, 0.65
        ),
        WaterEdgeState(
            "upper_to_deep", "underpeak_upper_reach", "underpeak_deep_river", 0.140, 0.70
        ),
    )
    state = HydrologyState(
        nodes=nodes,
        edges=edges,
        gate=GateHydraulicState(),
        gallery=GalleryState(),
        burial_bank=BurialBankState(),
        lake_band_states={"lake_mirror": "normal", "lake_whisper": "normal"},
    )
    return HydrologyProcess(world, ledger, state)
