from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Iterable

from .ledger import EventLedger
from .models import WorldState
from .processes.hydrology import HydrologyProcess


def _clean_text(value: str, label: str) -> str:
    cleaned = " ".join(str(value).split())
    if not cleaned:
        raise ValueError(f"{label} cannot be empty")
    return cleaned


def _json(value: dict[str, Any]) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, float(value)))


class PhysicalActionType(str, Enum):
    INSPECT_GATE = "inspect_gate"
    INSPECT_WATER_STATE = "inspect_water_state"
    SURVEY_GALLERY = "survey_gallery"
    INSPECT_BANK = "inspect_bank"
    ADJUST_SLUICE = "adjust_sluice"
    CLEAR_GATE_DEBRIS = "clear_gate_debris"
    FORCE_SLUICE = "force_sluice"
    REPAIR_GATE = "repair_gate"
    CLEAR_GALLERY_RUBBLE = "clear_gallery_rubble"
    REINFORCE_BANK = "reinforce_bank"
    SHIFT_LOCAL_SILT = "shift_local_silt"


class PhysicalActionOutcome(str, Enum):
    SUCCEEDED = "succeeded"
    PARTIAL = "partial"
    BLOCKED = "blocked"
    REJECTED = "rejected"


INSPECTION_ACTIONS = {
    PhysicalActionType.INSPECT_GATE,
    PhysicalActionType.INSPECT_WATER_STATE,
    PhysicalActionType.SURVEY_GALLERY,
    PhysicalActionType.INSPECT_BANK,
}


ACTION_DURATIONS = {
    PhysicalActionType.INSPECT_GATE: 45,
    PhysicalActionType.INSPECT_WATER_STATE: 30,
    PhysicalActionType.SURVEY_GALLERY: 90,
    PhysicalActionType.INSPECT_BANK: 60,
    PhysicalActionType.ADJUST_SLUICE: 180,
    PhysicalActionType.CLEAR_GATE_DEBRIS: 360,
    PhysicalActionType.FORCE_SLUICE: 120,
    PhysicalActionType.REPAIR_GATE: 480,
    PhysicalActionType.CLEAR_GALLERY_RUBBLE: 480,
    PhysicalActionType.REINFORCE_BANK: 720,
    PhysicalActionType.SHIFT_LOCAL_SILT: 180,
}


GATE_TARGET = "underpeak_river_gate"
GALLERY_TARGET = "underpeak_gallery_sump"
BANK_TARGET = "underpeak_upper_reach_bank"
GATE_SITE = "underpeak_gate_forebay"


@dataclass
class LocalSubjectState:
    """The body, local reach and tools available to one causal subject.

    This is not a mind and contains no world answer key. A neural or rule mind
    may later receive :class:`SubjectiveWorldView`, never this mutable server
    record.
    """

    subject_id: str
    subject_kind: str
    present_site_ids: tuple[str, ...]
    faculties: tuple[str, ...] = ()
    capability_levels: dict[str, float] = field(default_factory=dict)
    resources: dict[str, float] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.subject_id = _clean_text(self.subject_id, "subject_id")
        self.subject_kind = _clean_text(self.subject_kind, "subject_kind")
        self.present_site_ids = tuple(
            dict.fromkeys(_clean_text(item, "present site") for item in self.present_site_ids)
        )
        if not self.present_site_ids:
            raise ValueError("a local subject must be present at at least one site")
        self.faculties = tuple(
            dict.fromkeys(_clean_text(item, "faculty") for item in self.faculties)
        )
        cleaned_capabilities: dict[str, float] = {}
        for key, value in self.capability_levels.items():
            action_key = key.value if isinstance(key, PhysicalActionType) else _clean_text(key, "capability")
            numeric = float(value)
            if not 0.0 <= numeric <= 1.0:
                raise ValueError(f"capability {action_key} must be in [0, 1]")
            cleaned_capabilities[action_key] = numeric
        self.capability_levels = cleaned_capabilities
        cleaned_resources: dict[str, float] = {}
        for key, value in self.resources.items():
            resource = _clean_text(key, "resource")
            numeric = float(value)
            if not math.isfinite(numeric) or numeric < 0.0:
                raise ValueError(f"resource {resource} must be finite and non-negative")
            cleaned_resources[resource] = round(numeric, 6)
        self.resources = cleaned_resources

    def capability(self, action_type: PhysicalActionType) -> float:
        return self.capability_levels.get(action_type.value, 0.0)

    def as_dict(self) -> dict[str, Any]:
        return {
            "subject_id": self.subject_id,
            "subject_kind": self.subject_kind,
            "present_site_ids": list(self.present_site_ids),
            "faculties": list(self.faculties),
            "capability_levels": dict(sorted(self.capability_levels.items())),
            "resources": dict(sorted(self.resources.items())),
        }


@dataclass(frozen=True)
class SubjectivePercept:
    percept_id: int
    game_minute: int
    subject_id: str
    observation_type: str
    target_ref: str
    site_id: str
    cues_json: str
    summary: str
    certainty: str

    @property
    def ref(self) -> str:
        return f"local_percept:{self.percept_id}"

    @property
    def cues(self) -> dict[str, str]:
        return json.loads(self.cues_json)

    def as_dict(self) -> dict[str, Any]:
        return {
            "percept_id": self.percept_id,
            "ref": self.ref,
            "game_minute": self.game_minute,
            "subject_id": self.subject_id,
            "observation_type": self.observation_type,
            "target_ref": self.target_ref,
            "site_id": self.site_id,
            "cues": self.cues,
            "summary": self.summary,
            "certainty": self.certainty,
        }


