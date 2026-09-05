from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Protocol

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

    def __init__(
        self,
        projects: PersistentProjectStore,
        trace: CausalTrace,
        *,
        clock: Callable[[], int] | None = None,
    ) -> None:
        self.projects = projects
        self.trace = trace
        self._minds: dict[str, ProjectMind] = {}
        self._resolvers: dict[str, IntentResolver] = {}
        self._review_preparers: dict[str, Callable[[str, int], None]] = {}
        self._errors: list[str] = []
        # Optional authoritative time reader, not another clock. Legacy trials
        # continue to use their supplied tick minute and unchanged trace shape.
        self._clock = clock
        self._ticking = False
        self._retry_not_before: dict[str, int] = {}

    @property
    def errors(self) -> tuple[str, ...]:
        return tuple(self._errors)

    def register_mind(self, owner_id: str, mind: ProjectMind) -> None:
        self._minds[owner_id] = mind

    def register_resolver(self, intent_type: str, resolver: IntentResolver) -> None:
        self._resolvers[intent_type] = resolver

    def register_review_preparer(
        self, owner_id: str, prepare: Callable[[str, int], None],
    ) -> None:
        """Trusted evidence binding before snapshot capture; never a model callback."""
        self._review_preparers[owner_id] = prepare

    @property
    def next_review_minute(self) -> int | None:
        return min(
            (
                self._due_minute(project)
                for project in self.projects.projects
                if project.status is ProjectStatus.ACTIVE and project.owner_id in self._minds
            ),
            default=None,
        )

    def _due_minute(self, project: PersistentProject) -> int:
        return max(project.next_review_minute, self._retry_not_before.get(project.project_id, 0))

    def _now(self, tick_minute: int) -> int:
        return tick_minute if self._clock is None else self._clock()

    def tick(self, game_minute: int) -> tuple[ProjectReviewResult, ...]:
        if self._clock is None:
            return self._tick(game_minute)
        if self._ticking:
            return ()
        self._ticking = True
        try:
            return self._tick(game_minute)
        finally:
            self._ticking = False

    def _tick(self, game_minute: int) -> tuple[ProjectReviewResult, ...]:
        results: list[ProjectReviewResult] = []
        projects = self.projects.projects
        if self._clock is not None:
            projects = tuple(sorted(projects, key=lambda p: (self._due_minute(p), p.project_id)))
        for candidate in projects:
            project = candidate if self._clock is None else self.projects.get(candidate.project_id)
            review_minute = self._now(game_minute)
            if project.status is not ProjectStatus.ACTIVE:
                continue
            if self._due_minute(project) > review_minute:
                continue
            mind = self._minds.get(project.owner_id)
            if mind is None:
                continue
            try:
                result = self._review(project.project_id, review_minute, mind)
            except Exception as exc:
                self._errors.append(
                    f"minute {review_minute} / {project.project_id}: {type(exc).__name__}: {exc}"
                )
                result = None
            if result is not None:
                self._retry_not_before.pop(project.project_id, None)
                results.append(result)
            elif self._clock is not None:
                # None/failed cognition cannot spin at one due minute. This is
                # retry metadata only; no invented decision, belief or attempt.
                self._retry_not_before[project.project_id] = self._now(game_minute) + 360
        return tuple(results)

    def _review(
        self,
        project_id: str,
        game_minute: int,
        mind: ProjectMind,
    ) -> ProjectReviewResult | None:
        project_before = self.projects.get(project_id)
        prepare = self._review_preparers.get(project_before.owner_id)
        if prepare is not None:
            prepare(project_id, game_minute)
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
        if self._clock is not None and (
            isinstance(decision.next_review_minute, bool)
            or not isinstance(decision.next_review_minute, int)
        ):
            raise ValueError("project review time must be an integer minute")
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
                    game_minute=self._now(game_minute),
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
                game_minute=self._now(game_minute),
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
                game_minute=self._now(game_minute),
                strategy=decision.strategy,
                decision_ref=decision_trace.ref,
                intent_refs=intent_refs,
                resolution_refs=resolution_refs,
                outcome=outcome,
                result_event_ids=result_event_ids,
                evidence_refs=resolution_refs,
            )
            attempt_ref = attempt.ref

        completed_minute = self._now(game_minute)
        project_after = self.projects.get(project_id)
        if (
            self._clock is not None
            and project_after.status is ProjectStatus.ACTIVE
            and project_after.next_review_minute <= completed_minute
        ):
            # A long action can overrun the requested review deadline. Preserve
            # the requested interval and original thought time, not a new thought.
            self.projects.reconsider(
                project_id,
                game_minute=game_minute,
                current_strategy=project_after.current_strategy,
                next_review_minute=completed_minute + decision.next_review_minute - game_minute,
            )

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
