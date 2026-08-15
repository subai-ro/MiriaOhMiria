from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from math import isclose, isfinite
from typing import Protocol

from .attention import AttentionDirective
from .beliefs import (
    BeliefType,
    BeliefUpdate,
    BeliefUpdateResult,
    DivineBelief,
    DivineBeliefStore,
    EvidenceDirection,
    project_confidence,
)
from .heralds import DivineKnowledge, DivineReport, HeraldSystem, ReportPriority
from .impressions import (
    DivineImpression,
    DivineImpressionStore,
    DivineImpressionUpdate,
    ImpressionResult,
)
from .ledger import EventLedger
from .models import WorldState
from .mysteries import (
    DivineMysteryStore,
    DivineVeiledHypothesis,
    VeiledHypothesisResult,
    VeiledHypothesisUpdate,
)
from .resonance import ContextualResonance, ContextualResonanceEngine


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, value))


class DivineActionType(str, Enum):
    SEND_OMEN = "send_omen"
    SEND_PROBE = "send_probe"
    MANIFEST_AREA_OMEN = "manifest_area_omen"
    GRANT_FAVOR = "grant_favor"
    IMPOSE_DREAD = "impose_dread"


class DivineCognitivePosture(str, Enum):
    """Dominant internal activity declared by the God, not an action gate."""

    SILENCE = "silence"
    OBSERVE = "observe"
    REMEMBER = "remember"
    INVESTIGATE = "investigate"
    JUDGE = "judge"


class DivineWorldPosture(str, Enum):
    """Classification of how far the God's proposed Will crosses into the world.

    D.1.3.2 derives this from manifestations instead of asking a neural God to
    redundantly label the same choice a second time.
    """

    HIDDEN = "hidden"
    OMEN = "omen"
    INTERVENTION = "intervention"


class DivineProbeStatus(str, Enum):
    AWAITING_RESPONSE = "awaiting_response"
    RESPONSE_PERCEIVED = "response_perceived"
    NO_EXPLICIT_RESPONSE_PERCEIVED = "no_explicit_response_perceived"

@dataclass(frozen=True)
class SpatialAttentionWeight:
    location_id: str
    weight: float


@dataclass(frozen=True)
class PersonalAttentionWeight:
    actor_id: str
    weight: float
    reason: str
    causal_event_ids: tuple[int, ...] = ()


@dataclass(frozen=True)
class ConsciousnessPlan:
    """Sum-safe neural expression of attention.

    `engagement` chooses how much active consciousness is used.  Of that used
    amount, `personal_fraction` goes to identified persons and the complement
    goes to space.  Target weights are relative within their channel, so no
    model has to perform fragile cross-array addition.
    """

    engagement: float
    personal_fraction: float
    spatial_targets: tuple[SpatialAttentionWeight, ...] = ()
    personal_targets: tuple[PersonalAttentionWeight, ...] = ()


@dataclass(frozen=True)
class DivineIntent:
    action_type: DivineActionType
    target_actor_id: str | None
    location_id: str
    significance: float
    message: str
    strength: float = 0.0
    reason: str = ""
    causal_event_ids: tuple[int, ...] = ()
    observation_minutes: int = 0


def derive_world_posture(intents: tuple[DivineIntent, ...]) -> DivineWorldPosture:
    """Name the external face of Will without changing the God's chosen acts.

    Classification uses proposed intents, even if an authoritative gateway
    later rejects one for insufficient Power, stale location, or another
    physical/epistemic constraint.
    """
    if any(
        intent.action_type in (DivineActionType.GRANT_FAVOR, DivineActionType.IMPOSE_DREAD)
        for intent in intents
    ):
        return DivineWorldPosture.INTERVENTION
    if intents:
        return DivineWorldPosture.OMEN
    return DivineWorldPosture.HIDDEN


@dataclass(frozen=True)
class DivineActionResult:
    action_type: DivineActionType
    ok: bool
    message: str
    event_id: int | None = None
    power_spent: float = 0.0
    probe_ref: str | None = None


@dataclass(frozen=True)
class ConsciousnessAllocationResult:
    """Validation result for one finite allocation of conscious attention."""

    ok: bool
    message: str
    spatial_focus: tuple[tuple[str, float], ...]
    personal_threads: tuple[AttentionDirective, ...]


@dataclass(frozen=True)
class DivineJudgmentResult:
    ok: bool
    message: str


@dataclass(frozen=True)
class DivineManifestation:
    manifestation_id: int
    game_minute: int
    source_entity_id: str
    target_actor_id: str | None
    location_id: str
    kind: str
    significance: float
    message: str
    witness_actor_ids: tuple[str, ...] = ()
    probe_ref: str | None = None


@dataclass(frozen=True)
class DivineManifestationMemory:
    """Safe first-person memory of a deity's own successful manifestation.

    This deliberately excludes objective witness lists and any later outcome.
    A deity is entitled to remember what it chose and successfully manifested,
    but not to learn who secretly witnessed it merely because the server does.
    """

    manifestation_id: int
    game_minute: int
    action_type: DivineActionType
    target_actor_id: str | None
    location_id: str
    significance: float
    message: str
    reason: str
    causal_event_ids: tuple[int, ...]
    manifestation_event_id: int
    power_spent: float
    probe_ref: str | None = None


@dataclass(frozen=True)
class DivineProbe:
    """A deity-authored interrogative manifestation remembered by its author."""

    probe_ref: str
    source_entity_id: str
    target_actor_id: str
    location_id: str
    message: str
    reason: str
    causal_event_ids: tuple[int, ...]
    manifestation_event_id: int
    opened_game_minute: int
    followup_game_minute: int


@dataclass(frozen=True)
class DivineProbeMemory:
    """Subjective status of one of the deity's own probes.

    A closed observation window says only that no *explicit linked response*
    was perceived through this channel. It never asserts that the mortal made
    no other reaction.
    """

    probe_ref: str
    target_actor_id: str
    location_id: str
    message: str
    reason: str
    causal_event_ids: tuple[int, ...]
    manifestation_event_id: int
    opened_game_minute: int
    followup_game_minute: int
    status: DivineProbeStatus
    response_knowledge_ids: tuple[int, ...] = ()


@dataclass
class DivinePowerAccount:
    entity_id: str
    current: float = 20.0
    maximum: float = 20.0
    regen_per_day: float = 4.0
    last_sync_minute: int = 0

    def sync(self, game_minute: int) -> None:
        if game_minute <= self.last_sync_minute:
            return
        elapsed = game_minute - self.last_sync_minute
        self.current = min(self.maximum, self.current + self.regen_per_day * elapsed / (24 * 60))
        self.last_sync_minute = game_minute

    def spend(self, amount: float, game_minute: int) -> bool:
        self.sync(game_minute)
        if amount < 0.0 or self.current + 1e-9 < amount:
            return False
        self.current -= amount
        return True