@dataclass(frozen=True)
class ObservationProvenance:
    percept_ref: str
    inspection_event_id: int
    source_state_hash: str
    source_hydrology_tick_ref: str | None
    objective_source_event_ids: tuple[int, ...]
    source_process_refs: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        payload = {
            "record_type": "observation_provenance",
            "percept_ref": self.percept_ref,
            "inspection_event_id": self.inspection_event_id,
            "source_state_hash": self.source_state_hash,
            "source_hydrology_tick_ref": self.source_hydrology_tick_ref,
            "objective_source_event_ids": list(self.objective_source_event_ids),
        }
        if self.source_process_refs:
            payload["source_process_refs"] = list(self.source_process_refs)
        return payload


class LocalPerceptionStore:
    """Private subjective observations plus a separate Creator-facing trace."""

    def __init__(self) -> None:
        self._percepts: list[SubjectivePercept] = []
        self._provenance: list[ObservationProvenance] = []
        self._percept_by_ref: dict[str, SubjectivePercept] = {}
        self._provenance_by_ref: dict[str, ObservationProvenance] = {}

    @property
    def all_percepts(self) -> tuple[SubjectivePercept, ...]:
        return tuple(self._percepts)

    @property
    def provenance(self) -> tuple[ObservationProvenance, ...]:
        return tuple(self._provenance)

    def for_subject(self, subject_id: str) -> tuple[SubjectivePercept, ...]:
        return tuple(item for item in self._percepts if item.subject_id == subject_id)

    def get_for_subject(self, subject_id: str, percept_ref: str) -> SubjectivePercept:
        try:
            percept = self._percept_by_ref[percept_ref]
        except KeyError as exc:
            raise ValueError(f"unknown local percept: {percept_ref}") from exc
        if percept.subject_id != subject_id:
            raise PermissionError("a subject cannot use another subject's private percept")
        return percept

    def provenance_for(self, percept_ref: str) -> ObservationProvenance:
        try:
            return self._provenance_by_ref[percept_ref]
        except KeyError as exc:
            raise ValueError(f"unknown local percept provenance: {percept_ref}") from exc

    def record(
        self,
        *,
        game_minute: int,
        subject_id: str,
        observation_type: str,
        target_ref: str,
        site_id: str,
        cues: dict[str, str],
        summary: str,
        certainty: str,
        inspection_event_id: int,
        source_state_hash: str,
        source_hydrology_tick_ref: str | None,
        objective_source_event_ids: Iterable[int] = (),
        source_process_refs: Iterable[str] = (),
    ) -> SubjectivePercept:
        percept = SubjectivePercept(
            percept_id=len(self._percepts) + 1,
            game_minute=game_minute,
            subject_id=_clean_text(subject_id, "subject_id"),
            observation_type=_clean_text(observation_type, "observation_type"),
            target_ref=_clean_text(target_ref, "target_ref"),
            site_id=_clean_text(site_id, "site_id"),
            cues_json=_json({str(key): str(value) for key, value in sorted(cues.items())}),
            summary=_clean_text(summary, "percept summary"),
            certainty=_clean_text(certainty, "certainty"),
        )
        sources = tuple(sorted(set(int(item) for item in objective_source_event_ids)))
        if any(item <= 0 for item in sources):
            raise ValueError("objective source event ids must be positive")
        process_refs = tuple(
            dict.fromkeys(_clean_text(item, "source process ref") for item in source_process_refs)
        )
        trace = ObservationProvenance(
            percept_ref=percept.ref,
            inspection_event_id=inspection_event_id,
            source_state_hash=_clean_text(source_state_hash, "source_state_hash"),
            source_hydrology_tick_ref=source_hydrology_tick_ref,
            objective_source_event_ids=sources,
            source_process_refs=process_refs,
        )
        self._percepts.append(percept)
        self._provenance.append(trace)
        self._percept_by_ref[percept.ref] = percept
        self._provenance_by_ref[percept.ref] = trace
        return percept

    def export_percepts_jsonl(self, path: str | Path) -> None:
        with Path(path).open("w", encoding="utf-8") as handle:
            for percept in self._percepts:
                handle.write(json.dumps(percept.as_dict(), ensure_ascii=False, sort_keys=True) + "\n")

    def export_provenance_jsonl(self, path: str | Path) -> None:
        with Path(path).open("w", encoding="utf-8") as handle:
            for trace in self._provenance:
                handle.write(json.dumps(trace.as_dict(), ensure_ascii=False, sort_keys=True) + "\n")


@dataclass(frozen=True)
class PhysicalActionRequest:
    subject_id: str
    action_type: PhysicalActionType
    target_ref: str
    params: dict[str, Any] = field(default_factory=dict)
    evidence_refs: tuple[str, ...] = ()


@dataclass(frozen=True)
class PhysicalActionResult:
    ok: bool
    outcome: PhysicalActionOutcome
    message: str
    event_id: int | None = None
    duration_minutes: int = 0
    percept: SubjectivePercept | None = None


@dataclass(frozen=True)
class PhysicalActionTrace:
    action_id: int
    subject_id: str
    action_type: PhysicalActionType
    target_ref: str
    start_minute: int
    end_minute: int
    evidence_refs: tuple[str, ...]
    outcome: PhysicalActionOutcome
    event_id: int | None
    input_state_hash: str
    output_state_hash: str
    effect_json: str

    @property
    def ref(self) -> str:
        return f"physical_action:{self.action_id}"

    @property
    def effect(self) -> dict[str, Any]:
        return json.loads(self.effect_json)

    def as_dict(self) -> dict[str, Any]:
        return {
            "action_id": self.action_id,
            "ref": self.ref,
            "subject_id": self.subject_id,
            "action_type": self.action_type.value,
            "target_ref": self.target_ref,
            "start_minute": self.start_minute,
            "end_minute": self.end_minute,
            "evidence_refs": list(self.evidence_refs),
            "outcome": self.outcome.value,
            "event_id": self.event_id,
            "input_state_hash": self.input_state_hash,
            "output_state_hash": self.output_state_hash,
            "effect": self.effect,
        }


