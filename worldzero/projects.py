from __future__ import annotations

import json
from dataclasses import dataclass, replace
from enum import Enum
from pathlib import Path
from typing import Callable, Iterable


class ProjectStatus(str, Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    ABANDONED = "abandoned"


class AttemptOutcome(str, Enum):
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    BLOCKED = "blocked"
    PARTIAL = "partial"
    INCONCLUSIVE = "inconclusive"


def _clean_text(value: str, label: str) -> str:
    cleaned = " ".join(value.split())
    if not cleaned:
        raise ValueError(f"{label} cannot be empty")
    return cleaned


def _unique(values: Iterable[str]) -> tuple[str, ...]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        cleaned = _clean_text(value, "project reference")
        if cleaned in seen:
            continue
        seen.add(cleaned)
        result.append(cleaned)
    return tuple(result)


@dataclass(frozen=True)
class ProjectAttempt:
    attempt_id: int
    game_minute: int
    strategy: str
    decision_ref: str
    intent_refs: tuple[str, ...]
    resolution_refs: tuple[str, ...]
    outcome: AttemptOutcome
    result_event_ids: tuple[int, ...] = ()
    evidence_refs: tuple[str, ...] = ()

    @property
    def ref(self) -> str:
        return f"project_attempt:{self.attempt_id}"

    def as_dict(self) -> dict:
        return {
            "attempt_id": self.attempt_id,
            "ref": self.ref,
            "game_minute": self.game_minute,
            "strategy": self.strategy,
            "decision_ref": self.decision_ref,
            "intent_refs": list(self.intent_refs),
            "resolution_refs": list(self.resolution_refs),
            "outcome": self.outcome.value,
            "result_event_ids": list(self.result_event_ids),
            "evidence_refs": list(self.evidence_refs),
        }


@dataclass(frozen=True)
class PersistentProject:
    project_id: str
    owner_id: str
    desire: str
    motivation: str
    status: ProjectStatus
    commitment: float
    known_constraints: tuple[str, ...]
    hypotheses: tuple[str, ...]
    current_strategy: str
    attempt_history: tuple[ProjectAttempt, ...]
    subjective_evidence_refs: tuple[str, ...]
    created_minute: int
    last_reconsidered_minute: int
    next_review_minute: int
    revision: int = 1
    completion_rule_id: str | None = None

    @property
    def ref(self) -> str:
        return f"project:{self.project_id}"

    def as_dict(self) -> dict:
        return {
            "project_id": self.project_id,
            "ref": self.ref,
            "owner_id": self.owner_id,
            "desire": self.desire,
            "motivation": self.motivation,
            "status": self.status.value,
            "commitment": self.commitment,
            "known_constraints": list(self.known_constraints),
            "hypotheses": list(self.hypotheses),
            "current_strategy": self.current_strategy,
            "attempt_history": [attempt.as_dict() for attempt in self.attempt_history],
            "subjective_evidence_refs": list(self.subjective_evidence_refs),
            "created_minute": self.created_minute,
            "last_reconsidered_minute": self.last_reconsidered_minute,
            "next_review_minute": self.next_review_minute,
            "revision": self.revision,
            "completion_rule_id": self.completion_rule_id,
        }


class PersistentProjectStore:
    """Durable unfinished intentions. There is deliberately no quest-step graph here."""

    def __init__(self) -> None:
        self._projects: dict[str, PersistentProject] = {}
        self._attempt_sequence = 0

    @property
    def projects(self) -> tuple[PersistentProject, ...]:
        return tuple(self._projects[key] for key in sorted(self._projects))

    def get(self, project_id: str) -> PersistentProject:
        try:
            return self._projects[project_id]
        except KeyError as exc:
            raise KeyError(f"Unknown project: {project_id}") from exc

    def for_owner(self, owner_id: str) -> tuple[PersistentProject, ...]:
        return tuple(project for project in self.projects if project.owner_id == owner_id)

    def create(
        self,
        *,
        project_id: str,
        owner_id: str,
        desire: str,
        motivation: str,
        commitment: float,
        known_constraints: Iterable[str] = (),
        hypotheses: Iterable[str] = (),
        current_strategy: str,
        subjective_evidence_refs: Iterable[str] = (),
        created_minute: int,
        next_review_minute: int | None = None,
    ) -> PersistentProject:
        project_id = _clean_text(project_id, "project_id")
        owner_id = _clean_text(owner_id, "owner_id")
        if project_id in self._projects:
            raise ValueError(f"Project already exists: {project_id}")
        if not 0.0 <= commitment <= 1.0:
            raise ValueError("commitment must be in [0, 1]")
        if created_minute < 0:
            raise ValueError("created_minute cannot be negative")
        review_minute = created_minute if next_review_minute is None else next_review_minute
        if review_minute < created_minute:
            raise ValueError("next review cannot precede project creation")

        project = PersistentProject(
            project_id=project_id,
            owner_id=owner_id,
            desire=_clean_text(desire, "desire"),
            motivation=_clean_text(motivation, "motivation"),
            status=ProjectStatus.ACTIVE,
            commitment=round(commitment, 6),
            known_constraints=_unique(known_constraints),
            hypotheses=_unique(hypotheses),
            current_strategy=_clean_text(current_strategy, "current_strategy"),
            attempt_history=(),
            subjective_evidence_refs=_unique(subjective_evidence_refs),
            created_minute=created_minute,
            last_reconsidered_minute=created_minute,
            next_review_minute=review_minute,
        )
        self._projects[project_id] = project
        return project

    def reconsider(
        self,
        project_id: str,
        *,
        game_minute: int,
        current_strategy: str,
        next_review_minute: int,
        known_constraints_add: Iterable[str] = (),
        hypotheses: Iterable[str] | None = None,
        subjective_evidence_add: Iterable[str] = (),
    ) -> PersistentProject:
        project = self._require_active(project_id)
        if game_minute < project.last_reconsidered_minute:
            raise ValueError("project reconsideration cannot move backward in time")
        if next_review_minute <= game_minute:
            raise ValueError("an active project must schedule its next review in the future")

        revised = replace(
            project,
            known_constraints=_unique((*project.known_constraints, *known_constraints_add)),
            hypotheses=project.hypotheses if hypotheses is None else _unique(hypotheses),
            current_strategy=_clean_text(current_strategy, "current_strategy"),
            subjective_evidence_refs=_unique(
                (*project.subjective_evidence_refs, *subjective_evidence_add)
            ),
            last_reconsidered_minute=game_minute,
            next_review_minute=next_review_minute,
            revision=project.revision + 1,
        )
        self._projects[project_id] = revised
        return revised

    def record_attempt(
        self,
        project_id: str,
        *,
        game_minute: int,
        strategy: str,
        decision_ref: str,
        intent_refs: Iterable[str],
        resolution_refs: Iterable[str],
        outcome: AttemptOutcome,
        result_event_ids: Iterable[int] = (),
        evidence_refs: Iterable[str] = (),
    ) -> ProjectAttempt:
        project = self._require_active(project_id)
        if game_minute < project.created_minute:
            raise ValueError("project attempt cannot precede project creation")
        event_ids = tuple(sorted(set(result_event_ids)))
        if any(event_id <= 0 for event_id in event_ids):
            raise ValueError("result event ids must be positive")

        self._attempt_sequence += 1
        attempt = ProjectAttempt(
            attempt_id=self._attempt_sequence,
            game_minute=game_minute,
            strategy=_clean_text(strategy, "attempt strategy"),
            decision_ref=_clean_text(decision_ref, "decision_ref"),
            intent_refs=_unique(intent_refs),
            resolution_refs=_unique(resolution_refs),
            outcome=outcome,
            result_event_ids=event_ids,
            evidence_refs=_unique(evidence_refs),
        )
        revised = replace(
            project,
            attempt_history=project.attempt_history + (attempt,),
            subjective_evidence_refs=_unique(
                (*project.subjective_evidence_refs, attempt.ref, *attempt.evidence_refs)
            ),
            revision=project.revision + 1,
        )
        self._projects[project_id] = revised
        return attempt

    def pause(self, project_id: str) -> PersistentProject:
        project = self._require_active(project_id)
        revised = replace(project, status=ProjectStatus.PAUSED, revision=project.revision + 1)
        self._projects[project_id] = revised
        return revised

    def resume(self, project_id: str, *, next_review_minute: int) -> PersistentProject:
        project = self.get(project_id)
        if project.status is not ProjectStatus.PAUSED:
            raise ValueError("only paused projects can resume")
        if next_review_minute < project.last_reconsidered_minute:
            raise ValueError("next review cannot move backward in time")
        revised = replace(
            project,
            status=ProjectStatus.ACTIVE,
            next_review_minute=next_review_minute,
            revision=project.revision + 1,
        )
        self._projects[project_id] = revised
        return revised

    def abandon(self, project_id: str) -> PersistentProject:
        project = self.get(project_id)
        if project.status in {ProjectStatus.COMPLETED, ProjectStatus.ABANDONED}:
            raise ValueError("terminal project cannot be abandoned again")
        revised = replace(project, status=ProjectStatus.ABANDONED, revision=project.revision + 1)
        self._projects[project_id] = revised
        return revised

    def complete_if(
        self,
        project_id: str,
        *,
        completion_rule_id: str,
        validator: Callable[[PersistentProject], bool],
    ) -> tuple[bool, PersistentProject]:
        project = self._require_active(project_id)
        rule_id = _clean_text(completion_rule_id, "completion_rule_id")
        if not bool(validator(project)):
            return False, project
        revised = replace(
            project,
            status=ProjectStatus.COMPLETED,
            completion_rule_id=rule_id,
            revision=project.revision + 1,
        )
        self._projects[project_id] = revised
        return True, revised

    def export_jsonl(self, path: str | Path) -> None:
        destination = Path(path)
        with destination.open("w", encoding="utf-8") as handle:
            for project in self.projects:
                handle.write(json.dumps(project.as_dict(), ensure_ascii=False, sort_keys=True) + "\n")

    def _require_active(self, project_id: str) -> PersistentProject:
        project = self.get(project_id)
        if project.status is not ProjectStatus.ACTIVE:
            raise ValueError(f"Project {project_id} is not active")
        return project


def seed_silver_thread_projects(game_minute: int = 0) -> PersistentProjectStore:
    """Seed unfinished business before Arra performs the first player-controlled action."""
    store = PersistentProjectStore()
    store.create(
        project_id="nereid_return_underpeak",
        owner_id="nereid_01",
        desire="Regain meaningful water connectivity with native waters in Underpeak.",
        motivation="Return to waters remembered as home without assuming a mortal helper exists.",
        commitment=0.92,
        known_constraints=("native_underpeak_waters_are_currently_cut_off",),
        hypotheses=("a_weaker_restored_current_may_be_enough",),
        current_strategy="seek a water-connected route toward the remembered Underpeak signature",
        subjective_evidence_refs=(
            "memory:nereid_01:native_underpeak_signature",
            "memory:nereid_01:current_separation",
        ),
        created_minute=game_minute,
        next_review_minute=game_minute + 6 * 24 * 60,
    )
    store.create(
        project_id="trade_house_underpeak_route",
        owner_id="trade_house_01",
        desire="Establish a viable northern Underpeak route if one can be made profitable.",
        motivation="Create a durable commercial passage rather than serve another subject's project.",
        commitment=0.68,
        known_constraints=("reported_old_access_is_not_currently_verified",),
        hypotheses=("an_old_subterranean_access_route_may_still_exist",),
        current_strategy="verify old reports of subterranean access before committing resources",
        subjective_evidence_refs=("record:trade_house_01:old_underpeak_route_report",),
        created_minute=game_minute,
        next_review_minute=game_minute + 8 * 24 * 60,
    )
    return store