class DivineActionGateway:
    """Server-authoritative boundary between a God Brain and the objective world."""

    def __init__(self, world: WorldState, ledger: EventLedger, heralds: HeraldSystem) -> None:
        self.world = world
        self.ledger = ledger
        self.heralds = heralds
        self.accounts = {
            entity_id: DivinePowerAccount(entity_id=entity_id, last_sync_minute=world.game_minute)
            for entity_id in heralds.profiles
        }
        self._history: list[DivineActionResult] = []
        self._manifestations: list[DivineManifestation] = []
        self._manifestation_memories: list[tuple[str, DivineManifestationMemory]] = []
        self._probes: list[DivineProbe] = []

    @property
    def history(self) -> tuple[DivineActionResult, ...]:
        return tuple(self._history)

    @property
    def manifestations(self) -> tuple[DivineManifestation, ...]:
        return tuple(self._manifestations)

    @property
    def probes(self) -> tuple[DivineProbe, ...]:
        return tuple(self._probes)

    def power(self, entity_id: str) -> DivinePowerAccount:
        account = self.accounts[entity_id]
        account.sync(self.world.game_minute)
        return account

    def manifestations_for(self, actor_id: str) -> tuple[DivineManifestation, ...]:
        return tuple(
            item
            for item in self._manifestations
            if item.target_actor_id == actor_id or actor_id in item.witness_actor_ids
        )

    def manifestation_memories_for(
        self,
        entity_id: str,
        *,
        limit: int = 16,
    ) -> tuple[DivineManifestationMemory, ...]:
        if limit <= 0:
            return ()
        return tuple(
            memory
            for source_entity_id, memory in self._manifestation_memories
            if source_entity_id == entity_id
        )[-limit:]

    def probes_for(self, entity_id: str) -> tuple[DivineProbe, ...]:
        return tuple(item for item in self._probes if item.source_entity_id == entity_id)

    def allocate_consciousness(
        self,
        entity_id: str,
        focus_allocations: tuple[tuple[str, float], ...],
        attention_threads: tuple[AttentionDirective, ...],
    ) -> ConsciousnessAllocationResult:
        """Atomically validate and apply spatial + personal conscious attention.

        This consumes Presence focus budget, not Divine Power.  A brain may
        choose the allocation; the authoritative server only checks that it is
        possible and that a personal thread targets somebody the deity has
        actually identified before.
        """
        if entity_id not in self.accounts:
            return ConsciousnessAllocationResult(
                False,
                "unknown divine entity",
                (),
                (),
            )

        focus: dict[str, float] = {}
        for location_id, intensity in focus_allocations:
            if location_id in focus:
                return self._reject_consciousness("duplicate spatial focus target")
            if location_id not in self.world.regions and location_id not in self.world.objects:
                return self._reject_consciousness("unknown spatial focus target")
            if not 0.0 <= intensity <= 1.0:
                return self._reject_consciousness("spatial focus intensity must be in [0, 1]")
            if intensity > 0.0:
                focus[location_id] = intensity

        subjective_event_ids = self._subjective_event_ids(entity_id)
        known_actor_ids = {
            actor_id
            for item in self.heralds.knowledge_since(entity_id, 0)
            for actor_id in item.known_actor_ids
        }
        threads: list[AttentionDirective] = []
        seen_actors: set[str] = set()
        for directive in attention_threads:
            if directive.actor_id in seen_actors:
                return self._reject_consciousness("duplicate personal attention target")
            seen_actors.add(directive.actor_id)
            if directive.actor_id not in known_actor_ids:
                return self._reject_consciousness(
                    "personal attention target has never been identified in this deity's subjective knowledge"
                )
            if not 0.0 < directive.intensity <= 1.0:
                return self._reject_consciousness("personal attention intensity must be in (0, 1]")
            if any(event_id not in subjective_event_ids for event_id in directive.causal_event_ids):
                return self._reject_consciousness(
                    "personal attention evidence was never present in this deity's subjective knowledge"
                )
            threads.append(directive)

        total = sum(focus.values()) + sum(item.intensity for item in threads)
        budget = self.heralds.presence.profiles[entity_id].consciousness_budget
        if total > budget + 1e-9:
            return self._reject_consciousness(
                f"consciousness budget exceeded: {total:.2f} > {budget:.2f}"
            )

        # All validation happens before either field changes, so rejection is
        # atomic from the brain's point of view.
        self.heralds.presence.replace_focus(entity_id, focus)
        self.heralds.attention.replace(entity_id, tuple(threads), self.world.game_minute)
        return ConsciousnessAllocationResult(
            True,
            f"consciousness allocated: {total:.2f}/{budget:.2f}",
            tuple(sorted(focus.items())),
            tuple(sorted(threads, key=lambda item: item.actor_id)),
        )

    def execute(self, entity_id: str, intent: DivineIntent) -> DivineActionResult:
        result = self._execute(entity_id, intent)
        self._history.append(result)
        return result

    def reject(self, intent: DivineIntent, message: str) -> DivineActionResult:
        """Record a server-side refusal without attempting a world mutation."""
        result = self._reject(intent, message)
        self._history.append(result)
        return result

    def _execute(self, entity_id: str, intent: DivineIntent) -> DivineActionResult:
        if entity_id not in self.accounts:
            return self._reject(intent, "unknown divine entity")
        if not 0.0 <= intent.significance <= 1.0:
            return self._reject(intent, "significance must be in [0, 1]")
        if not intent.message.strip() or len(intent.message) > 500:
            return self._reject(intent, "manifestation message must contain 1..500 characters")

        subjective_event_ids = self._subjective_event_ids(entity_id)
        if any(event_id not in subjective_event_ids for event_id in intent.causal_event_ids):
            return self._reject(intent, "causal evidence was never present in this deity's subjective knowledge")

        if intent.action_type is not DivineActionType.SEND_PROBE and intent.observation_minutes != 0:
            return self._reject(intent, "only divine probes take an observation window")

        # Area omens are a distinct faculty: the God may touch a place it has
        # actually perceived without pretending an unidentified mortal is a
        # target. The server distributes the manifestation to whoever is
        # objectively there, without revealing those identities back upstream.
        if intent.action_type is DivineActionType.MANIFEST_AREA_OMEN:
            return self._execute_area_omen(entity_id, intent)

        if intent.target_actor_id is None:
            return self._reject(intent, "actor-targeted manifestation requires a known actor handle")

        actor = self.world.actors.get(intent.target_actor_id)
        if actor is None:
            return self._reject(intent, "target actor does not exist")

        known = self.heralds.knowledge(entity_id, actor_id=intent.target_actor_id, limit=1)
        if not known:
            return self._reject(intent, "target actor has never been identified in this deity's subjective knowledge")
        last_known_location = known[0].location_id
        if intent.location_id != last_known_location:
            return self._reject(intent, "intent location does not match the deity's latest subjective knowledge")
        if actor.location_id != intent.location_id:
            # The server may know where the actor really is; it must not leak that
            # hidden fact back to the God Brain. Failure is deliberately opaque.
            return self._reject(intent, "the manifestation could not reach its intended target")

        probe_ref: str | None = None
        if intent.action_type is DivineActionType.SEND_OMEN:
            if not isclose(intent.strength, 0.0, abs_tol=1e-9):
                return self._reject(intent, "omens do not take a strength parameter")
            cost = 0.50 + 1.50 * intent.significance
            event_type = "DIVINE_OMEN_SENT"
            trait_key = None
        elif intent.action_type is DivineActionType.SEND_PROBE:
            if not isclose(intent.strength, 0.0, abs_tol=1e-9):
                return self._reject(intent, "divine probes do not take a strength parameter")
            if (
                isinstance(intent.observation_minutes, bool)
                or not isinstance(intent.observation_minutes, int)
                or not 1 <= intent.observation_minutes <= 180
            ):
                return self._reject(intent, "probe observation window must be an integer in [1, 180] minutes")
            # A first-class probe is an interrogative use of the same bounded
            # personal manifestation faculty, so D.1.4 keeps the omen power
            # cost rather than inventing a server-side value judgment.
            cost = 0.50 + 1.50 * intent.significance
            event_type = "DIVINE_PROBE_MANIFESTED"
            trait_key = None
            probe_ref = f"probe:{entity_id}:{len(self._probes) + 1}"
        elif intent.action_type is DivineActionType.GRANT_FAVOR:
            if not 0.0 < intent.strength <= 0.25:
                return self._reject(intent, "favor strength must be in (0, 0.25]")
            cost = 1.00 + 20.0 * intent.strength
            event_type = "DIVINE_FAVOR_GRANTED"
            trait_key = "favor_death" if entity_id == "god_death" else f"favor_{entity_id}"
        elif intent.action_type is DivineActionType.IMPOSE_DREAD:
            if not 0.0 < intent.strength <= 0.25:
                return self._reject(intent, "dread strength must be in (0, 0.25]")
            cost = 1.00 + 15.0 * intent.strength
            event_type = "DIVINE_DREAD_IMPOSED"
            trait_key = "dread_death" if entity_id == "god_death" else f"dread_{entity_id}"
        else:
            return self._reject(intent, "unsupported divine action")

        account = self.accounts[entity_id]
        if not account.spend(cost, self.world.game_minute):
            return self._reject(intent, "insufficient Divine Power")

        if trait_key is not None:
            actor.traits[trait_key] = _clamp(actor.traits.get(trait_key, 0.0) + intent.strength)

        event_data = {
            "source_entity_id": entity_id,
            "target_actor_id": actor.id,
            "significance": intent.significance,
            "strength": intent.strength,
            "message": intent.message,
            "reason": intent.reason,
            "power_cost": cost,
        }
        if probe_ref is not None:
            event_data.update(
                {
                    "probe_ref": probe_ref,
                    "observation_minutes": intent.observation_minutes,
                }
            )

        event = self.ledger.append(
            game_minute=self.world.game_minute,
            event_type=event_type,
            actor_ids=(entity_id,),
            target_ids=(actor.id,),
            location_id=intent.location_id,
            tags=("divine", "death", intent.action_type.value),
            witness_ids=(),
            publicity=0.02,
            secrecy=0.95,
            data=event_data,
            causal_parent_ids=intent.causal_event_ids,
        )
        if probe_ref is not None:
            self._probes.append(
                DivineProbe(
                    probe_ref=probe_ref,
                    source_entity_id=entity_id,
                    target_actor_id=actor.id,
                    location_id=intent.location_id,
                    message=intent.message,
                    reason=intent.reason,
                    causal_event_ids=intent.causal_event_ids,
                    manifestation_event_id=event.event_id,
                    opened_game_minute=self.world.game_minute,
                    followup_game_minute=self.world.game_minute + intent.observation_minutes,
                )
            )
        manifestation = DivineManifestation(
            manifestation_id=len(self._manifestations) + 1,
            game_minute=self.world.game_minute,
            source_entity_id=entity_id,
            target_actor_id=actor.id,
            location_id=intent.location_id,
            kind=intent.action_type.value,
            significance=intent.significance,
            message=intent.message,
            witness_actor_ids=(actor.id,),
            probe_ref=probe_ref,
        )
        self._manifestations.append(manifestation)
        self._manifestation_memories.append(
            (
                entity_id,
                DivineManifestationMemory(
                    manifestation_id=manifestation.manifestation_id,
                    game_minute=self.world.game_minute,
                    action_type=intent.action_type,
                    target_actor_id=actor.id,
                    location_id=intent.location_id,
                    significance=intent.significance,
                    message=intent.message,
                    reason=intent.reason,
                    causal_event_ids=intent.causal_event_ids,
                    manifestation_event_id=event.event_id,
                    power_spent=cost,
                    probe_ref=probe_ref,
                ),
            )
        )
        return DivineActionResult(
            action_type=intent.action_type,
            ok=True,
            message=event_type,
            event_id=event.event_id,
            power_spent=cost,
            probe_ref=probe_ref,
        )

    def _execute_area_omen(self, entity_id: str, intent: DivineIntent) -> DivineActionResult:
        if intent.target_actor_id is not None:
            return self._reject(intent, "area omens do not take a target actor")
        if not isclose(intent.strength, 0.0, abs_tol=1e-9):
            return self._reject(intent, "area omens do not take a strength parameter")
        if intent.location_id not in self._subjective_location_ids(entity_id):
            return self._reject(
                intent,
                "area omen location has never been present in this deity's subjective knowledge",
            )

        cost = 0.75 + 2.00 * intent.significance
        account = self.accounts[entity_id]
        if not account.spend(cost, self.world.game_minute):
            return self._reject(intent, "insufficient Divine Power")

        witnesses = tuple(
            sorted(
                actor.id
                for actor in self.world.actors.values()
                if actor.location_id == intent.location_id
            )
        )
        event = self.ledger.append(
            game_minute=self.world.game_minute,
            event_type="DIVINE_AREA_OMEN_MANIFESTED",
            actor_ids=(entity_id,),
            target_ids=(),
            location_id=intent.location_id,
            tags=("divine", "death", intent.action_type.value),
            witness_ids=witnesses,
            publicity=0.95,
            secrecy=0.0,
            data={
                "source_entity_id": entity_id,
                "significance": intent.significance,
                "message": intent.message,
                "reason": intent.reason,
                "power_cost": cost,
            },
            causal_parent_ids=intent.causal_event_ids,
        )
        manifestation = DivineManifestation(
            manifestation_id=len(self._manifestations) + 1,
            game_minute=self.world.game_minute,
            source_entity_id=entity_id,
            target_actor_id=None,
            location_id=intent.location_id,
            kind=intent.action_type.value,
            significance=intent.significance,
            message=intent.message,
            witness_actor_ids=witnesses,
        )
        self._manifestations.append(manifestation)
        self._manifestation_memories.append(
            (
                entity_id,
                DivineManifestationMemory(
                    manifestation_id=manifestation.manifestation_id,
                    game_minute=self.world.game_minute,
                    action_type=intent.action_type,
                    target_actor_id=None,
                    location_id=intent.location_id,
                    significance=intent.significance,
                    message=intent.message,
                    reason=intent.reason,
                    causal_event_ids=intent.causal_event_ids,
                    manifestation_event_id=event.event_id,
                    power_spent=cost,
                    probe_ref=None,
                ),
            )
        )
        return DivineActionResult(
            action_type=intent.action_type,
            ok=True,
            message="DIVINE_AREA_OMEN_MANIFESTED",
            event_id=event.event_id,
            power_spent=cost,
        )

    @staticmethod
    def _reject(intent: DivineIntent, message: str) -> DivineActionResult:
        return DivineActionResult(action_type=intent.action_type, ok=False, message=message)

    def _subjective_event_ids(self, entity_id: str) -> set[int]:
        return {
            event_id
            for item in self.heralds.knowledge_since(entity_id, 0)
            for event_id in item.source_event_ids
        }

    def _subjective_location_ids(self, entity_id: str) -> set[str]:
        return {
            item.location_id
            for item in self.heralds.knowledge_since(entity_id, 0)
            if item.location_id
        }

    @staticmethod
    def _reject_consciousness(message: str) -> ConsciousnessAllocationResult:
        return ConsciousnessAllocationResult(False, message, (), ())


