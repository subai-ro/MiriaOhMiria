from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

from .projects import AttemptOutcome, PersistentProject, PersistentProjectStore, ProjectStatus
from .provenance import CausalTrace


@dataclass(frozen=True)
class ProjectIntent:
    intent_type: str
    target_refs: tuple[str, ...] = ()
    params: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ProjectDecision:
    strategy: str
    subjective_evidence_refs: tuple[str, ...]
    next_review_minute: int
    intents: tuple[ProjectIntent, ...] = ()
    known_constraints_add: tuple[str, ...] = ()
    hypotheses: tuple[str, ...] | None = None


@dataclass(frozen=True)
class ProjectPercept:
    project: PersistentProject
    available_evidence_refs: tuple[str, ...]
    game_minute: int


@dataclass(frozen=True)
class IntentResolution:
    ok: bool
    outcome: AttemptOutcome
    message: str
    result_event_ids: tuple[int, ...] = ()


@dataclass(frozen=True)
class ProjectReviewResult:
    project_id: str
    decision_ref: str | None
    intent_refs: tuple[str, ...]
    resolution_refs: tuple[str, ...]
    attempt_ref: str | None


class ProjectMind(Protocol):
    def decide(self, percept: ProjectPercept) -> ProjectDecision | None: ...


class IntentResolver(Protocol):
    rule_id: str

    def resolve(
        self,
        *,
        project: PersistentProject,
        intent: ProjectIntent,
        game_minute: int,
    ) -> IntentResolution: ...


class ProjectRuntime:
    """Schedules project reconsideration while leaving consequences to registered resolvers."""

    def __init__(self, projects: PersistentProjectStore, trace: CausalTrace) -> None:
        self.projects = projects
        self.trace = trace
        self._minds: dict[str, ProjectMind] = {}
        self._resolvers: dict[str, IntentResolver] = {}
        self._errors: list[str] = []

    @property
    def errors(self) -> tuple[str, ...]:
        return tuple(self._errors)

    def register_mind(self, owner_id: str, mind: ProjectMind) -> None:
        self._minds[owner_id] = mind

    def register_resolver(self, intent_type: str, resolver: IntentResolver) -> None:
        self._resolvers[intent_type] = resolver

    def tick(self, game_minute: int) -> tuple[ProjectReviewResult, ...]:
        results: list[ProjectReviewResult] = []
        for project in self.projects.projects:
            if project.status is not ProjectStatus.ACTIVE:
                continue
            if project.next_review_minute > game_minute:
                continue
            mind = self._minds.get(project.owner_id)
            if mind is None:
                continue
            try:
                result = self._review(project.project_id, game_minute, mind)
            except Exception as exc:
                self._errors.append(
                    f"minute {game_minute} / {project.project_id}: {type(exc).__name__}: {exc}"
                )
                continue
            if result is not None:
                results.append(result)
        return tuple(results)

    def _review(
        self,
        project_id: str,
        game_minute: int,
        mind: ProjectMind,
    ) -> ProjectReviewResult | None:
        project_before = self.projects.get(project_id)
        available_evidence = project_before.subjective_evidence_refs
        decision = mind.decide(
            ProjectPercept(
                project=project_before,
                available_evidence_refs=available_evidence,
                game_minute=game_minute,
            )
        )
        if decision is None:
            return None
        unavailable = set(decision.subjective_evidence_refs) - set(available_evidence)
        if unavailable:
            raise ValueError(
                "project mind cited unavailable evidence: " + ", ".join(sorted(unavailable))
            )
        if decision.next_review_minute <= game_minute:
            raise ValueError("project mind must schedule a future review")

        decision_trace = self.trace.record_decision(
            project=project_before,
            game_minute=game_minute,
            subjective_evidence_refs=decision.subjective_evidence_refs,
        )
        self.projects.reconsider(
            project_id,
            game_minute=game_minute,
            current_strategy=decision.strategy,
            next_review_minute=decision.next_review_minute,
            known_constraints_add=decision.known_constraints_add,
            hypotheses=decision.hypotheses,
        )

        intent_refs: list[str] = []
        resolution_refs: list[str] = []
        result_event_ids: list[int] = []
        outcomes: list[AttemptOutcome] = []
        for intent in decision.intents:
            intent_trace = self.trace.record_intent(
                decision_ref=decision_trace.ref,
                intent_type=intent.intent_type,
                target_refs=intent.target_refs,
                params=intent.params,
            )
            intent_refs.append(intent_trace.ref)
            resolver = self._resolvers.get(intent.intent_type)
            if resolver is None:
                resolution = IntentResolution(
                    ok=False,
                    outcome=AttemptOutcome.BLOCKED,
                    message=f"No authoritative resolver registered for {intent.intent_type}",
                )
                rule_id = "project_runtime.unsupported_intent"
            else:
                resolution = resolver.resolve(
                    project=self.projects.get(project_id),
                    intent=intent,
                    game_minute=game_minute,
                )
                rule_id = resolver.rule_id
            if (
                resolution.outcome is AttemptOutcome.SUCCEEDED
                and not resolution.ok
            ) or (
                resolution.outcome in {AttemptOutcome.FAILED, AttemptOutcome.BLOCKED}
                and resolution.ok
            ):
                raise ValueError(
                    "resolver result is internally inconsistent with its outcome"
                )
            resolution_trace = self.trace.record_resolution(
                intent_ref=intent_trace.ref,
                game_minute=game_minute,
                resolver_rule_id=rule_id,
                ok=resolution.ok,
                outcome=resolution.outcome.value,
                message=resolution.message,
                result_event_ids=resolution.result_event_ids,
            )
            resolution_refs.append(resolution_trace.ref)
            result_event_ids.extend(resolution.result_event_ids)
            outcomes.append(resolution.outcome)

        attempt_ref: str | None = None
        if intent_refs:
            outcome = self._aggregate_outcome(outcomes)
            attempt = self.projects.record_attempt(
                project_id,
                game_minute=game_minute,
                strategy=decision.strategy,
                decision_ref=decision_trace.ref,
                intent_refs=intent_refs,
                resolution_refs=resolution_refs,
                outcome=outcome,
                result_event_ids=result_event_ids,
                evidence_refs=resolution_refs,
            )
            attempt_ref = attempt.ref

        return ProjectReviewResult(
            project_id=project_id,
            decision_ref=decision_trace.ref,
            intent_refs=tuple(intent_refs),
            resolution_refs=tuple(resolution_refs),
            attempt_ref=attempt_ref,
        )

    @staticmethod
    def _aggregate_outcome(outcomes: list[AttemptOutcome]) -> AttemptOutcome:
        if not outcomes:
            return AttemptOutcome.INCONCLUSIVE
        if all(outcome is AttemptOutcome.SUCCEEDED for outcome in outcomes):
            return AttemptOutcome.SUCCEEDED
        if all(outcome is AttemptOutcome.BLOCKED for outcome in outcomes):
            return AttemptOutcome.BLOCKED
        if all(outcome in {AttemptOutcome.FAILED, AttemptOutcome.BLOCKED} for outcome in outcomes):
            return AttemptOutcome.FAILED
        if any(outcome in {AttemptOutcome.SUCCEEDED, AttemptOutcome.PARTIAL} for outcome in outcomes):
            return AttemptOutcome.PARTIAL
        return AttemptOutcome.INCONCLUSIVE
