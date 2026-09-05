from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable

from ..ledger import EventLedger, WorldEvent
from ..materials import MATERIAL_CONTACT_SCHEMA
from ..models import WorldState
from ..perception import PerceptualAspect, PerceptualBarrier
from .hydrology import HYDROLOGY_TICK_MINUTES, HydrologyProcess

if TYPE_CHECKING:
    from ..affordances import (
        LocalPerceptionStore,
        PhysicalAffordanceBridge,
        SubjectivePercept,
    )


AQUEOUS_ECHO_TICK_MINUTES = HYDROLOGY_TICK_MINUTES
ECHO_DECAY_FACTOR = 0.82
SILVER_RESPONSE_PER_CONTACT_UNIT = 0.052
MIN_CONNECTED_FLOW = 0.003
TRANSPORT_MOBILITY = 3.0
MAX_EXPORT_FRACTION = 0.58
TRANSMISSION_RETENTION = 0.90
ECHO_BALANCE_TOLERANCE = 1e-10
ECHO_SENSE_DURATION_MINUTES = 30


def _round(value: float) -> float:
    return round(float(value), 12)


def _clean(value: str, label: str) -> str:
    cleaned = " ".join(str(value).split())
    if not cleaned:
        raise ValueError(f"{label} cannot be empty")
    return cleaned