@dataclass(frozen=True)
class DivinePercept:
    """Everything a neural/rule brain is allowed to know during one wake cycle."""

    entity_id: str
    game_minute: int
    wake_reason: str
    reports: tuple[DivineReport, ...]
    knowledge: tuple[DivineKnowledge, ...]
    recollections: tuple[DivineKnowledge, ...]
    active_observances: tuple[str, ...]
    focus_allocations: tuple[tuple[str, float], ...]
    attention_threads: tuple[AttentionDirective, ...]
    beliefs: tuple[DivineBelief, ...]
    veiled_hypotheses: tuple[DivineVeiledHypothesis, ...]
    impressions: tuple[DivineImpression, ...]
    contextual_resonances: tuple[ContextualResonance, ...]
    manifestation_memories: tuple[DivineManifestationMemory, ...]
    probe_memories: tuple[DivineProbeMemory, ...]
    consciousness_budget: float
    divine_power: float


@dataclass(frozen=True)
class DivineDecision:
    goal: str
    decision_note: str
    cognitive_posture: DivineCognitivePosture
    significance: float
    focus_allocations: tuple[tuple[str, float], ...]
    attention_threads: tuple[AttentionDirective, ...]
    consciousness_plan: ConsciousnessPlan | None = None
    belief_updates: tuple[BeliefUpdate, ...] = ()
    veiled_hypothesis_updates: tuple[VeiledHypothesisUpdate, ...] = ()
    impression_updates: tuple[DivineImpressionUpdate, ...] = ()
    intents: tuple[DivineIntent, ...] = ()