@dataclass(frozen=True)
class SubjectiveWorldView:
    subject_id: str
    game_minute: int
    present_site_ids: tuple[str, ...]
    faculties: tuple[str, ...]
    capability_levels: dict[str, float]
    resources: dict[str, float]
    percepts: tuple[SubjectivePercept, ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "subject_id": self.subject_id,
            "game_minute": self.game_minute,
            "present_site_ids": list(self.present_site_ids),
            "faculties": list(self.faculties),
            "capability_levels": dict(sorted(self.capability_levels.items())),
            "resources": dict(sorted(self.resources.items())),
            "percepts": [item.as_dict() for item in self.percepts],
        }


@dataclass(frozen=True)
class _MutationPlan:
    event_type: str
    outcome: PhysicalActionOutcome
    message: str
    effect: dict[str, Any]
    apply: Callable[[int], None]


class PhysicalAffordanceBridge:
    """Bounded subject-facing bridge over authoritative Silver Thread physics.

    Minds receive only :class:`SubjectiveWorldView`. Requests are checked for
    local presence, capability, private-evidence ownership and resources. The
    bridge records an objective action and then asks Hydrology to apply the
    physical mutation; it never sets a story outcome or Project status.
    """

    def __init__(
        self,
        world: WorldState,
        ledger: EventLedger,
        hydrology: HydrologyProcess,
        perceptions: LocalPerceptionStore | None = None,
        *,
        advance_time: Callable[[int], None] | None = None,
    ) -> None:
        if hydrology.world is not world or hydrology.ledger is not ledger:
            raise ValueError("affordance bridge must share world and ledger with hydrology")
        self.world = world
        self.ledger = ledger
        self._hydrology = hydrology
        self.perceptions = perceptions or LocalPerceptionStore()
        self._advance_time = advance_time or world.advance
        self._subjects: dict[str, LocalSubjectState] = {}
        self._action_traces: list[PhysicalActionTrace] = []

    @property
    def subjects(self) -> tuple[LocalSubjectState, ...]:
        return tuple(self._subjects[key] for key in sorted(self._subjects))

    @property
    def action_traces(self) -> tuple[PhysicalActionTrace, ...]:
        return tuple(self._action_traces)

    def register_subject(self, subject: LocalSubjectState) -> None:
        if subject.subject_id in self._subjects:
            raise ValueError(f"local subject already registered: {subject.subject_id}")
        self._subjects[subject.subject_id] = subject

    def subject_view(self, subject_id: str) -> SubjectiveWorldView:
        subject = self._require_subject(subject_id)
        return SubjectiveWorldView(
            subject_id=subject.subject_id,
            game_minute=self.world.game_minute,
            present_site_ids=subject.present_site_ids,
            faculties=subject.faculties,
            capability_levels=dict(subject.capability_levels),
            resources=dict(subject.resources),
            percepts=self.perceptions.for_subject(subject.subject_id),
        )

    def perform(self, request: PhysicalActionRequest) -> PhysicalActionResult:
        subject_id = _clean_text(request.subject_id, "subject_id")
        target_ref = _clean_text(request.target_ref, "target_ref")
        subject = self._subjects.get(subject_id)
        if subject is None:
            return self._reject(request, target_ref, "Unknown local subject")

        try:
            target_site = self._target_site(request.action_type, target_ref)
        except ValueError as exc:
            return self._reject(request, target_ref, str(exc))
        if target_site not in subject.present_site_ids:
            return self._reject(
                request,
                target_ref,
                "The target is outside the subject's present local reach",
            )
        skill = subject.capability(request.action_type)
        if skill <= 0.0:
            return self._reject(
                request,
                target_ref,
                "The subject lacks the required physical faculty or capability",
            )

        evidence_refs = tuple(dict.fromkeys(request.evidence_refs))
        try:
            evidence = tuple(
                self.perceptions.get_for_subject(subject_id, ref) for ref in evidence_refs
            )
        except (ValueError, PermissionError) as exc:
            return self._reject(request, target_ref, str(exc), evidence_refs=evidence_refs)
        if evidence and not any(item.target_ref == target_ref for item in evidence):
            return self._reject(
                request,
                target_ref,
                "The cited local evidence does not concern this target",
                evidence_refs=evidence_refs,
            )

        if request.action_type in INSPECTION_ACTIONS:
            return self._inspect(
                subject,
                request,
                target_ref,
                target_site,
                evidence_refs,
            )
        return self._mutate(
            subject,
            request,
            target_ref,
            target_site,
            skill,
            evidence_refs,
        )

    def export_action_trace_jsonl(self, path: str | Path) -> None:
        with Path(path).open("w", encoding="utf-8") as handle:
            for trace in self._action_traces:
                handle.write(json.dumps(trace.as_dict(), ensure_ascii=False, sort_keys=True) + "\n")

    def forensic_graph(self) -> dict[str, Any]:
        """Return the auditable observation → action → physics braid.

        Edge names describe records the runtime actually has. In particular,
        ``decision_input`` means a cited private percept, not a post-hoc claim
        about an agent's inner psychology.
        """

        nodes: dict[str, dict[str, Any]] = {}
        edges: set[tuple[str, str, str]] = set()

        def add_node(ref: str, kind: str, **payload: Any) -> None:
            node = nodes.setdefault(ref, {"ref": ref, "kind": kind})
            if node["kind"] != kind:
                raise AssertionError(f"forensic ref changed kind: {ref}")
            node.update(payload)

        for event in self.ledger.events:
            ref = f"world_event:{event.event_id}"
            add_node(
                ref,
                "world_event",
                game_minute=event.game_minute,
                event_type=event.event_type,
            )
            for parent_id in event.causal_parent_ids:
                parent_ref = f"world_event:{parent_id}"
                add_node(parent_ref, "world_event")
                edges.add((parent_ref, ref, "objective_cause"))

        for percept in self.perceptions.all_percepts:
            add_node(
                percept.ref,
                "subjective_percept",
                game_minute=percept.game_minute,
                subject_id=percept.subject_id,
                observation_type=percept.observation_type,
                target_ref=percept.target_ref,
            )
            provenance = self.perceptions.provenance_for(percept.ref)
            inspection_ref = f"world_event:{provenance.inspection_event_id}"
            add_node(inspection_ref, "world_event")
            edges.add((inspection_ref, percept.ref, "perception_record"))
            if provenance.source_hydrology_tick_ref is not None:
                add_node(provenance.source_hydrology_tick_ref, "hydrology_tick")
                edges.add(
                    (provenance.source_hydrology_tick_ref, percept.ref, "observation_state_source")
                )
            for process_ref in provenance.source_process_refs:
                add_node(process_ref, "world_process_tick")
                edges.add((process_ref, percept.ref, "observation_state_source"))
            for event_id in provenance.objective_source_event_ids:
                source_ref = f"world_event:{event_id}"
                add_node(source_ref, "world_event")
                edges.add((source_ref, percept.ref, "perception_source"))

        for action in self._action_traces:
            add_node(
                action.ref,
                "physical_action",
                subject_id=action.subject_id,
                action_type=action.action_type.value,
                outcome=action.outcome.value,
                start_minute=action.start_minute,
                end_minute=action.end_minute,
            )
            for percept_ref in action.evidence_refs:
                add_node(percept_ref, "subjective_percept")
                edges.add((percept_ref, action.ref, "decision_input"))
            if action.event_id is not None:
                event_ref = f"world_event:{action.event_id}"
                add_node(event_ref, "world_event")
                edges.add((action.ref, event_ref, "action_resolution"))

        for tick in self._hydrology.traces:
            add_node(
                tick.ref,
                "hydrology_tick",
                game_minute=tick.game_minute,
                input_state_hash=tick.input_state_hash,
                output_state_hash=tick.output_state_hash,
            )
            for event_id in tick.causal_action_event_ids:
                event_ref = f"world_event:{event_id}"
                add_node(event_ref, "world_event")
                edges.add((event_ref, tick.ref, "physical_consequence_input"))
            for event_id in tick.emitted_event_ids:
                event_ref = f"world_event:{event_id}"
                add_node(event_ref, "world_event")
                edges.add((tick.ref, event_ref, "objective_consequence"))

        return {
            "nodes": [nodes[key] for key in sorted(nodes)],
            "edges": [
                {"source_ref": source, "target_ref": target, "kind": kind}
                for source, target, kind in sorted(edges)
            ],
        }

    def export_forensic_graph_json(self, path: str | Path) -> None:
        Path(path).write_text(
            json.dumps(self.forensic_graph(), ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    def export_subjects_json(self, path: str | Path) -> None:
        Path(path).write_text(
            json.dumps(
                {item.subject_id: item.as_dict() for item in self.subjects},
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )

    def _require_subject(self, subject_id: str) -> LocalSubjectState:
        try:
            return self._subjects[subject_id]
        except KeyError as exc:
            raise KeyError(f"Unknown local subject: {subject_id}") from exc

    def _reject(
        self,
        request: PhysicalActionRequest,
        target_ref: str,
        message: str,
        *,
        evidence_refs: tuple[str, ...] | None = None,
        outcome: PhysicalActionOutcome = PhysicalActionOutcome.REJECTED,
    ) -> PhysicalActionResult:
        state_hash = self._hydrology.state.state_hash()
        self._action_traces.append(
            PhysicalActionTrace(
                action_id=len(self._action_traces) + 1,
                subject_id=str(request.subject_id),
                action_type=request.action_type,
                target_ref=target_ref,
                start_minute=self.world.game_minute,
                end_minute=self.world.game_minute,
                evidence_refs=tuple(request.evidence_refs) if evidence_refs is None else evidence_refs,
                outcome=outcome,
                event_id=None,
                input_state_hash=state_hash,
                output_state_hash=state_hash,
                effect_json="{}",
            )
        )
        return PhysicalActionResult(False, outcome, message)

    def _inspect(
        self,
        subject: LocalSubjectState,
        request: PhysicalActionRequest,
        target_ref: str,
        target_site: str,
        evidence_refs: tuple[str, ...],
    ) -> PhysicalActionResult:
        start_minute = self.world.game_minute
        input_hash = self._hydrology.state.state_hash()
        duration = ACTION_DURATIONS[request.action_type]
        self._advance_time(duration)
        cues, summary, certainty = self._observation_payload(subject, request.action_type, target_ref)
        parent_ids = self._observation_parent_event_ids(target_ref)
        event = self.ledger.append(
            game_minute=self.world.game_minute,
            event_type="LOCAL_INSPECTION_PERFORMED",
            actor_ids=(subject.subject_id,),
            target_ids=(target_ref,),
            location_id=self._site_region(target_site),
            tags=("objective_action", "inspection", "local_perception"),
            witness_ids=(),
            publicity=0.05,
            secrecy=0.50,
            data={
                "inspection_type": request.action_type.value,
                "percept_payload_withheld_from_ledger": True,
            },
            causal_parent_ids=parent_ids,
        )
        last_tick = self._hydrology.last_trace
        percept = self.perceptions.record(
            game_minute=self.world.game_minute,
            subject_id=subject.subject_id,
            observation_type=request.action_type.value,
            target_ref=target_ref,
            site_id=target_site,
            cues=cues,
            summary=summary,
            certainty=certainty,
            inspection_event_id=event.event_id,
            source_state_hash=self._hydrology.state.state_hash(),
            source_hydrology_tick_ref=last_tick.ref if last_tick is not None else None,
            objective_source_event_ids=parent_ids,
        )
        output_hash = self._hydrology.state.state_hash()
        self._action_traces.append(
            PhysicalActionTrace(
                action_id=len(self._action_traces) + 1,
                subject_id=subject.subject_id,
                action_type=request.action_type,
                target_ref=target_ref,
                start_minute=start_minute,
                end_minute=self.world.game_minute,
                evidence_refs=evidence_refs,
                outcome=PhysicalActionOutcome.SUCCEEDED,
                event_id=event.event_id,
                input_state_hash=input_hash,
                output_state_hash=output_hash,
                effect_json=_json({"percept_ref": percept.ref}),
            )
        )
        return PhysicalActionResult(
            True,
            PhysicalActionOutcome.SUCCEEDED,
            "A local observation was formed.",
            event_id=event.event_id,
            duration_minutes=duration,
            percept=percept,
        )

    def _mutate(
        self,
        subject: LocalSubjectState,
        request: PhysicalActionRequest,
        target_ref: str,
        target_site: str,
        skill: float,
        evidence_refs: tuple[str, ...],
    ) -> PhysicalActionResult:
        try:
            effort = float(request.params.get("effort", 1.0))
        except (TypeError, ValueError):
            return self._reject(request, target_ref, "effort must be numeric", evidence_refs=evidence_refs)
        if not 0.0 < effort <= 1.0:
            return self._reject(request, target_ref, "effort must be in (0, 1]", evidence_refs=evidence_refs)
        try:
            costs = self._resource_costs(request.action_type, effort)
            self._validate_action_params(request)
        except ValueError as exc:
            return self._reject(request, target_ref, str(exc), evidence_refs=evidence_refs)
        missing = {
            key: amount - subject.resources.get(key, 0.0)
            for key, amount in costs.items()
            if subject.resources.get(key, 0.0) + 1e-12 < amount
        }
        if missing:
            return self._reject(
                request,
                target_ref,
                "The subject lacks the required local effort or materials",
                evidence_refs=evidence_refs,
                outcome=PhysicalActionOutcome.BLOCKED,
            )

        start_minute = self.world.game_minute
        input_hash = self._hydrology.state.state_hash()
        duration = ACTION_DURATIONS[request.action_type]
        self._advance_time(duration)
        plan = self._mutation_plan(request, skill, effort)
        parent_ids = tuple(
            self.perceptions.provenance_for(ref).inspection_event_id for ref in evidence_refs
        )
        event = self.ledger.append(
            game_minute=self.world.game_minute,
            event_type=plan.event_type,
            actor_ids=(subject.subject_id,),
            target_ids=(target_ref,),
            location_id=self._site_region(target_site),
            tags=("objective_action", "physical_affordance", "hydrology_intervention"),
            witness_ids=(),
            publicity=0.10,
            secrecy=0.35,
            data={
                "action_type": request.action_type.value,
                "effect": plan.effect,
                "evidence_refs": list(evidence_refs),
            },
            causal_parent_ids=parent_ids,
        )
        plan.apply(event.event_id)
        for key, amount in costs.items():
            subject.resources[key] = round(subject.resources.get(key, 0.0) - amount, 6)
        output_hash = self._hydrology.state.state_hash()
        self._action_traces.append(
            PhysicalActionTrace(
                action_id=len(self._action_traces) + 1,
                subject_id=subject.subject_id,
                action_type=request.action_type,
                target_ref=target_ref,
                start_minute=start_minute,
                end_minute=self.world.game_minute,
                evidence_refs=evidence_refs,
                outcome=plan.outcome,
                event_id=event.event_id,
                input_state_hash=input_hash,
                output_state_hash=output_hash,
                effect_json=_json(plan.effect),
            )
        )
        return PhysicalActionResult(
            plan.outcome in {PhysicalActionOutcome.SUCCEEDED, PhysicalActionOutcome.PARTIAL},
            plan.outcome,
            plan.message,
            event_id=event.event_id,
            duration_minutes=duration,
        )

    def _validate_action_params(self, request: PhysicalActionRequest) -> None:
        if request.action_type in {PhysicalActionType.ADJUST_SLUICE, PhysicalActionType.FORCE_SLUICE}:
            try:
                delta = float(request.params.get("delta"))
            except (TypeError, ValueError):
                raise ValueError("sluice delta must be numeric") from None
            if not -1.0 <= delta <= 1.0 or abs(delta) < 1e-9:
                raise ValueError("sluice delta must be non-zero and in [-1, 1]")

    @staticmethod
    def _resource_costs(action_type: PhysicalActionType, effort: float) -> dict[str, float]:
        effort_scale = {
            PhysicalActionType.ADJUST_SLUICE: 0.30,
            PhysicalActionType.CLEAR_GATE_DEBRIS: 0.55,
            PhysicalActionType.FORCE_SLUICE: 0.45,
            PhysicalActionType.REPAIR_GATE: 0.75,
            PhysicalActionType.CLEAR_GALLERY_RUBBLE: 0.80,
            PhysicalActionType.REINFORCE_BANK: 0.90,
            PhysicalActionType.SHIFT_LOCAL_SILT: 0.35,
        }
        costs = {"effort": round(effort_scale[action_type] * effort, 6)}
        if action_type is PhysicalActionType.REPAIR_GATE:
            costs["materials"] = round(0.60 * effort, 6)
        elif action_type is PhysicalActionType.REINFORCE_BANK:
            costs["materials"] = round(0.90 * effort, 6)
        return costs

    def _mutation_plan(
        self,
        request: PhysicalActionRequest,
        skill: float,
        effort: float,
    ) -> _MutationPlan:
        state = self._hydrology.state
        action_type = request.action_type

        if action_type is PhysicalActionType.ADJUST_SLUICE:
            requested = float(request.params["delta"])
            before = state.gate.sluice_position
            mobility = _clamp(
                (1.0 - 0.85 * state.gate.debris_load)
                * (0.45 + 0.55 * state.gate.structure_integrity)
            )
            max_motion = 0.38 * skill * effort * mobility
            available = (1.0 - before) if requested > 0.0 else before
            applied = math.copysign(min(abs(requested), max_motion, available), requested)
            after = _clamp(before + applied)
            outcome = self._movement_outcome(requested, applied)
            message = {
                PhysicalActionOutcome.SUCCEEDED: "The sluice moved as intended.",
                PhysicalActionOutcome.PARTIAL: "The mechanism moved, but less than intended.",
                PhysicalActionOutcome.BLOCKED: "The old mechanism resisted the attempt.",
            }[outcome]
            return _MutationPlan(
                "SLUICE_ADJUSTED",
                outcome,
                message,
                {
                    "requested_delta": round(requested, 6),
                    "applied_delta": round(applied, 6),
                    "before_position": round(before, 6),
                    "after_position": round(after, 6),
                },
                lambda event_id: self._hydrology.apply_sluice_position(
                    after, causal_action_event_id=event_id
                ),
            )

        if action_type is PhysicalActionType.CLEAR_GATE_DEBRIS:
            before = state.gate.debris_load
            removed = min(before, 0.28 * skill * effort)
            after = _clamp(before - removed)
            outcome = (
                PhysicalActionOutcome.SUCCEEDED
                if removed >= 0.01
                else PhysicalActionOutcome.BLOCKED
            )
            return _MutationPlan(
                "GATE_DEBRIS_CLEARED",
                outcome,
                "Debris was pulled away from the gate throat."
                if outcome is PhysicalActionOutcome.SUCCEEDED
                else "No meaningful debris could be removed.",
                {
                    "removed": round(removed, 6),
                    "before_debris": round(before, 6),
                    "after_debris": round(after, 6),
                },
                lambda event_id: self._hydrology.clear_gate_debris(
                    removed, causal_action_event_id=event_id
                ),
            )

        if action_type is PhysicalActionType.SHIFT_LOCAL_SILT:
            before = state.gate.debris_load
            removed = min(before, 0.08 * skill * effort)
            after = _clamp(before - removed)
            outcome = (
                PhysicalActionOutcome.SUCCEEDED
                if removed >= 0.005
                else PhysicalActionOutcome.BLOCKED
            )
            return _MutationPlan(
                "LOCAL_SILT_SHIFTED",
                outcome,
                "A bounded tongue of silt moved away from the gate throat."
                if outcome is PhysicalActionOutcome.SUCCEEDED
                else "The local silt barely moved.",
                {
                    "removed": round(removed, 6),
                    "before_debris": round(before, 6),
                    "after_debris": round(after, 6),
                    "bounded_lesser_entity_action": True,
                },
                lambda event_id: self._hydrology.clear_gate_debris(
                    removed, causal_action_event_id=event_id
                ),
            )

        if action_type is PhysicalActionType.FORCE_SLUICE:
            requested = float(request.params["delta"])
            before_position = state.gate.sluice_position
            before_integrity = state.gate.structure_integrity
            leverage = 0.60 + 0.40 * (1.0 - state.gate.debris_load)
            max_motion = 0.55 * skill * effort * leverage
            available = (1.0 - before_position) if requested > 0.0 else before_position
            applied = math.copysign(min(abs(requested), max_motion, available), requested)
            after_position = _clamp(before_position + applied)
            damage = min(
                before_integrity,
                (0.04 + 0.12 * effort * state.gate.debris_load) if abs(applied) >= 0.01 else 0.0,
            )
            after_integrity = _clamp(before_integrity - damage)
            outcome = self._movement_outcome(requested, applied)

            def apply(event_id: int) -> None:
                self._hydrology.apply_sluice_position(
                    after_position, causal_action_event_id=event_id
                )
                self._hydrology.damage_gate(damage, causal_action_event_id=event_id)

            return _MutationPlan(
                "SLUICE_FORCED",
                outcome,
                "The sluice yielded under force, and the old structure protested."
                if outcome is not PhysicalActionOutcome.BLOCKED
                else "The forced attempt failed to move the sluice.",
                {
                    "requested_delta": round(requested, 6),
                    "applied_delta": round(applied, 6),
                    "before_position": round(before_position, 6),
                    "after_position": round(after_position, 6),
                    "integrity_damage": round(damage, 6),
                    "after_integrity": round(after_integrity, 6),
                },
                apply,
            )

        if action_type is PhysicalActionType.REPAIR_GATE:
            before = state.gate.structure_integrity
            restored = min(1.0 - before, 0.22 * skill * effort)
            after = _clamp(before + restored)
            outcome = (
                PhysicalActionOutcome.SUCCEEDED
                if restored >= 0.01
                else PhysicalActionOutcome.BLOCKED
            )
            return _MutationPlan(
                "GATE_REPAIRED",
                outcome,
                "The repair took hold in the old gate structure."
                if outcome is PhysicalActionOutcome.SUCCEEDED
                else "The work found no repairable gain.",
                {
                    "restored": round(restored, 6),
                    "before_integrity": round(before, 6),
                    "after_integrity": round(after, 6),
                },
                lambda event_id: self._hydrology.repair_gate(
                    restored, causal_action_event_id=event_id
                ),
            )

        if action_type is PhysicalActionType.CLEAR_GALLERY_RUBBLE:
            before = state.gallery.rubble_obstruction
            removed = min(before, 0.30 * skill * effort)
            after = _clamp(before - removed)
            outcome = (
                PhysicalActionOutcome.SUCCEEDED
                if removed >= 0.01
                else PhysicalActionOutcome.BLOCKED
            )
            return _MutationPlan(
                "GALLERY_RUBBLE_CLEARED",
                outcome,
                "Rubble was removed from the gallery route."
                if outcome is PhysicalActionOutcome.SUCCEEDED
                else "The attempt did not clear a meaningful path.",
                {
                    "removed": round(removed, 6),
                    "before_obstruction": round(before, 6),
                    "after_obstruction": round(after, 6),
                },
                lambda event_id: self._hydrology.clear_gallery_rubble(
                    removed, causal_action_event_id=event_id
                ),
            )

        if action_type is PhysicalActionType.REINFORCE_BANK:
            before = state.burial_bank.sediment_mobility
            reduction = _clamp(0.50 * skill * effort)
            after = _clamp(before * (1.0 - reduction))
            outcome = (
                PhysicalActionOutcome.SUCCEEDED
                if before - after >= 0.01
                else PhysicalActionOutcome.BLOCKED
            )
            return _MutationPlan(
                "RIVERBANK_REINFORCED",
                outcome,
                "The visible riverbank was reinforced against further scour."
                if outcome is PhysicalActionOutcome.SUCCEEDED
                else "The reinforcement produced no meaningful change.",
                {
                    "fractional_reduction": round(reduction, 6),
                    "before_sediment_mobility": round(before, 6),
                    "after_sediment_mobility": round(after, 6),
                },
                lambda event_id: self._hydrology.reinforce_bank(
                    reduction, causal_action_event_id=event_id
                ),
            )

        raise ValueError(f"unsupported physical mutation: {action_type.value}")

    @staticmethod
    def _movement_outcome(requested: float, applied: float) -> PhysicalActionOutcome:
        if abs(applied) < 0.01:
            return PhysicalActionOutcome.BLOCKED
        if abs(applied) + 0.005 >= abs(requested):
            return PhysicalActionOutcome.SUCCEEDED
        return PhysicalActionOutcome.PARTIAL

    def _observation_payload(
        self,
        subject: LocalSubjectState,
        action_type: PhysicalActionType,
        target_ref: str,
    ) -> tuple[dict[str, str], str, str]:
        state = self._hydrology.state
        faculties = set(subject.faculties)

        if action_type is PhysicalActionType.INSPECT_GATE:
            position = self._band(
                state.gate.sluice_position,
                ((0.04, "sealed"), (0.25, "slightly_raised"), (0.65, "partly_open")),
                "wide_open",
            )
            debris = self._band(
                state.gate.debris_load,
                ((0.10, "clear"), (0.35, "light"), (0.65, "moderate")),
                "heavy",
            )
            condition = self._band(
                state.gate.structure_integrity,
                ((0.25, "fragile"), (0.60, "worn"), (0.88, "weathered")),
                "sound",
            )
            flow = self._flow_band(self._gate_discharge())
            cues = {
                "visible_sluice": position,
                "visible_debris": debris,
                "mechanism_condition": condition,
                "outflow_cue": flow,
            }
            certainty = "direct_engineering_inspection" if "engineering" in faculties else "direct_but_coarse"
            summary = (
                f"The sluice looks {position.replace('_', ' ')}; debris looks {debris}; "
                f"the mechanism looks {condition}; the outflow feels {flow.replace('_', ' ')}."
            )
            return cues, summary, certainty

        if action_type is PhysicalActionType.INSPECT_WATER_STATE:
            node = state.nodes[target_ref]
            level = self._band(
                node.level,
                ((0.20, "very_low"), (0.42, "low"), (0.82, "normal"), (0.96, "high")),
                "brimming",
            )
            current = self._flow_band(self._node_current(target_ref))
            cues = {"visible_level": level, "felt_current": current}
            if "native_water_memory" in faculties:
                cues["remembered_signature"] = (
                    "familiar" if "native_nereid" in node.water_tags else "not_native"
                )
            certainty = "direct_water_sense" if "water_sense" in faculties else "surface_estimate"
            summary = (
                f"The local water appears {level.replace('_', ' ')} with a "
                f"{current.replace('_', ' ')} current."
            )
            if "remembered_signature" in cues:
                summary += (
                    " Its character feels familiar."
                    if cues["remembered_signature"] == "familiar"
                    else " It does not feel like the remembered native water."
                )
            return cues, summary, certainty

        if action_type is PhysicalActionType.SURVEY_GALLERY:
            rubble = self._band(
                state.gallery.rubble_obstruction,
                ((0.10, "clear"), (0.35, "scattered"), (0.65, "difficult")),
                "heavy_blockage",
            )
            wetness = self._band(
                state.nodes[GALLERY_TARGET].level,
                ((0.08, "mostly_dry"), (0.20, "damp"), (0.45, "wet")),
                "flooded",
            )
            route = {
                "blocked_by_rubble": "blocked",
                "passable": "appears_passable",
                "wet_risky": "appears_hazardous",
                "flooded_impassable": "appears_impassable",
            }[state.gallery.route_state.value]
            cues = {"visible_rubble": rubble, "visible_wetness": wetness, "route_impression": route}
            certainty = "direct_engineering_survey" if "engineering" in faculties else "direct_but_coarse"
            summary = (
                f"The gallery shows {rubble.replace('_', ' ')} and is {wetness.replace('_', ' ')}; "
                f"the route {route.replace('_', ' ')}."
            )
            return cues, summary, certainty

        if action_type is PhysicalActionType.INSPECT_BANK:
            flow = self._gate_discharge()
            mobility = state.burial_bank.sediment_mobility
            exposure = state.burial_bank.exposure_fraction
            stress = flow * mobility
            stability = self._band(
                stress,
                ((0.025, "stable"), (0.055, "softening"), (0.090, "actively_eroding")),
                "failing",
            )
            if exposure <= 0.0:
                surface = "ordinary_scoured_bank" if stress > 0.04 else "ordinary_bank"
            elif exposure < 0.35:
                surface = "unidentified_fragments_visible"
            else:
                surface = "subsurface_material_exposed"
            cues = {"visible_stability": stability, "surface_signs": surface}
            certainty = "direct_engineering_inspection" if "engineering" in faculties else "direct_but_coarse"
            summary = (
                f"The bank looks {stability.replace('_', ' ')} and shows "
                f"{surface.replace('_', ' ')}."
            )
            return cues, summary, certainty

        raise ValueError(f"unsupported inspection: {action_type.value}")

    def _gate_discharge(self) -> float:
        if self._hydrology.last_trace is not None:
            return self._hydrology.last_trace.edge_flows.get("gate_discharge", 0.0)
        return 0.10 * self._hydrology.state.gate.effective_opening

    def _node_current(self, node_id: str) -> float:
        trace = self._hydrology.last_trace
        if trace is None:
            return 0.0
        total = 0.0
        for edge in self._hydrology.state.edges:
            if edge.source_id == node_id or edge.target_id == node_id:
                total += trace.edge_flows.get(edge.edge_id, 0.0)
        if node_id == "underpeak_gate_forebay":
            total += trace.edge_flows.get("gate_discharge", 0.0)
            total += trace.edge_flows.get("forebay_to_gallery_backwater", 0.0)
        elif node_id == "underpeak_gallery_sump":
            total += trace.edge_flows.get("forebay_to_gallery_backwater", 0.0)
            total += trace.edge_flows.get("upper_to_gallery_flood", 0.0)
            total += trace.edge_flows.get("gallery_drain", 0.0)
        elif node_id == "underpeak_upper_reach":
            total += trace.edge_flows.get("gate_discharge", 0.0)
            total += trace.edge_flows.get("gallery_drain", 0.0)
        return total

    @staticmethod
    def _flow_band(flow: float) -> str:
        if flow < 0.005:
            return "almost_still"
        if flow < 0.020:
            return "weak"
        if flow < 0.055:
            return "steady"
        if flow < 0.100:
            return "strong"
        return "violent"

    @staticmethod
    def _band(
        value: float,
        thresholds: tuple[tuple[float, str], ...],
        final: str,
    ) -> str:
        for threshold, label in thresholds:
            if value < threshold:
                return label
        return final

    def _observation_parent_event_ids(self, target_ref: str) -> tuple[int, ...]:
        state = self._hydrology.state
        candidates: list[int | None] = []
        if target_ref == GATE_TARGET or target_ref == "underpeak_gate_forebay":
            candidates.append(state.gate.last_change_event_id)
        if target_ref == GALLERY_TARGET:
            candidates.append(state.gallery.last_change_event_id)
        if target_ref == BANK_TARGET or target_ref == "underpeak_upper_reach":
            candidates.append(state.burial_bank.last_change_event_id)
        if self._hydrology.last_trace is not None:
            candidates.extend(self._hydrology.last_trace.emitted_event_ids)
        return tuple(sorted({item for item in candidates if item is not None}))

    def _target_site(self, action_type: PhysicalActionType, target_ref: str) -> str:
        if action_type in {
            PhysicalActionType.INSPECT_GATE,
            PhysicalActionType.ADJUST_SLUICE,
            PhysicalActionType.CLEAR_GATE_DEBRIS,
            PhysicalActionType.FORCE_SLUICE,
            PhysicalActionType.REPAIR_GATE,
            PhysicalActionType.SHIFT_LOCAL_SILT,
        }:
            if target_ref != GATE_TARGET:
                raise ValueError("this action requires the ancient river gate target")
            return GATE_SITE
        if action_type is PhysicalActionType.INSPECT_WATER_STATE:
            if target_ref not in self._hydrology.state.nodes:
                raise ValueError("water inspection requires a known local water node")
            return target_ref
        if action_type in {
            PhysicalActionType.SURVEY_GALLERY,
            PhysicalActionType.CLEAR_GALLERY_RUBBLE,
        }:
            if target_ref != GALLERY_TARGET:
                raise ValueError("this action requires the old gallery target")
            return GALLERY_TARGET
        if action_type in {PhysicalActionType.INSPECT_BANK, PhysicalActionType.REINFORCE_BANK}:
            if target_ref != BANK_TARGET:
                raise ValueError("this action requires the visible upper-reach bank target")
            return "underpeak_upper_reach"
        raise ValueError(f"unsupported physical action: {action_type.value}")

    @staticmethod
    def _site_region(site_id: str) -> str:
        if site_id in {"lake_mirror", "lake_whisper", "northwood_junction"}:
            return "northwood"
        return "underpeak"


def create_silver_thread_affordance_bridge(
    world: WorldState,
    ledger: EventLedger,
    hydrology: HydrologyProcess,
    *,
    advance_time: Callable[[int], None] | None = None,
) -> PhysicalAffordanceBridge:
    """Create the production bridge with conservative seed-time local agency.

    Registering a body does not wake a mind or make it act. Nereid can reach
    the upstream forebay through already-connected northern water but cannot
    cross the Gate. Trade has an upstream field team, not magical access to the
    sealed gallery or hidden bank.
    """

    bridge = PhysicalAffordanceBridge(
        world,
        ledger,
        hydrology,
        advance_time=advance_time,
    )
    bridge.register_subject(
        LocalSubjectState(
            subject_id="nereid_01",
            subject_kind="lesser_water_entity",
            present_site_ids=("northwood_junction", GATE_SITE),
            faculties=("water_sense", "native_water_memory"),
            capability_levels={
                PhysicalActionType.INSPECT_GATE.value: 0.70,
                PhysicalActionType.INSPECT_WATER_STATE.value: 1.00,
                PhysicalActionType.SHIFT_LOCAL_SILT.value: 0.78,
            },
            resources={"effort": 4.0},
        )
    )
    bridge.register_subject(
        LocalSubjectState(
            subject_id="trade_house_01",
            subject_kind="institutional_field_team",
            present_site_ids=(GATE_SITE,),
            faculties=("sight", "engineering"),
            capability_levels={
                PhysicalActionType.INSPECT_GATE.value: 0.92,
                PhysicalActionType.INSPECT_WATER_STATE.value: 0.65,
                PhysicalActionType.ADJUST_SLUICE.value: 0.88,
                PhysicalActionType.CLEAR_GATE_DEBRIS.value: 0.82,
                PhysicalActionType.FORCE_SLUICE.value: 0.65,
                PhysicalActionType.REPAIR_GATE.value: 0.80,
            },
            resources={"effort": 8.0, "materials": 4.0},
        )
    )
    return bridge
