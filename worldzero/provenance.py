from __future__ import annotations

import json
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Iterable

from .ledger import EventLedger
from .projects import PersistentProject


def _json(value: dict[str, Any]) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


class CausalEdgeKind(str, Enum):
    PROJECT_CONTEXT = "project_context"
    DECISION_INPUT = "decision_input"
    AUTHORED_INTENT = "authored_intent"
    ACTION_RESOLUTION = "action_resolution"
    OBJECTIVE_RESULT = "objective_result"


@dataclass(frozen=True)
class DecisionTrace:
    decision_id: int
    game_minute: int
    subject_id: str
    project_ref: str
    project_revision: int
    subjective_evidence_refs: tuple[str, ...]

    @property
    def ref(self) -> str:
        return f"decision:{self.decision_id}"

    def as_dict(self) -> dict:
        return {
            "record_type": "decision",
            "decision_id": self.decision_id,
            "ref": self.ref,
            "game_minute": self.game_minute,
            "subject_id": self.subject_id,
            "project_ref": self.project_ref,
            "project_revision": self.project_revision,
            "subjective_evidence_refs": list(self.subjective_evidence_refs),
        }


@dataclass(frozen=True)
class IntentTrace:
    intent_id: int
    game_minute: int
    decision_ref: str
    intent_type: str
    target_refs: tuple[str, ...]
    params_json: str

    @property
    def ref(self) -> str:
        return f"intent:{self.intent_id}"

    @property
    def params(self) -> dict[str, Any]:
        return json.loads(self.params_json)

    def as_dict(self) -> dict:
        return {
            "record_type": "intent",
            "intent_id": self.intent_id,
            "ref": self.ref,
            "game_minute": self.game_minute,
            "decision_ref": self.decision_ref,
            "intent_type": self.intent_type,
            "target_refs": list(self.target_refs),
            "params": self.params,
        }


@dataclass(frozen=True)
class ResolutionTrace:
    resolution_id: int
    game_minute: int
    intent_ref: str
    resolver_rule_id: str
    ok: bool
    outcome: str
    message: str
    result_event_ids: tuple[int, ...]

    @property
    def ref(self) -> str:
        return f"resolution:{self.resolution_id}"

    def as_dict(self) -> dict:
        return {
            "record_type": "resolution",
            "resolution_id": self.resolution_id,
            "ref": self.ref,
            "game_minute": self.game_minute,
            "intent_ref": self.intent_ref,
            "resolver_rule_id": self.resolver_rule_id,
            "ok": self.ok,
            "outcome": self.outcome,
            "message": self.message,
            "result_event_ids": list(self.result_event_ids),
        }


@dataclass(frozen=True)
class CausalEdge:
    source_ref: str
    target_ref: str
    kind: CausalEdgeKind

    def as_dict(self) -> dict:
        return {
            "source_ref": self.source_ref,
            "target_ref": self.target_ref,
            "kind": self.kind.value,
        }