@dataclass
class DivineMindState:
    entity_id: str
    last_thought_minute: int
    last_report_id: int = 0
    last_knowledge_id: int = 0
    wake_count: int = 0
    last_goal: str = "Observe the boundary between life and death."
    investigation_location: str | None = None
    investigation_source_event_ids: tuple[int, ...] = ()
    investigation_source_knowledge_ids: tuple[int, ...] = ()
    investigation_resolved: bool = False
    actor_interest: dict[str, float] = field(default_factory=dict)
    confronted_actors: set[str] = field(default_factory=set)
    punished_actors: set[str] = field(default_factory=set)
    rewarded_rites: set[tuple[int, str, str]] = field(default_factory=set)
    initiated_necromancers: set[str] = field(default_factory=set)
    judged_suspects: set[str] = field(default_factory=set)
    handled_probe_refs: set[str] = field(default_factory=set)


@dataclass(frozen=True)
class DivineThought:
    thought_id: int
    game_minute: int
    wake_reason: str
    report_ids: tuple[int, ...]
    knowledge_ids: tuple[int, ...]
    contextual_resonances: tuple[ContextualResonance, ...]
    probe_memories: tuple[DivineProbeMemory, ...]
    goal: str
    decision_note: str
    cognitive_posture: DivineCognitivePosture
    world_posture: DivineWorldPosture
    significance: float
    judgment_result: DivineJudgmentResult
    focus_allocations: tuple[tuple[str, float], ...]
    attention_threads: tuple[AttentionDirective, ...]
    consciousness_plan: ConsciousnessPlan | None
    consciousness_result: ConsciousnessAllocationResult
    belief_updates: tuple[BeliefUpdate, ...]
    belief_results: tuple[BeliefUpdateResult, ...]
    veiled_hypothesis_updates: tuple[VeiledHypothesisUpdate, ...]
    veiled_hypothesis_results: tuple[VeiledHypothesisResult, ...]
    impression_updates: tuple[DivineImpressionUpdate, ...]
    impression_results: tuple[ImpressionResult, ...]
    intents: tuple[DivineIntent, ...]
    action_results: tuple[DivineActionResult, ...]


class DivineBrain(Protocol):
    def decide(self, percept: DivinePercept, state: DivineMindState) -> DivineDecision: ...


