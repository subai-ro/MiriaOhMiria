from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum
from math import isfinite

from .heralds import HeraldSystem


class BeliefType(str, Enum):
    """Fallible actor-event roles a deity may infer from subjective evidence.

    These names deliberately separate culpability from weaker forms of
    relevance.  A God may still choose the wrong role; the server validates
    provenance, never objective truth.
    """

    RESPONSIBILITY = "responsibility"
    AWARENESS = "awareness"
    WITNESS = "witness"
    EVENT_TARGET = "event_target"
    AFFECTED_BY = "affected_by"
    ASSOCIATION = "association"
    BYSTANDER = "bystander"


EVENT_ROLE_BELIEF_TYPES = frozenset(BeliefType)


BELIEF_TYPE_MEANINGS: dict[BeliefType, str] = {
    BeliefType.RESPONSIBILITY: "caused, ordered, or knowingly participated in",
    BeliefType.AWARENESS: "is aware of or understands something about",
    BeliefType.WITNESS: "perceived or witnessed",
    BeliefType.EVENT_TARGET: "was an intended target of",
    BeliefType.AFFECTED_BY: "was affected by",
    BeliefType.ASSOCIATION: "has a meaningful non-causal association with",
    BeliefType.BYSTANDER: "was a non-participating bystander near",
}


def canonical_belief_proposition(
    belief_type: BeliefType,
    actor_id: str,
    object_ref: str,
) -> str:
    """Return the sole semantic proposition tracked by a typed actor-event belief.

    Free-form neural text is deliberately excluded.  SUPPORT always supports
    this proposition and OPPOSE always weighs against this same proposition,
    so a model cannot accidentally encode innocence as responsibility merely
    by negating a sentence in prose.
    """

    meaning = BELIEF_TYPE_MEANINGS[belief_type]
    return f"{actor_id} {meaning} {object_ref}."


class EvidenceDirection(str, Enum):
    SUPPORT = "support"
    OPPOSE = "oppose"


class BeliefStatus(str, Enum):
    DISMISSED = "dismissed"
    POSSIBLE = "possible"
    SUSPECTED = "suspected"
    CONVICTION = "conviction"


def belief_status(confidence: float) -> BeliefStatus:
    if confidence < 0.10:
        return BeliefStatus.DISMISSED
    if confidence < 0.40:
        return BeliefStatus.POSSIBLE
    if confidence < 0.70:
        return BeliefStatus.SUSPECTED
    return BeliefStatus.CONVICTION


def project_confidence(
    confidence: float,
    direction: EvidenceDirection,
    weight: float,
) -> float:
    """Combine subjective evidential weight without pretending it is truth.

    The God chooses both direction and weight. The memory layer merely folds
    that choice into a stable bounded confidence value.
    """
    if direction is EvidenceDirection.SUPPORT:
        result = confidence + (1.0 - confidence) * weight
    else:
        result = confidence * (1.0 - weight)
    return max(0.0, min(1.0, result))


@dataclass(frozen=True)
class BeliefUpdate:
    belief_type: BeliefType
    subject_actor_id: str
    object_ref: str
    direction: EvidenceDirection
    weight: float
    reason: str
    evidence_knowledge_ids: tuple[int, ...]


@dataclass(frozen=True)
class BeliefEvidence:
    evidence_id: int
    game_minute: int
    direction: EvidenceDirection
    weight: float
    reason: str
    source_knowledge_ids: tuple[int, ...]
    source_event_ids: tuple[int, ...]
    confidence_before: float
    confidence_after: float


@dataclass(frozen=True)
class DivineBelief:
    belief_id: int
    entity_id: str
    belief_type: BeliefType
    subject_actor_id: str
    object_ref: str
    proposition: str
    confidence: float
    status: BeliefStatus
    created_minute: int
    updated_minute: int
    evidence: tuple[BeliefEvidence, ...]