@dataclass
class AqueousEchoState:
    """Objective hidden-metaphysics field carried by focal water nodes."""

    node_amounts: dict[str, float]
    band_states: dict[str, str] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "node_amounts": {
                key: _round(self.node_amounts[key]) for key in sorted(self.node_amounts)
            },
            "band_states": dict(sorted(self.band_states.items())),
        }

    def state_hash(self) -> str:
        encoded = json.dumps(
            self.as_dict(),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    def validate_invariants(self, expected_nodes: set[str]) -> None:
        if set(self.node_amounts) != expected_nodes:
            raise AssertionError("aqueous echo nodes must match authoritative hydrology nodes")
        if set(self.band_states) != expected_nodes:
            raise AssertionError("aqueous echo bands must match authoritative hydrology nodes")
        for node_id, amount in self.node_amounts.items():
            if not math.isfinite(amount) or amount < -ECHO_BALANCE_TOLERANCE:
                raise AssertionError(f"aqueous echo at {node_id} is not finite and non-negative")
        valid_bands = {"silent", "faint", "clear", "strong"}
        if any(value not in valid_bands for value in self.band_states.values()):
            raise AssertionError("aqueous echo band escaped the fixed qualitative vocabulary")


@dataclass(frozen=True)
class AqueousMaterialContactInput:
    event_id: int
    contact_index: int
    game_minute: int
    node_id: str
    contact_item_id: str
    contact_units: float
    silver_fraction: float

    @property
    def ref(self) -> str:
        return f"world_event:{self.event_id}#material_contact:{self.contact_index}"

    @property
    def impulse(self) -> float:
        return self.contact_units * self.silver_fraction * SILVER_RESPONSE_PER_CONTACT_UNIT

    def as_dict(self) -> dict[str, Any]:
        return {
            "ref": self.ref,
            "event_id": self.event_id,
            "contact_index": self.contact_index,
            "game_minute": self.game_minute,
            "node_id": self.node_id,
            "contact_item_id": self.contact_item_id,
            "contact_units": _round(self.contact_units),
            "silver_fraction": _round(self.silver_fraction),
            "impulse": _round(self.impulse),
        }


@dataclass(frozen=True)
class AqueousEchoTickTrace:
    echo_tick_id: int
    game_minute: int
    input_state_hash: str
    hydrology_tick_ref: str
    material_contact_refs: tuple[str, ...]
    resonant_contact_refs: tuple[str, ...]
    contact_event_ids: tuple[int, ...]
    node_impulses: dict[str, float]
    edge_exports: dict[str, float]
    edge_deliveries: dict[str, float]
    boundary_losses: dict[str, float]
    decay_loss: float
    transmission_loss: float
    balance_residual: float
    emitted_event_ids: tuple[int, ...]
    output_state_hash: str

    @property
    def ref(self) -> str:
        return f"aqueous_echo_tick:{self.echo_tick_id}"

    def as_dict(self) -> dict[str, Any]:
        return {
            "echo_tick_id": self.echo_tick_id,
            "ref": self.ref,
            "game_minute": self.game_minute,
            "input_state_hash": self.input_state_hash,
            "hydrology_tick_ref": self.hydrology_tick_ref,
            "material_contact_refs": list(self.material_contact_refs),
            "resonant_contact_refs": list(self.resonant_contact_refs),
            "contact_event_ids": list(self.contact_event_ids),
            "node_impulses": self.node_impulses,
            "edge_exports": self.edge_exports,
            "edge_deliveries": self.edge_deliveries,
            "boundary_losses": self.boundary_losses,
            "decay_loss": self.decay_loss,
            "transmission_loss": self.transmission_loss,
            "balance_residual": self.balance_residual,
            "emitted_event_ids": list(self.emitted_event_ids),
            "output_state_hash": self.output_state_hash,
        }


@dataclass(frozen=True)
class _ParsedContact:
    ref: str
    event_id: int
    node_id: str
    contact_item_id: str
    contact_units: float
    silver_fraction: float
    resonant: AqueousMaterialContactInput | None


class AqueousSilverEchoProcess:
    """Deterministic silver/water hidden-metaphysics process.

    The process reads the generic ``material_medium_contact.v1`` event schema.
    It never reads gameplay event types, actor identities, Projects, attention,
    quests or entity IDs.  Silver creates a weak impulse; decay and transport
    through sufficiently connected authoritative water determine the rest.
    """

    # The runtime orders simultaneous process IDs lexically. ``water`` keeps
    # this process after ``silver_thread_hydrology`` at each six-hour boundary.
    process_id = "silver_thread_water_echo"
    tick_interval_minutes = AQUEOUS_ECHO_TICK_MINUTES

    def __init__(
        self,
        world: WorldState,
        ledger: EventLedger,
        hydrology: HydrologyProcess,
        state: AqueousEchoState,
    ) -> None:
        if hydrology.world is not world or hydrology.ledger is not ledger:
            raise ValueError("aqueous echo must share world and ledger with hydrology")
        self.world = world
        self.ledger = ledger
        self.hydrology = hydrology
        self.state = state
        self._traces: list[AqueousEchoTickTrace] = []
        self._last_scanned_event_id = 0
        self._node_source_event_ids: dict[str, set[int]] = {
            node_id: set() for node_id in self.state.node_amounts
        }
        self.state.validate_invariants(set(self.hydrology.state.nodes))

    @property
    def traces(self) -> tuple[AqueousEchoTickTrace, ...]:
        return tuple(self._traces)

    @property
    def last_trace(self) -> AqueousEchoTickTrace | None:
        return self._traces[-1] if self._traces else None

    @property
    def active_contact_event_ids(self) -> tuple[int, ...]:
        return tuple(
            sorted(
                set().union(*self._node_source_event_ids.values())
                if self._node_source_event_ids
                else set()
            )
        )

    def source_contact_event_ids(self, node_id: str) -> tuple[int, ...]:
        if node_id not in self._node_source_event_ids:
            raise ValueError(f"unknown aqueous echo node: {node_id}")
        return tuple(sorted(self._node_source_event_ids[node_id]))

    def concentration(self, node_id: str) -> float:
        if node_id not in self.state.node_amounts:
            raise ValueError(f"unknown aqueous echo node: {node_id}")
        storage = max(self.hydrology.state.nodes[node_id].storage, 0.05)
        return self.state.node_amounts[node_id] / storage

    def tick(self, game_minute: int) -> None:
        if self._traces and game_minute <= self._traces[-1].game_minute:
            raise ValueError("aqueous echo ticks must move forward in time")
        hydrology_tick = self.hydrology.last_trace
        if hydrology_tick is None or hydrology_tick.game_minute != game_minute:
            raise RuntimeError(
                "aqueous echo requires the same-boundary authoritative hydrology tick first"
            )

        tick_id = len(self._traces) + 1
        input_hash = self.state.state_hash()
        start = dict(self.state.node_amounts)
        all_contacts, resonant_contacts = self._scan_material_contacts(game_minute)
        impulses = {node_id: 0.0 for node_id in self.state.node_amounts}
        provenance = {
            node_id: set(event_ids)
            for node_id, event_ids in self._node_source_event_ids.items()
        }
        for contact in resonant_contacts:
            impulses[contact.node_id] += contact.impulse
            provenance[contact.node_id].add(contact.event_id)

        decayed = {
            node_id: max(0.0, amount) * ECHO_DECAY_FACTOR
            for node_id, amount in start.items()
        }
        decay_loss = sum(start.values()) - sum(decayed.values())
        transported = {
            node_id: decayed[node_id] + impulses[node_id]
            for node_id in decayed
        }
        pre_transport_total = sum(transported.values())

        routes = self._transport_routes(hydrology_tick.edge_flows)
        edge_exports: dict[str, float] = {}
        edge_deliveries: dict[str, float] = {}
        boundary_losses: dict[str, float] = {}
        transmission_loss = 0.0
        delta = {node_id: 0.0 for node_id in transported}
        source_provenance = {
            node_id: set(event_ids) for node_id, event_ids in provenance.items()
        }

        outgoing: dict[str, list[tuple[str, str | None, float, bool]]] = {
            node_id: [] for node_id in transported
        }
        for route_id, source_id, target_id, flow in routes:
            if flow >= MIN_CONNECTED_FLOW:
                outgoing[source_id].append((route_id, target_id, flow, False))
        for node_id, amount in hydrology_tick.external_sink_totals.items():
            if amount >= MIN_CONNECTED_FLOW:
                outgoing[node_id].append((f"boundary:{node_id}", None, amount, True))
        for node_id, amount in hydrology_tick.spill_totals.items():
            if amount >= MIN_CONNECTED_FLOW:
                outgoing[node_id].append((f"spill:{node_id}", None, amount, True))

        for source_id, paths in outgoing.items():
            if not paths or transported[source_id] <= 0.0:
                continue
            storage = max(self.hydrology.state.nodes[source_id].storage, 0.05)
            weights = [flow / storage for _, _, flow, _ in paths]
            weight_total = sum(weights)
            export_fraction = min(MAX_EXPORT_FRACTION, TRANSPORT_MOBILITY * weight_total)
            export_total = transported[source_id] * export_fraction
            for (route_id, target_id, _, is_boundary), weight in zip(paths, weights):
                exported = export_total * weight / weight_total
                delta[source_id] -= exported
                edge_exports[route_id] = edge_exports.get(route_id, 0.0) + exported
                if is_boundary or target_id is None:
                    boundary_losses[route_id] = boundary_losses.get(route_id, 0.0) + exported
                    continue
                delivered = exported * TRANSMISSION_RETENTION
                lost = exported - delivered
                delta[target_id] += delivered
                if delivered > 0.0:
                    provenance[target_id].update(source_provenance[source_id])
                edge_deliveries[route_id] = edge_deliveries.get(route_id, 0.0) + delivered
                transmission_loss += lost

        for node_id in transported:
            transported[node_id] = max(0.0, transported[node_id] + delta[node_id])

        final_total = sum(transported.values())
        expected_total = (
            pre_transport_total
            - sum(boundary_losses.values())
            - transmission_loss
        )
        residual = final_total - expected_total
        if abs(residual) > ECHO_BALANCE_TOLERANCE:
            raise AssertionError(
                f"aqueous echo balance residual {residual} exceeds tolerance"
            )

        previous_bands = dict(self.state.band_states)
        self.state.node_amounts = transported
        self._node_source_event_ids = provenance
        self.state.band_states = {
            node_id: self._band_for_concentration(self.concentration(node_id))
            for node_id in sorted(self.state.node_amounts)
        }
        self.state.validate_invariants(set(self.hydrology.state.nodes))

        emitted_event_ids: list[int] = []
        for node_id in sorted(self.state.band_states):
            before = previous_bands[node_id]
            after = self.state.band_states[node_id]
            if before == after:
                continue
            event = self.ledger.append(
                game_minute=game_minute,
                event_type="AQUEOUS_ECHO_BAND_CROSSED",
                actor_ids=(),
                target_ids=(node_id,),
                location_id=self._site_region(node_id),
                tags=(
                    "world_process",
                    "hidden_metaphysics",
                    "aqueous_echo",
                    "objective_transition",
                ),
                witness_ids=(),
                publicity=0.0,
                secrecy=1.0,
                data={
                    "aqueous_echo_tick_id": tick_id,
                    "from_band": before,
                    "to_band": after,
                },
                causal_parent_ids=self.source_contact_event_ids(node_id),
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
            emitted_event_ids.append(event.event_id)

        output_hash = self.state.state_hash()
        self._traces.append(
            AqueousEchoTickTrace(
                echo_tick_id=tick_id,
                game_minute=game_minute,
                input_state_hash=input_hash,
                hydrology_tick_ref=hydrology_tick.ref,
                material_contact_refs=tuple(item.ref for item in all_contacts),
                resonant_contact_refs=tuple(item.ref for item in resonant_contacts),
                contact_event_ids=tuple(
                    sorted({item.event_id for item in resonant_contacts})
                ),
                node_impulses={
                    key: _round(value) for key, value in sorted(impulses.items())
                },
                edge_exports={
                    key: _round(value) for key, value in sorted(edge_exports.items())
                },
                edge_deliveries={
                    key: _round(value) for key, value in sorted(edge_deliveries.items())
                },
                boundary_losses={
                    key: _round(value) for key, value in sorted(boundary_losses.items())
                },
                decay_loss=_round(decay_loss),
                transmission_loss=_round(transmission_loss),
                balance_residual=_round(residual),
                emitted_event_ids=tuple(emitted_event_ids),
                output_state_hash=output_hash,
            )
        )

    def _scan_material_contacts(
        self,
        game_minute: int,
    ) -> tuple[list[_ParsedContact], list[AqueousMaterialContactInput]]:
        all_contacts: list[_ParsedContact] = []
        resonant: list[AqueousMaterialContactInput] = []
        next_last_scanned_event_id = self._last_scanned_event_id
        for event in self.ledger.events:
            if event.event_id <= self._last_scanned_event_id:
                continue
            if event.game_minute > game_minute:
                break
            next_last_scanned_event_id = event.event_id
            payload = event.data
            if "material_contacts" not in payload:
                continue
            raw_contacts = payload["material_contacts"]
            if not isinstance(raw_contacts, list):
                raise ValueError("material_contacts must be a list")
            for index, raw in enumerate(raw_contacts, start=1):
                parsed = self._parse_contact(event, index, raw)
                if parsed is None:
                    continue
                all_contacts.append(parsed)
                if parsed.resonant is not None:
                    resonant.append(parsed.resonant)
        self._last_scanned_event_id = next_last_scanned_event_id
        return all_contacts, resonant

    def _parse_contact(
        self,
        event: WorldEvent,
        index: int,
        raw: Any,
    ) -> _ParsedContact | None:
        if not isinstance(raw, dict):
            raise ValueError("a material contact must be an object")
        if raw.get("schema") != MATERIAL_CONTACT_SCHEMA:
            raise ValueError("unsupported material contact schema")
        if _clean(raw.get("medium_kind", ""), "medium_kind") != "water":
            return None
        node_id = _clean(raw.get("medium_ref", ""), "medium_ref")
        if node_id not in self.state.node_amounts:
            return None
        item_id = _clean(raw.get("contact_item_id", ""), "contact_item_id")
        try:
            contact_units = float(raw.get("contact_units"))
        except (TypeError, ValueError):
            raise ValueError("material contact_units must be numeric") from None
        if not math.isfinite(contact_units) or contact_units <= 0.0:
            raise ValueError("material contact_units must be finite and positive")
        fractions = raw.get("material_fractions")
        if not isinstance(fractions, dict) or not fractions:
            raise ValueError("material contact needs material_fractions")
        cleaned_fractions: dict[str, float] = {}
        for material_id, fraction in fractions.items():
            cleaned_id = _clean(material_id, "material_id")
            try:
                numeric = float(fraction)
            except (TypeError, ValueError):
                raise ValueError("material fraction must be numeric") from None
            if not math.isfinite(numeric) or not 0.0 < numeric <= 1.0:
                raise ValueError("material fraction must be finite and in (0, 1]")
            cleaned_fractions[cleaned_id] = numeric
        if sum(cleaned_fractions.values()) > 1.0 + 1e-12:
            raise ValueError("material contact fractions cannot exceed 1")
        silver_fraction = cleaned_fractions.get("silver", 0.0)
        resonant = None
        if silver_fraction > 0.0:
            resonant = AqueousMaterialContactInput(
                event_id=event.event_id,
                contact_index=index,
                game_minute=event.game_minute,
                node_id=node_id,
                contact_item_id=item_id,
                contact_units=contact_units,
                silver_fraction=silver_fraction,
            )
        ref = f"world_event:{event.event_id}#material_contact:{index}"
        return _ParsedContact(
            ref=ref,
            event_id=event.event_id,
            node_id=node_id,
            contact_item_id=item_id,
            contact_units=contact_units,
            silver_fraction=silver_fraction,
            resonant=resonant,
        )

    def _transport_routes(
        self,
        edge_flows: dict[str, float],
    ) -> tuple[tuple[str, str, str, float], ...]:
        routes = {
            edge.edge_id: (edge.source_id, edge.target_id)
            for edge in self.hydrology.state.edges
        }
        routes.update(
            {
                "gate_discharge": (
                    "underpeak_gate_forebay",
                    "underpeak_upper_reach",
                ),
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
        return tuple(
            (edge_id, routes[edge_id][0], routes[edge_id][1], float(flow))
            for edge_id, flow in sorted(edge_flows.items())
            if edge_id in routes
        )

    @staticmethod
    def _band_for_concentration(concentration: float) -> str:
        if concentration < 0.0025:
            return "silent"
        if concentration < 0.010:
            return "faint"
        if concentration < 0.035:
            return "clear"
        return "strong"

    @staticmethod
    def _site_region(node_id: str) -> str:
        if node_id in {"lake_mirror", "lake_whisper", "northwood_junction"}:
            return "northwood"
        return "underpeak"

    def forensic_graph(self) -> dict[str, Any]:
        nodes: dict[str, dict[str, Any]] = {}
        edges: set[tuple[str, str, str]] = set()

        def add_node(ref: str, kind: str, **payload: Any) -> None:
            node = nodes.setdefault(ref, {"ref": ref, "kind": kind})
            node.update(payload)

        previous_ref: str | None = None
        for trace in self._traces:
            add_node(
                trace.ref,
                "aqueous_echo_tick",
                game_minute=trace.game_minute,
                input_state_hash=trace.input_state_hash,
                output_state_hash=trace.output_state_hash,
            )
            add_node(trace.hydrology_tick_ref, "hydrology_tick")
            edges.add((trace.hydrology_tick_ref, trace.ref, "water_transport_input"))
            if previous_ref is not None:
                edges.add((previous_ref, trace.ref, "echo_state_chain"))
            previous_ref = trace.ref
            for contact_ref in trace.material_contact_refs:
                event_ref = contact_ref.split("#", 1)[0]
                add_node(event_ref, "world_event")
                add_node(contact_ref, "material_contact")
                edges.add((event_ref, contact_ref, "event_contact_record"))
                edges.add((contact_ref, trace.ref, "material_contact_input"))
            for event_id in trace.emitted_event_ids:
                event_ref = f"world_event:{event_id}"
                add_node(event_ref, "world_event")
                edges.add((trace.ref, event_ref, "objective_consequence"))

        return {
            "nodes": [nodes[key] for key in sorted(nodes)],
            "edges": [
                {"source_ref": source, "target_ref": target, "kind": kind}
                for source, target, kind in sorted(edges)
            ],
        }

    def export_trace_jsonl(self, path: str | Path) -> None:
        with Path(path).open("w", encoding="utf-8") as handle:
            for trace in self._traces:
                handle.write(json.dumps(trace.as_dict(), ensure_ascii=False, sort_keys=True) + "\n")

    def export_state_json(self, path: str | Path) -> None:
        Path(path).write_text(
            json.dumps(self.state.as_dict(), ensure_ascii=False, indent=2, sort_keys=True)
            + "\n",
            encoding="utf-8",
        )

    def export_forensic_graph_json(self, path: str | Path) -> None:
        Path(path).write_text(
            json.dumps(self.forensic_graph(), ensure_ascii=False, indent=2, sort_keys=True)
            + "\n",
            encoding="utf-8",
        )


class EchoSenseOutcome(str, Enum):
    SENSED = "sensed"
    REJECTED = "rejected"


@dataclass(frozen=True)
class EchoSenseRequest:
    subject_id: str
    water_node_id: str


@dataclass(frozen=True)
class EchoSenseResult:
    ok: bool
    outcome: EchoSenseOutcome
    message: str
    event_id: int | None = None
    duration_minutes: int = 0
    percept: SubjectivePercept | None = None


@dataclass(frozen=True)
class EchoSenseTrace:
    sense_id: int
    subject_id: str
    water_node_id: str
    start_minute: int
    end_minute: int
    outcome: EchoSenseOutcome
    event_id: int | None
    percept_ref: str | None
    source_echo_tick_ref: str | None
    source_state_hash: str

    @property
    def ref(self) -> str:
        return f"aqueous_echo_sense:{self.sense_id}"

    def as_dict(self) -> dict[str, Any]:
        return {
            "sense_id": self.sense_id,
            "ref": self.ref,
            "subject_id": self.subject_id,
            "water_node_id": self.water_node_id,
            "start_minute": self.start_minute,
            "end_minute": self.end_minute,
            "outcome": self.outcome.value,
            "event_id": self.event_id,
            "percept_ref": self.percept_ref,
            "source_echo_tick_ref": self.source_echo_tick_ref,
            "source_state_hash": self.source_state_hash,
        }


class AqueousEchoSenseBridge:
    """Local, faculty-gated conversion of hidden field into a private percept."""

    def __init__(
        self,
        world: WorldState,
        ledger: EventLedger,
        echo: AqueousSilverEchoProcess,
        affordances: PhysicalAffordanceBridge,
        *,
        advance_time: Callable[[int], None] | None = None,
    ) -> None:
        if echo.world is not world or echo.ledger is not ledger:
            raise ValueError("echo sensing must share world and ledger with the echo process")
        if affordances.world is not world or affordances.ledger is not ledger:
            raise ValueError("echo sensing must share world and ledger with local affordances")
        self.world = world
        self.ledger = ledger
        self.echo = echo
        self.affordances = affordances
        self.perceptions: LocalPerceptionStore = affordances.perceptions
        self._advance_time = advance_time or world.advance
        self._traces: list[EchoSenseTrace] = []

    @property
    def traces(self) -> tuple[EchoSenseTrace, ...]:
        return tuple(self._traces)

    def sense(self, request: EchoSenseRequest) -> EchoSenseResult:
        subject_id = _clean(request.subject_id, "subject_id")
        node_id = _clean(request.water_node_id, "water_node_id")
        subjects = {item.subject_id: item for item in self.affordances.subjects}
        subject = subjects.get(subject_id)
        if subject is None:
            return self._reject(subject_id, node_id, "Unknown local subject")
        if node_id not in self.echo.state.node_amounts:
            return self._reject(subject_id, node_id, "Unknown local water node")
        if node_id not in subject.present_site_ids:
            return self._reject(
                subject_id,
                node_id,
                "The water is outside the subject's present local reach",
            )
        if "water_sense" not in subject.faculties:
            return self._reject(
                subject_id,
                node_id,
                "The subject lacks a faculty able to perceive an aqueous echo",
            )

        start_minute = self.world.game_minute
        self._advance_time(ECHO_SENSE_DURATION_MINUTES)
        source_hash = self.echo.state.state_hash()
        band = self.echo.state.band_states[node_id]
        movement = self._movement_cue(node_id, band)
        cues = {
            "echo_presence": band,
            "water_borne_pattern": "indistinct" if band == "silent" else "threaded",
            "movement_cue": movement,
            "source_identity": "unknown",
        }
        summary = {
            "silent": "No distinct foreign echo can be separated from the local water.",
            "faint": "A weak, uncertain thread seems to move within the local water.",
            "clear": "A distinct but source-less thread is perceptible in the local water.",
            "strong": "A strong water-borne thread is present, though its source remains hidden.",
        }[band]
        certainty = "uncertain" if band in {"silent", "faint"} else "bounded"
        parent_ids = self.echo.source_contact_event_ids(node_id)
        event = self.ledger.append(
            game_minute=self.world.game_minute,
            event_type="LOCAL_AQUEOUS_ECHO_SENSING_PERFORMED",
            actor_ids=(subject_id,),
            target_ids=(node_id,),
            location_id=AqueousSilverEchoProcess._site_region(node_id),
            tags=("objective_action", "local_perception", "aqueous_echo_sense"),
            witness_ids=(),
            publicity=0.02,
            secrecy=0.75,
            data={
                "observation_type": "sense_aqueous_echo",
                "percept_payload_withheld_from_ledger": True,
            },
            causal_parent_ids=parent_ids,
        )
        echo_tick_ref = self.echo.last_trace.ref if self.echo.last_trace is not None else None
        hydrology_tick = self.echo.hydrology.last_trace
        percept = self.perceptions.record(
            game_minute=self.world.game_minute,
            subject_id=subject_id,
            observation_type="sense_aqueous_echo",
            target_ref=node_id,
            site_id=node_id,
            cues=cues,
            summary=summary,
            certainty=certainty,
            inspection_event_id=event.event_id,
            source_state_hash=source_hash,
            source_hydrology_tick_ref=(
                hydrology_tick.ref if hydrology_tick is not None else None
            ),
            objective_source_event_ids=parent_ids,
            source_process_refs=(echo_tick_ref,) if echo_tick_ref is not None else (),
        )
        self._traces.append(
            EchoSenseTrace(
                sense_id=len(self._traces) + 1,
                subject_id=subject_id,
                water_node_id=node_id,
                start_minute=start_minute,
                end_minute=self.world.game_minute,
                outcome=EchoSenseOutcome.SENSED,
                event_id=event.event_id,
                percept_ref=percept.ref,
                source_echo_tick_ref=echo_tick_ref,
                source_state_hash=source_hash,
            )
        )
        return EchoSenseResult(
            True,
            EchoSenseOutcome.SENSED,
            "A private, qualitative aqueous perception was formed.",
            event_id=event.event_id,
            duration_minutes=ECHO_SENSE_DURATION_MINUTES,
            percept=percept,
        )

    def _reject(self, subject_id: str, node_id: str, message: str) -> EchoSenseResult:
        source_hash = self.echo.state.state_hash()
        self._traces.append(
            EchoSenseTrace(
                sense_id=len(self._traces) + 1,
                subject_id=subject_id,
                water_node_id=node_id,
                start_minute=self.world.game_minute,
                end_minute=self.world.game_minute,
                outcome=EchoSenseOutcome.REJECTED,
                event_id=None,
                percept_ref=None,
                source_echo_tick_ref=(
                    self.echo.last_trace.ref if self.echo.last_trace is not None else None
                ),
                source_state_hash=source_hash,
            )
        )
        return EchoSenseResult(False, EchoSenseOutcome.REJECTED, message)

    def _movement_cue(self, node_id: str, band: str) -> str:
        if band == "silent" or self.echo.hydrology.last_trace is None:
            return "none_discernible"
        incoming = 0.0
        for route_id, _, target_id, flow in self.echo._transport_routes(
            self.echo.hydrology.last_trace.edge_flows
        ):
            if target_id == node_id and flow >= MIN_CONNECTED_FLOW:
                incoming += flow
        return "moving" if incoming >= MIN_CONNECTED_FLOW else "pooled"

    def forensic_graph(self) -> dict[str, Any]:
        graph = self.echo.forensic_graph()
        nodes = {item["ref"]: dict(item) for item in graph["nodes"]}
        edges = {
            (item["source_ref"], item["target_ref"], item["kind"])
            for item in graph["edges"]
        }
        for trace in self._traces:
            nodes[trace.ref] = {
                "ref": trace.ref,
                "kind": "aqueous_echo_sense",
                "subject_id": trace.subject_id,
                "water_node_id": trace.water_node_id,
                "outcome": trace.outcome.value,
            }
            if trace.source_echo_tick_ref is not None:
                nodes.setdefault(
                    trace.source_echo_tick_ref,
                    {"ref": trace.source_echo_tick_ref, "kind": "aqueous_echo_tick"},
                )
                edges.add(
                    (trace.source_echo_tick_ref, trace.ref, "local_sensing_state_input")
                )
            if trace.event_id is not None:
                event_ref = f"world_event:{trace.event_id}"
                nodes.setdefault(event_ref, {"ref": event_ref, "kind": "world_event"})
                edges.add((trace.ref, event_ref, "sensing_resolution"))
            if trace.percept_ref is not None and trace.event_id is not None:
                nodes[trace.percept_ref] = {
                    "ref": trace.percept_ref,
                    "kind": "subjective_percept",
                    "subject_id": trace.subject_id,
                }
                edges.add(
                    (f"world_event:{trace.event_id}", trace.percept_ref, "perception_record")
                )
        return {
            "nodes": [nodes[key] for key in sorted(nodes)],
            "edges": [
                {"source_ref": source, "target_ref": target, "kind": kind}
                for source, target, kind in sorted(edges)
            ],
        }

    def export_trace_jsonl(self, path: str | Path) -> None:
        with Path(path).open("w", encoding="utf-8") as handle:
            for trace in self._traces:
                handle.write(json.dumps(trace.as_dict(), ensure_ascii=False, sort_keys=True) + "\n")

    def export_forensic_graph_json(self, path: str | Path) -> None:
        Path(path).write_text(
            json.dumps(self.forensic_graph(), ensure_ascii=False, indent=2, sort_keys=True)
            + "\n",
            encoding="utf-8",
        )


def create_silver_thread_aqueous_echo(
    world: WorldState,
    ledger: EventLedger,
    hydrology: HydrologyProcess,
) -> AqueousSilverEchoProcess:
    node_ids = set(hydrology.state.nodes)
    state = AqueousEchoState(
        node_amounts={node_id: 0.0 for node_id in sorted(node_ids)},
        band_states={node_id: "silent" for node_id in sorted(node_ids)},
    )
    return AqueousSilverEchoProcess(world, ledger, hydrology, state)


def create_silver_thread_echo_sense_bridge(
    world: WorldState,
    ledger: EventLedger,
    echo: AqueousSilverEchoProcess,
    affordances: PhysicalAffordanceBridge,
    *,
    advance_time: Callable[[int], None] | None = None,
) -> AqueousEchoSenseBridge:
    return AqueousEchoSenseBridge(
        world,
        ledger,
        echo,
        affordances,
        advance_time=advance_time,
    )