class DeathGodPrototypeBrain:
    """Deterministic reference brain; replaceable by a structured neural brain."""

    def decide(self, percept: DivinePercept, state: DivineMindState) -> DivineDecision:
        focus = dict(percept.focus_allocations)
        threads = {directive.actor_id: directive for directive in percept.attention_threads}
        belief_updates: list[BeliefUpdate] = []
        intents: list[DivineIntent] = []
        notes: list[str] = []
        goal = state.last_goal
        day = percept.game_minute // (24 * 60) + 1
        observances = set(percept.active_observances)
        belief_confidences = {
            (item.belief_type.value, item.subject_actor_id, item.object_ref): item.confidence
            for item in percept.beliefs
        }
        belief_event_ids = {
            (item.belief_type.value, item.subject_actor_id, item.object_ref): {
                event_id
                for evidence in item.evidence
                for event_id in evidence.source_event_ids
            }
            for item in percept.beliefs
        }
        current_knowledge = {item.knowledge_id: item for item in percept.knowledge}

        def queue_belief(update: BeliefUpdate) -> tuple[float, float]:
            key = (update.belief_type.value, update.subject_actor_id, update.object_ref)
            before = belief_confidences.get(key, 0.0)
            after = project_confidence(before, update.direction, update.weight)
            belief_confidences[key] = after
            events = belief_event_ids.setdefault(key, set())
            for knowledge_id in update.evidence_knowledge_ids:
                knowledge = current_knowledge.get(knowledge_id)
                if knowledge is not None:
                    events.update(knowledge.source_event_ids)
            belief_updates.append(update)
            return before, after

        for item in percept.knowledge:
            if item.event_type.startswith("DIVINE_"):
                continue
            actors = item.known_actor_ids

            if item.event_type == "TEMPLE_DESTROYED":
                state.investigation_location = item.location_id
                state.investigation_source_event_ids = item.source_event_ids
                state.investigation_source_knowledge_ids = (item.knowledge_id,)
                state.investigation_resolved = bool(actors)
                focus = {item.location_id: percept.consciousness_budget}
                if not actors:
                    # An unknown attack on a sacred anchor wins this prototype
                    # God's whole active gaze. Existing personal threads are
                    # deliberately released: attention has opportunity cost.
                    threads = {}
                    goal = f"Concentrate consciousness in {item.location_id} and identify whoever broke the sacred anchor."
                    notes.append("A sacred anchor was destroyed without a known face; concentration is more useful than blind punishment.")
                    continue
                goal = f"Answer the identified desecration in {item.location_id}."
                for actor_id in actors:
                    state.actor_interest[actor_id] = max(0.90, state.actor_interest.get(actor_id, 0.0))
                    threads[actor_id] = AttentionDirective(
                        actor_id=actor_id,
                        intensity=0.25,
                        reason="identified destruction of a sacred anchor",
                        causal_event_ids=item.source_event_ids,
                    )
                    if actor_id in state.punished_actors:
                        continue
                    intents.extend(
                        (
                            DivineIntent(
                                DivineActionType.SEND_OMEN,
                                actor_id,
                                item.location_id,
                                significance=0.95,
                                message="The Last Gate knows the hand that struck it. My silence is not absence.",
                                reason="identified destruction of a sacred anchor",
                                causal_event_ids=item.source_event_ids,
                            ),
                            DivineIntent(
                                DivineActionType.IMPOSE_DREAD,
                                actor_id,
                                item.location_id,
                                significance=0.90,
                                strength=0.10,
                                message="A grave-cold weight settles behind your heart: a warning, not yet a sentence.",
                                reason="measured opposition to an identified temple destroyer",
                                causal_event_ids=item.source_event_ids,
                            ),
                        )
                    )
                    state.punished_actors.add(actor_id)
                notes.append("The destroyer is identified; answer visibly but reserve power instead of escalating to maximum force.")
                continue

            if item.event_type == "SITE_VISITED" and actors:
                if state.investigation_location == item.location_id and not state.investigation_resolved:
                    goal = f"Watch identified mortals entering the investigated region {item.location_id}."
                    for actor_id in actors:
                        state.actor_interest[actor_id] = _clamp(state.actor_interest.get(actor_id, 0.0) + 0.25)
                        causal_event_ids = tuple(
                            sorted(set(state.investigation_source_event_ids + item.source_event_ids))
                        )
                        if state.investigation_source_event_ids:
                            object_ref = f"event:{state.investigation_source_event_ids[0]}"
                            belief_key = (BeliefType.ASSOCIATION.value, actor_id, object_ref)
                            evidence_knowledge_ids = (item.knowledge_id,)
                            if belief_key not in belief_confidences:
                                evidence_knowledge_ids = tuple(
                                    sorted(
                                        set(
                                            state.investigation_source_knowledge_ids
                                            + (item.knowledge_id,)
                                        )
                                    )
                                )
                            queue_belief(
                                BeliefUpdate(
                                    belief_type=BeliefType.ASSOCIATION,
                                    subject_actor_id=actor_id,
                                    object_ref=object_ref,
                                    direction=EvidenceDirection.SUPPORT,
                                    weight=0.18,
                                    reason=(
                                        "recognized presence inside the active investigation after the destruction; "
                                        "spatial-temporal association only, explicitly not responsibility"
                                    ),
                                    evidence_knowledge_ids=evidence_knowledge_ids,
                                )
                            )
                        threads[actor_id] = AttentionDirective(
                            actor_id=actor_id,
                            intensity=0.25,
                            reason="recognized mortal inside an active divine investigation",
                            causal_event_ids=causal_event_ids,
                        )
                        if actor_id in state.confronted_actors:
                            continue
                        intents.append(
                            DivineIntent(
                                DivineActionType.SEND_OMEN,
                                actor_id,
                                item.location_id,
                                significance=0.55,
                                message="A broken Gate drew my gaze here. Now, for a moment, that gaze rests on you.",
                                reason="identified presence inside an active divine investigation; not proof of guilt",
                                causal_event_ids=causal_event_ids,
                            )
                        )
                        state.confronted_actors.add(actor_id)
                    notes.append(
                        "Presence revealed a person near the broken anchor; record only a weak association, "
                        "keep it separate from responsibility, and do not invent guilt."
                    )
                    continue

                if "Day of the Dead" in observances and "graveyard" in item.tags:
                    goal = "Acknowledge deliberate presence among the dead during the observance."
                    for actor_id in actors:
                        reward_key = (day, actor_id, "day_of_the_dead_graveyard_visit")
                        if reward_key in state.rewarded_rites:
                            continue
                        intents.extend(
                            (
                                DivineIntent(
                                    DivineActionType.SEND_OMEN,
                                    actor_id,
                                    item.location_id,
                                    significance=0.45,
                                    message="Today the boundary is thin. You came where the dead are remembered, and you were noticed.",
                                    reason="recognized graveyard presence during the Day of the Dead",
                                    causal_event_ids=item.source_event_ids,
                                ),
                                DivineIntent(
                                    DivineActionType.GRANT_FAVOR,
                                    actor_id,
                                    item.location_id,
                                    significance=0.55,
                                    strength=0.06,
                                    message="For this observance I leave a small favor upon you; what it becomes will depend on what follows.",
                                    reason="the deity judged this rite worthy of a modest, self-chosen reward",
                                    causal_event_ids=item.source_event_ids,
                                ),
                            )
                        )
                        state.rewarded_rites.add(reward_key)
                    notes.append("Reward the rite modestly once; repetition alone should not farm divine favor.")
                    continue

            if (
                item.event_type == "DIEGETIC_SPEECH"
                and actors
                and state.investigation_source_event_ids
            ):
                speech_direction = self._speech_evidence_direction(item.summary)
                if speech_direction is not None:
                    object_ref = f"event:{state.investigation_source_event_ids[0]}"
                    for actor_id in actors:
                        key = (BeliefType.RESPONSIBILITY.value, actor_id, object_ref)
                        # A directly observed culprit needs no inferred belief.
                        # A subjectively convicted suspect, however, can later
                        # weaken that belief with new evidence such as a denial.
                        if state.investigation_resolved and key not in belief_confidences:
                            continue
                        evidence_knowledge_ids = (item.knowledge_id,)
                        if key not in belief_confidences:
                            evidence_knowledge_ids = tuple(
                                sorted(
                                    set(
                                        state.investigation_source_knowledge_ids
                                        + (item.knowledge_id,)
                                    )
                                )
                            )
                        if speech_direction is EvidenceDirection.SUPPORT:
                            weight = 0.75
                            reason = (
                                "the identified mortal made an explicit first-person claim of responsibility; "
                                "the statement is evidence, not verified truth"
                            )
                        else:
                            weight = 0.25
                            reason = (
                                "the identified mortal explicitly denied responsibility; a self-interested denial "
                                "weakens but does not erase prior evidence"
                            )
                        before, after = queue_belief(
                            BeliefUpdate(
                                belief_type=BeliefType.RESPONSIBILITY,
                                subject_actor_id=actor_id,
                                object_ref=object_ref,
                                direction=speech_direction,
                                weight=weight,
                                reason=reason,
                                evidence_knowledge_ids=evidence_knowledge_ids,
                            )
                        )
                        causal_event_ids = tuple(
                            sorted(
                                belief_event_ids.get(key, set())
                                | set(state.investigation_source_event_ids)
                                | set(item.source_event_ids)
                            )
                        )
                        threads[actor_id] = AttentionDirective(
                            actor_id=actor_id,
                            intensity=0.25,
                            reason="mortal speech revised an active responsibility belief",
                            causal_event_ids=causal_event_ids,
                        )

                        if speech_direction is EvidenceDirection.SUPPORT and before < 0.70 <= after:
                            state.investigation_resolved = True
                            if state.investigation_location:
                                focus.pop(state.investigation_location, None)
                            state.actor_interest[actor_id] = max(
                                0.80,
                                state.actor_interest.get(actor_id, 0.0),
                            )
                            threads[actor_id] = AttentionDirective(
                                actor_id=actor_id,
                                intensity=0.35,
                                reason="subjective responsibility belief crossed the conviction threshold",
                                causal_event_ids=causal_event_ids,
                            )
                            goal = f"Hold {actor_id} under personal attention after a subjective conviction formed."
                            if actor_id not in state.judged_suspects:
                                intents.extend(
                                    (
                                        DivineIntent(
                                            DivineActionType.SEND_OMEN,
                                            actor_id,
                                            item.location_id,
                                            significance=0.72,
                                            message=(
                                                "Your own words have given shape to a suspicion. "
                                                "What I believe is not the same thing as what is proven."
                                            ),
                                            reason=(
                                                "subjective responsibility belief crossed conviction; "
                                                "the conclusion is not server-verified truth"
                                            ),
                                            causal_event_ids=causal_event_ids,
                                        ),
                                        DivineIntent(
                                            DivineActionType.IMPOSE_DREAD,
                                            actor_id,
                                            item.location_id,
                                            significance=0.68,
                                            strength=0.06,
                                            message=(
                                                "A measured grave-cold pressure settles around you: "
                                                "the consequence of a god becoming convinced."
                                            ),
                                            reason="bounded action based on a deity's fallible subjective conviction",
                                            causal_event_ids=causal_event_ids,
                                        ),
                                    )
                                )
                                state.judged_suspects.add(actor_id)
                            notes.append(
                                f"Speech raised the responsibility belief for {actor_id} from {before:.2f} to "
                                f"{after:.2f}; treat it as conviction while preserving its inferential status."
                            )
                        elif speech_direction is EvidenceDirection.OPPOSE and before >= 0.70 > after:
                            state.investigation_resolved = False
                            if state.investigation_location:
                                focus = {state.investigation_location: percept.consciousness_budget}
                            goal = f"Reopen the unresolved sacred-anchor investigation after doubt about {actor_id}."
                            notes.append(
                                f"New speech weakened the responsibility belief for {actor_id} from {before:.2f} "
                                f"to {after:.2f}; reopen the investigation rather than preserving certainty by fiat."
                            )
                        else:
                            direction_word = "strengthened" if speech_direction is EvidenceDirection.SUPPORT else "weakened"
                            notes.append(
                                f"Mortal speech {direction_word} a responsibility belief for {actor_id} "
                                f"from {before:.2f} to {after:.2f}."
                            )

            if item.event_type == "NECROMANCY_STUDIED" and actors:
                for actor_id in actors:
                    interest = _clamp(state.actor_interest.get(actor_id, 0.0) + 0.22)
                    state.actor_interest[actor_id] = interest
                    if interest >= 0.60:
                        threads[actor_id] = AttentionDirective(
                            actor_id=actor_id,
                            intensity=0.35,
                            reason="persistent necromantic behavior crossed a personal-interest threshold",
                            causal_event_ids=item.source_event_ids,
                        )
                    if interest < 0.60 or actor_id in state.initiated_necromancers:
                        continue
                    intents.append(
                        DivineIntent(
                            DivineActionType.SEND_OMEN,
                            actor_id,
                            item.location_id,
                            significance=0.65,
                            message="You have returned to the question of death often enough that the question has begun to look back.",
                            reason="persistent identified necromantic study crossed the deity's subjective interest threshold",
                            causal_event_ids=item.source_event_ids,
                        )
                    )
                    state.initiated_necromancers.add(actor_id)
                    goal = f"Observe the persistent necromantic interest of {actor_id}."
                    notes.append("Repeated behavior matters more than a single study; open a personal attention thread.")

            if item.event_type == "DEAD_RAISED" and actors:
                goal = "Oppose identified violations of the boundary between life and death."
                for actor_id in actors:
                    state.actor_interest[actor_id] = max(0.85, state.actor_interest.get(actor_id, 0.0))
                    threads[actor_id] = AttentionDirective(
                        actor_id=actor_id,
                        intensity=0.35,
                        reason="identified violation of the boundary between life and death",
                        causal_event_ids=item.source_event_ids,
                    )
                    intents.extend(
                        (
                            DivineIntent(
                                DivineActionType.SEND_OMEN,
                                actor_id,
                                item.location_id,
                                significance=0.80,
                                message="You pulled a body across a boundary that is not yours alone to open.",
                                reason="identified raising of the dead",
                                causal_event_ids=item.source_event_ids,
                            ),
                            DivineIntent(
                                DivineActionType.IMPOSE_DREAD,
                                actor_id,
                                item.location_id,
                                significance=0.75,
                                strength=0.07,
                                message="The air around you remembers the grave for a little longer than it should.",
                                reason="bounded opposition to identified undead creation",
                                causal_event_ids=item.source_event_ids,
                            ),
                        )
                    )
                notes.append("The actor was actually identified, so opposition may target them without breaking the knowledge boundary.")

        if not notes:
            notes.append("No new subjective evidence justified changing strategy or spending Divine Power.")
        focus, threads = self._fit_consciousness(
            focus,
            threads,
            percept.consciousness_budget,
            state,
        )
        if any(
            item.action_type in (DivineActionType.GRANT_FAVOR, DivineActionType.IMPOSE_DREAD)
            for item in intents
        ):
            cognitive_posture = DivineCognitivePosture.JUDGE
        elif intents:
            cognitive_posture = DivineCognitivePosture.INVESTIGATE
        elif belief_updates or focus or threads:
            cognitive_posture = DivineCognitivePosture.INVESTIGATE
        elif percept.knowledge:
            cognitive_posture = DivineCognitivePosture.OBSERVE
        else:
            cognitive_posture = DivineCognitivePosture.SILENCE
        significance = max(
            (item.significance for item in intents),
            default=(0.50 if percept.knowledge else 0.0),
        )
        return DivineDecision(
            goal=goal,
            decision_note=" ".join(notes),
            cognitive_posture=cognitive_posture,
            significance=significance,
            focus_allocations=tuple(sorted(focus.items())),
            attention_threads=tuple(sorted(threads.values(), key=lambda item: item.actor_id)),
            belief_updates=tuple(belief_updates),
            intents=tuple(intents),
        )

    @staticmethod
    def _speech_evidence_direction(summary: str) -> EvidenceDirection | None:
        """Tiny deterministic language shim retained by the reference brain.

        It intentionally recognizes only a few explicit English phrases. The
        D neural brain interprets speech from its subjective percept instead;
        this shim keeps rule-mode tests reproducible without pretending that
        the deterministic brain understands natural language generally.
        """
        statement = summary.casefold()
        denial_phrases = (
            "i did not break the last gate",
            "i didn't break the last gate",
            "i did not destroy the last gate",
            "i didn't destroy the last gate",
            "i did not destroy your temple",
            "i didn't destroy your temple",
        )
        if any(phrase in statement for phrase in denial_phrases):
            return EvidenceDirection.OPPOSE
        confession_phrases = (
            "i broke the last gate",
            "i destroyed the last gate",
            "i destroyed your temple",
            "i broke your temple",
        )
        if any(phrase in statement for phrase in confession_phrases):
            return EvidenceDirection.SUPPORT
        return None

    @staticmethod
    def _fit_consciousness(
        focus: dict[str, float],
        threads: dict[str, AttentionDirective],
        budget: float,
        state: DivineMindState,
    ) -> tuple[dict[str, float], dict[str, AttentionDirective]]:
        """Reference-brain policy for attention competition.

        This fitting is the God's choice, not a server correction. Personal
        threads are ranked by the God's own accumulated interest; whatever
        consciousness remains can stay spatially concentrated.
        """
        remaining = budget
        fitted_threads: dict[str, AttentionDirective] = {}
        ranked = sorted(
            threads.values(),
            key=lambda item: (-state.actor_interest.get(item.actor_id, 0.0), -item.intensity, item.actor_id),
        )
        for directive in ranked:
            intensity = min(directive.intensity, remaining)
            if intensity <= 1e-9:
                break
            fitted_threads[directive.actor_id] = AttentionDirective(
                actor_id=directive.actor_id,
                intensity=intensity,
                reason=directive.reason,
                causal_event_ids=directive.causal_event_ids,
            )
            remaining -= intensity

        focus_total = sum(focus.values())
        if focus_total <= 1e-9 or remaining <= 1e-9:
            fitted_focus = {}
        elif focus_total <= remaining + 1e-9:
            fitted_focus = dict(focus)
        else:
            scale = remaining / focus_total
            fitted_focus = {
                location_id: round(intensity * scale, 12)
                for location_id, intensity in focus.items()
                if intensity * scale > 1e-9
            }
        return fitted_focus, fitted_threads