class CausalTrace:
    """Forensic braid around the Ledger; it never substitutes an agent explanation for truth."""

    def __init__(self, ledger: EventLedger | None = None) -> None:
        self.ledger = ledger
        self._decisions: list[DecisionTrace] = []
        self._intents: list[IntentTrace] = []
        self._resolutions: list[ResolutionTrace] = []
        self._decision_by_ref: dict[str, DecisionTrace] = {}
        self._intent_by_ref: dict[str, IntentTrace] = {}

    @property
    def decisions(self) -> tuple[DecisionTrace, ...]:
        return tuple(self._decisions)

    @property
    def intents(self) -> tuple[IntentTrace, ...]:
        return tuple(self._intents)

    @property
    def resolutions(self) -> tuple[ResolutionTrace, ...]:
        return tuple(self._resolutions)

    def record_decision(
        self,
        *,
        project: PersistentProject,
        game_minute: int,
        subjective_evidence_refs: Iterable[str],
    ) -> DecisionTrace:
        evidence_refs = tuple(dict.fromkeys(subjective_evidence_refs))
        unavailable = set(evidence_refs) - set(project.subjective_evidence_refs)
        if unavailable:
            raise ValueError(
                "decision cited evidence outside the project's subjective state: "
                + ", ".join(sorted(unavailable))
            )
        decision = DecisionTrace(
            decision_id=len(self._decisions) + 1,
            game_minute=game_minute,
            subject_id=project.owner_id,
            project_ref=project.ref,
            project_revision=project.revision,
            subjective_evidence_refs=evidence_refs,
        )
        self._decisions.append(decision)
        self._decision_by_ref[decision.ref] = decision
        return decision

    def record_intent(
        self,
        *,
        decision_ref: str,
        intent_type: str,
        target_refs: Iterable[str] = (),
        params: dict[str, Any] | None = None,
    ) -> IntentTrace:
        if decision_ref not in self._decision_by_ref:
            raise ValueError(f"Unknown decision ref: {decision_ref}")
        decision = self._decision_by_ref[decision_ref]
        cleaned_type = " ".join(intent_type.split())
        if not cleaned_type:
            raise ValueError("intent_type cannot be empty")
        intent = IntentTrace(
            intent_id=len(self._intents) + 1,
            game_minute=decision.game_minute,
            decision_ref=decision_ref,
            intent_type=cleaned_type,
            target_refs=tuple(dict.fromkeys(target_refs)),
            params_json=_json(params or {}),
        )
        self._intents.append(intent)
        self._intent_by_ref[intent.ref] = intent
        return intent

    def record_resolution(
        self,
        *,
        intent_ref: str,
        game_minute: int,
        resolver_rule_id: str,
        ok: bool,
        outcome: str,
        message: str,
        result_event_ids: Iterable[int] = (),
    ) -> ResolutionTrace:
        if intent_ref not in self._intent_by_ref:
            raise ValueError(f"Unknown intent ref: {intent_ref}")
        rule_id = " ".join(resolver_rule_id.split())
        if not rule_id:
            raise ValueError("resolver_rule_id cannot be empty")
        event_ids = tuple(sorted(set(result_event_ids)))
        if any(event_id <= 0 for event_id in event_ids):
            raise ValueError("result event ids must be positive")
        if self.ledger is not None:
            known_event_ids = {event.event_id for event in self.ledger.events}
            missing = set(event_ids) - known_event_ids
            if missing:
                raise ValueError(
                    "resolution cited objective events absent from the attached Ledger: "
                    + ", ".join(str(event_id) for event_id in sorted(missing))
                )
        resolution = ResolutionTrace(
            resolution_id=len(self._resolutions) + 1,
            game_minute=game_minute,
            intent_ref=intent_ref,
            resolver_rule_id=rule_id,
            ok=bool(ok),
            outcome=" ".join(outcome.split()),
            message=" ".join(message.split()),
            result_event_ids=event_ids,
        )
        self._resolutions.append(resolution)
        return resolution

    def edges(self) -> tuple[CausalEdge, ...]:
        edges: list[CausalEdge] = []
        for decision in self._decisions:
            edges.append(
                CausalEdge(decision.project_ref, decision.ref, CausalEdgeKind.PROJECT_CONTEXT)
            )
            edges.extend(
                CausalEdge(ref, decision.ref, CausalEdgeKind.DECISION_INPUT)
                for ref in decision.subjective_evidence_refs
            )
        for intent in self._intents:
            edges.append(CausalEdge(intent.decision_ref, intent.ref, CausalEdgeKind.AUTHORED_INTENT))
        for resolution in self._resolutions:
            edges.append(
                CausalEdge(resolution.intent_ref, resolution.ref, CausalEdgeKind.ACTION_RESOLUTION)
            )
            edges.extend(
                CausalEdge(resolution.ref, f"event:{event_id}", CausalEdgeKind.OBJECTIVE_RESULT)
                for event_id in resolution.result_event_ids
            )
        return tuple(edges)

    def export_jsonl(self, path: str | Path) -> None:
        destination = Path(path)
        order = {"decision": 0, "intent": 1, "resolution": 2}
        records = [
            *self._decisions,
            *self._intents,
            *self._resolutions,
        ]
        records.sort(
            key=lambda record: (
                record.game_minute,
                order[record.as_dict()["record_type"]],
                record.as_dict().get("ref", ""),
            )
        )
        with destination.open("w", encoding="utf-8") as handle:
            for record in records:
                handle.write(json.dumps(record.as_dict(), ensure_ascii=False, sort_keys=True) + "\n")

    def export_graph_json(self, path: str | Path) -> None:
        destination = Path(path)
        payload = {"edges": [edge.as_dict() for edge in self.edges()]}
        destination.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