@dataclass(frozen=True)
class BeliefUpdateResult:
    ok: bool
    message: str
    belief_id: int | None = None
    confidence_before: float | None = None
    confidence_after: float | None = None
    status: BeliefStatus | None = None
    applied: bool = False
    applied_evidence_knowledge_ids: tuple[int, ...] = ()
    ignored_reused_knowledge_ids: tuple[int, ...] = ()

    @property
    def confidence_changed(self) -> bool:
        return (
            self.confidence_before is not None
            and self.confidence_after is not None
            and self.confidence_before != self.confidence_after
        )


class DivineBeliefStore:
    """Private, provenance-checked memory of a deity's interpretations.

    Deliberately has no Ledger or objective Archive. It can validate that
    evidence was present in DivineKnowledge, but it cannot ask whether the
    resulting proposition is objectively true.
    """

    def __init__(self, heralds: HeraldSystem) -> None:
        self.heralds = heralds
        self._beliefs: dict[str, dict[tuple[str, str, str], DivineBelief]] = {
            entity_id: {} for entity_id in heralds.profiles
        }
        self._belief_sequence = 0
        self._evidence_sequence = 0

    def beliefs(self, entity: str) -> tuple[DivineBelief, ...]:
        entity_id = self._entity_id(entity)
        return tuple(sorted(self._beliefs[entity_id].values(), key=lambda item: item.belief_id))

    def find(
        self,
        entity: str,
        *,
        belief_type: BeliefType | None = None,
        actor_id: str | None = None,
        object_ref: str | None = None,
    ) -> tuple[DivineBelief, ...]:
        items = self.beliefs(entity)
        return tuple(
            item
            for item in items
            if (belief_type is None or item.belief_type is belief_type)
            and (actor_id is None or item.subject_actor_id == actor_id)
            and (object_ref is None or item.object_ref == object_ref)
        )

    def get(
        self,
        entity: str,
        belief_type: BeliefType,
        actor_id: str,
        object_ref: str,
    ) -> DivineBelief | None:
        entity_id = self._entity_id(entity)
        return self._beliefs[entity_id].get((belief_type.value, actor_id, object_ref))

    def apply(
        self,
        entity: str,
        update: BeliefUpdate,
        *,
        game_minute: int | None = None,
    ) -> BeliefUpdateResult:
        entity_id = self._entity_id(entity, strict=False)
        if entity_id is None:
            return BeliefUpdateResult(False, "unknown divine entity")
        if not update.subject_actor_id.strip():
            return BeliefUpdateResult(False, "belief subject must identify an actor")
        if not update.reason.strip() or len(update.reason) > 500:
            return BeliefUpdateResult(False, "belief revision reason must contain 1..500 characters")
        if not isfinite(update.weight) or not 0.0 < update.weight <= 1.0:
            return BeliefUpdateResult(False, "subjective evidence weight must be in (0, 1]")
        if not update.evidence_knowledge_ids:
            return BeliefUpdateResult(False, "belief revision requires subjective evidence")
        if len(set(update.evidence_knowledge_ids)) != len(update.evidence_knowledge_ids):
            return BeliefUpdateResult(False, "duplicate subjective evidence ids")

        knowledge = {
            item.knowledge_id: item
            for item in self.heralds.knowledge_since(entity_id, 0)
        }
        missing = [item_id for item_id in update.evidence_knowledge_ids if item_id not in knowledge]
        if missing:
            return BeliefUpdateResult(
                False,
                "belief evidence was never present in this deity's subjective knowledge",
            )

        known_actor_ids = {
            actor_id
            for item in knowledge.values()
            for actor_id in item.known_actor_ids
        }
        if update.subject_actor_id not in known_actor_ids:
            return BeliefUpdateResult(
                False,
                "belief subject has never been identified in this deity's subjective knowledge",
            )

        if update.belief_type in EVENT_ROLE_BELIEF_TYPES:
            event_id = self._event_ref(update.object_ref)
            if event_id is None:
                return BeliefUpdateResult(False, "actor-event beliefs require object_ref='event:<id>'")
            subjective_event_ids = {
                event_id
                for item in knowledge.values()
                for event_id in item.source_event_ids
            }
            if event_id not in subjective_event_ids:
                return BeliefUpdateResult(
                    False,
                    "belief object was never present in this deity's subjective knowledge",
                )

        key = (update.belief_type.value, update.subject_actor_id, update.object_ref)
        previous = self._beliefs[entity_id].get(key)
        used_knowledge_ids = (
            {
                knowledge_id
                for evidence in previous.evidence
                for knowledge_id in evidence.source_knowledge_ids
            }
            if previous is not None
            else set()
        )
        reused_knowledge_ids = tuple(
            sorted(used_knowledge_ids.intersection(update.evidence_knowledge_ids))
        )
        novel_knowledge_ids = tuple(
            sorted(set(update.evidence_knowledge_ids) - used_knowledge_ids)
        )
        if not novel_knowledge_ids:
            return BeliefUpdateResult(
                True,
                "no new subjective evidence; confidence unchanged",
                belief_id=previous.belief_id if previous else None,
                confidence_before=previous.confidence if previous else None,
                confidence_after=previous.confidence if previous else None,
                status=previous.status if previous else None,
                applied=False,
                ignored_reused_knowledge_ids=reused_knowledge_ids,
            )

        before = previous.confidence if previous else 0.0
        after = round(project_confidence(before, update.direction, update.weight), 12)
        minute = self.heralds.world.game_minute if game_minute is None else game_minute
        source_event_ids = tuple(
            sorted(
                {
                    event_id
                    for knowledge_id in novel_knowledge_ids
                    for event_id in knowledge[knowledge_id].source_event_ids
                }
            )
        )
        self._evidence_sequence += 1
        evidence = BeliefEvidence(
            evidence_id=self._evidence_sequence,
            game_minute=minute,
            direction=update.direction,
            weight=update.weight,
            reason=update.reason,
            source_knowledge_ids=novel_knowledge_ids,
            source_event_ids=source_event_ids,
            confidence_before=before,
            confidence_after=after,
        )

        if previous is None:
            self._belief_sequence += 1
            revised = DivineBelief(
                belief_id=self._belief_sequence,
                entity_id=entity_id,
                belief_type=update.belief_type,
                subject_actor_id=update.subject_actor_id,
                object_ref=update.object_ref,
                proposition=canonical_belief_proposition(
                    update.belief_type,
                    update.subject_actor_id,
                    update.object_ref,
                ),
                confidence=after,
                status=belief_status(after),
                created_minute=minute,
                updated_minute=minute,
                evidence=(evidence,),
            )
        else:
            revised = replace(
                previous,
                confidence=after,
                status=belief_status(after),
                updated_minute=minute,
                evidence=previous.evidence + (evidence,),
            )
        self._beliefs[entity_id][key] = revised
        return BeliefUpdateResult(
            True,
            (
                f"belief revised from new evidence: {before:.3f} -> {after:.3f} "
                f"({revised.status.value})"
            ),
            belief_id=revised.belief_id,
            confidence_before=before,
            confidence_after=after,
            status=revised.status,
            applied=True,
            applied_evidence_knowledge_ids=novel_knowledge_ids,
            ignored_reused_knowledge_ids=reused_knowledge_ids,
        )

    @staticmethod
    def _event_ref(value: str) -> int | None:
        prefix = "event:"
        if not value.startswith(prefix):
            return None
        raw = value[len(prefix):]
        if not raw.isdigit():
            return None
        return int(raw)

    @staticmethod
    def _alias(entity: str) -> str:
        return {"death": "god_death", "nature": "god_nature", "trade": "god_trade"}.get(entity, entity)

    def _entity_id(self, entity: str, *, strict: bool = True) -> str | None:
        entity_id = self._alias(entity)
        if entity_id in self._beliefs:
            return entity_id
        if strict:
            raise KeyError(entity)
        return None