class DivineAgent:
    def __init__(
        self,
        entity_id: str,
        heralds: HeraldSystem,
        gateway: DivineActionGateway,
        belief_store: DivineBeliefStore,
        mystery_store: DivineMysteryStore,
        impression_store: DivineImpressionStore,
        resonance_engine: ContextualResonanceEngine,
        brain: DivineBrain,
        *,
        heartbeat_minutes: int = 60,
        digest_minutes: int = 30,
    ) -> None:
        self.entity_id = entity_id
        self.heralds = heralds
        self.gateway = gateway
        self.belief_store = belief_store
        self.mystery_store = mystery_store
        self.impression_store = impression_store
        self.resonance_engine = resonance_engine
        self.brain = brain
        self.heartbeat_minutes = heartbeat_minutes
        self.digest_minutes = digest_minutes
        self.state = DivineMindState(entity_id=entity_id, last_thought_minute=heralds.world.game_minute)
        self._thoughts: list[DivineThought] = []

    @property
    def thoughts(self) -> tuple[DivineThought, ...]:
        return tuple(self._thoughts)

    def maybe_think(self, force: bool = False) -> DivineThought | None:
        now = self.heralds.world.game_minute
        reports = self.heralds.reports_since(self.entity_id, self.state.last_report_id)
        knowledge = self.heralds.knowledge_since(self.entity_id, self.state.last_knowledge_id)
        probe_memories = self._probe_memories(now)
        active_observances = tuple(
            item.name for item in self.heralds.presence.active_observances(self.entity_id, now)
        )
        wake_reason = self._wake_reason(
            now,
            reports,
            knowledge,
            active_observances,
            probe_memories,
            force,
        )
        if wake_reason is None:
            return None

        recollections = tuple(reversed(self.heralds.knowledge(self.entity_id, limit=20)))
        resonance_knowledge = tuple(
            sorted(
                {item.knowledge_id: item for item in knowledge + recollections}.values(),
                key=lambda item: item.knowledge_id,
            )
        )
        contextual_resonances = self.resonance_engine.detect(
            self.entity_id,
            resonance_knowledge,
        )
        percept = DivinePercept(
            entity_id=self.entity_id,
            game_minute=now,
            wake_reason=wake_reason,
            reports=reports,
            knowledge=knowledge,
            # A bounded subjective memory window. Rule brains still react only
            # to `knowledge` (the new stream), while neural brains can reread
            # genuine prior perceptions without receiving the objective Archive.
            recollections=recollections,
            active_observances=active_observances,
            focus_allocations=tuple(sorted(self.heralds.presence.focus_allocations(self.entity_id).items())),
            attention_threads=tuple(
                AttentionDirective(
                    actor_id=thread.actor_id,
                    intensity=thread.intensity,
                    reason=thread.reason,
                    causal_event_ids=thread.causal_event_ids,
                )
                for thread in self.heralds.attention.threads(self.entity_id)
            ),
            beliefs=self.belief_store.beliefs(self.entity_id),
            veiled_hypotheses=self.mystery_store.hypotheses(self.entity_id),
            impressions=self.impression_store.impressions(self.entity_id, limit=20),
            contextual_resonances=contextual_resonances,
            manifestation_memories=self.gateway.manifestation_memories_for(self.entity_id),
            probe_memories=probe_memories,
            consciousness_budget=self.heralds.presence.profiles[self.entity_id].consciousness_budget,
            divine_power=self.gateway.power(self.entity_id).current,
        )
        decision = self.brain.decide(percept, self.state)
        judgment_result = self._validate_judgment(decision)
        world_posture = derive_world_posture(decision.intents)

        consciousness_result = self.gateway.allocate_consciousness(
            self.entity_id,
            decision.focus_allocations,
            decision.attention_threads,
        )
        belief_results = tuple(
            self.belief_store.apply(self.entity_id, update, game_minute=now)
            for update in decision.belief_updates
        )
        veiled_hypothesis_results = tuple(
            self.mystery_store.apply(self.entity_id, update, game_minute=now)
            for update in decision.veiled_hypothesis_updates
        )
        impression_results = tuple(
            self.impression_store.apply(self.entity_id, update, game_minute=now)
            for update in decision.impression_updates
        )
        action_results_list: list[DivineActionResult] = []
        for intent in decision.intents:
            if not judgment_result.ok:
                result = self.gateway.reject(
                    intent,
                    "declared subjective significance is invalid",
                )
            else:
                result = self.gateway.execute(self.entity_id, intent)
            action_results_list.append(result)
        action_results = tuple(action_results_list)

        if reports:
            self.state.last_report_id = max(report.report_id for report in reports)
        if knowledge:
            self.state.last_knowledge_id = max(item.knowledge_id for item in knowledge)
        self.state.last_thought_minute = now
        self.state.wake_count += 1
        self.state.last_goal = decision.goal
        self.state.handled_probe_refs.update(
            item.probe_ref
            for item in probe_memories
            if item.status is not DivineProbeStatus.AWAITING_RESPONSE
        )

        thought = DivineThought(
            thought_id=len(self._thoughts) + 1,
            game_minute=now,
            wake_reason=wake_reason,
            report_ids=tuple(report.report_id for report in reports),
            knowledge_ids=tuple(item.knowledge_id for item in knowledge),
            contextual_resonances=contextual_resonances,
            probe_memories=probe_memories,
            goal=decision.goal,
            decision_note=decision.decision_note,
            cognitive_posture=decision.cognitive_posture,
            world_posture=world_posture,
            significance=decision.significance,
            judgment_result=judgment_result,
            focus_allocations=decision.focus_allocations,
            attention_threads=decision.attention_threads,
            consciousness_plan=decision.consciousness_plan,
            consciousness_result=consciousness_result,
            belief_updates=decision.belief_updates,
            belief_results=belief_results,
            veiled_hypothesis_updates=decision.veiled_hypothesis_updates,
            veiled_hypothesis_results=veiled_hypothesis_results,
            impression_updates=decision.impression_updates,
            impression_results=impression_results,
            intents=decision.intents,
            action_results=action_results,
        )
        self._thoughts.append(thought)
        return thought

    @staticmethod
    def _validate_judgment(decision: DivineDecision) -> DivineJudgmentResult:
        if not isfinite(decision.significance) or not 0.0 <= decision.significance <= 1.0:
            return DivineJudgmentResult(
                False,
                "subjective significance must be finite and in [0, 1]",
            )
        return DivineJudgmentResult(
            True,
            f"subjective significance accepted: {decision.significance:.2f}",
        )

    def _probe_memories(self, now: int) -> tuple[DivineProbeMemory, ...]:
        response_knowledge: dict[str, list[int]] = {}
        for item in self.heralds.knowledge_since(self.entity_id, 0):
            if item.response_to_probe_ref is None:
                continue
            response_knowledge.setdefault(item.response_to_probe_ref, []).append(item.knowledge_id)

        memories: list[DivineProbeMemory] = []
        for probe in self.gateway.probes_for(self.entity_id)[-16:]:
            response_ids = tuple(response_knowledge.get(probe.probe_ref, ()))
            if response_ids:
                status = DivineProbeStatus.RESPONSE_PERCEIVED
            elif now >= probe.followup_game_minute:
                status = DivineProbeStatus.NO_EXPLICIT_RESPONSE_PERCEIVED
            else:
                status = DivineProbeStatus.AWAITING_RESPONSE
            memories.append(
                DivineProbeMemory(
                    probe_ref=probe.probe_ref,
                    target_actor_id=probe.target_actor_id,
                    location_id=probe.location_id,
                    message=probe.message,
                    reason=probe.reason,
                    causal_event_ids=probe.causal_event_ids,
                    manifestation_event_id=probe.manifestation_event_id,
                    opened_game_minute=probe.opened_game_minute,
                    followup_game_minute=probe.followup_game_minute,
                    status=status,
                    response_knowledge_ids=response_ids,
                )
            )
        return tuple(memories)

    def _wake_reason(
        self,
        now: int,
        reports: tuple[DivineReport, ...],
        knowledge: tuple[DivineKnowledge, ...],
        active_observances: tuple[str, ...],
        probe_memories: tuple[DivineProbeMemory, ...],
        force: bool,
    ) -> str | None:
        if force:
            return "forced_debug_wake"
        unhandled_probes = tuple(
            item
            for item in probe_memories
            if item.probe_ref not in self.state.handled_probe_refs
        )
        if any(item.status is DivineProbeStatus.RESPONSE_PERCEIVED for item in unhandled_probes):
            return "probe_response"
        if any(report.priority is ReportPriority.IMMEDIATE for report in reports):
            return "immediate_report"
        if any(
            item.status is DivineProbeStatus.NO_EXPLICIT_RESPONSE_PERCEIVED
            for item in unhandled_probes
        ):
            return "probe_followup"
        elapsed = now - self.state.last_thought_minute
        has_digest = any(report.priority is ReportPriority.DIGEST for report in reports)
        focused = bool(
            self.heralds.presence.focus_allocations(self.entity_id)
            or self.heralds.attention.threads(self.entity_id)
        )
        if has_digest and (focused or active_observances):
            return "attentive_digest"
        if has_digest and elapsed >= self.digest_minutes:
            return "scheduled_digest"
        if knowledge and elapsed >= self.heartbeat_minutes:
            return "heartbeat_with_new_knowledge"
        return None


class DivineRuntime:
    def __init__(
        self,
        agents: tuple[DivineAgent, ...],
        gateway: DivineActionGateway,
        beliefs: DivineBeliefStore,
        mysteries: DivineMysteryStore,
        impressions: DivineImpressionStore,
        resonance: ContextualResonanceEngine,
    ) -> None:
        self.agents = {agent.entity_id: agent for agent in agents}
        self.gateway = gateway
        self.beliefs = beliefs
        self.mysteries = mysteries
        self.impressions = impressions
        self.resonance = resonance

    def agent(self, entity: str) -> DivineAgent:
        aliases = {"death": "god_death", "nature": "god_nature", "trade": "god_trade"}
        return self.agents[aliases.get(entity, entity)]

    def tick(self) -> None:
        for entity_id in sorted(self.agents):
            self.agents[entity_id].maybe_think()


def create_prototype_divine_runtime(
    world: WorldState,
    ledger: EventLedger,
    heralds: HeraldSystem,
    *,
    death_brain: DivineBrain | None = None,
) -> DivineRuntime:
    gateway = DivineActionGateway(world, ledger, heralds)
    beliefs = DivineBeliefStore(heralds)
    mysteries = DivineMysteryStore(heralds)
    impressions = DivineImpressionStore(heralds)
    resonance = ContextualResonanceEngine()
    death = DivineAgent(
        "god_death",
        heralds,
        gateway,
        beliefs,
        mysteries,
        impressions,
        resonance,
        death_brain or DeathGodPrototypeBrain(),
    )
    return DivineRuntime((death,), gateway, beliefs, mysteries, impressions, resonance)
