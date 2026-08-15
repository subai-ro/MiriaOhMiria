from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum
from math import isfinite

from .beliefs import BeliefEvidence, EvidenceDirection, project_confidence
from .heralds import HeraldSystem


class HypothesisStatus(str, Enum):
    """Strength of support for a proposition about an unresolved subject.

    These names deliberately stop short of `conviction`: a God may strongly
    support a proposition about a veil while the identity behind that veil is
    still genuinely unknown.
    """

    DISMISSED = "dismissed"
    POSSIBLE = "possible"
    PLAUSIBLE = "plausible"
    STRONG = "strong"


def hypothesis_status(confidence: float) -> HypothesisStatus:
    if confidence < 0.10:
        return HypothesisStatus.DISMISSED
    if confidence < 0.40:
        return HypothesisStatus.POSSIBLE
    if confidence < 0.70:
        return HypothesisStatus.PLAUSIBLE
    return HypothesisStatus.STRONG


@dataclass(frozen=True)
class VeiledHypothesisUpdate:
    """A fallible thought about an unresolved subjective subject.

    `subject_ref` is an opaque divine-memory handle such as ``veil:event:7``.
    It is never an Actor id and therefore cannot be used as a target for
    personal attention, rewards, punishments, or direct manifestations.
    """

    subject_ref: str
    proposition: str
    direction: EvidenceDirection
    weight: float
    reason: str
    evidence_knowledge_ids: tuple[int, ...]


@dataclass(frozen=True)
class DivineVeiledHypothesis:
    hypothesis_id: int
    entity_id: str
    subject_ref: str
    proposition: str
    confidence: float
    status: HypothesisStatus
    created_minute: int
    updated_minute: int
    evidence: tuple[BeliefEvidence, ...]


@dataclass(frozen=True)
class VeiledHypothesisResult:
    ok: bool
    message: str
    hypothesis_id: int | None = None
    confidence_before: float | None = None
    confidence_after: float | None = None
    status: HypothesisStatus | None = None
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


class DivineMysteryStore:
    """Provenance-checked memory for things a God senses but cannot identify.

    Like DivineBeliefStore, this layer has no objective Ledger/Archive access.
    It can verify only that a veil and its cited evidence genuinely occurred in
    this deity's subjective knowledge.  It never tries to discover the mortal
    hiding behind a veil.
    """

    def __init__(self, heralds: HeraldSystem) -> None:
        self.heralds = heralds
        self._hypotheses: dict[str, dict[tuple[str, str], DivineVeiledHypothesis]] = {
            entity_id: {} for entity_id in heralds.profiles
        }
        self._hypothesis_sequence = 0
        self._evidence_sequence = 0

    def hypotheses(self, entity: str) -> tuple[DivineVeiledHypothesis, ...]:
        entity_id = self._entity_id(entity)
        return tuple(
            sorted(self._hypotheses[entity_id].values(), key=lambda item: item.hypothesis_id)
        )

    def apply(
        self,
        entity: str,
        update: VeiledHypothesisUpdate,
        *,
        game_minute: int | None = None,
    ) -> VeiledHypothesisResult:
        entity_id = self._entity_id(entity, strict=False)
        if entity_id is None:
            return VeiledHypothesisResult(False, "unknown divine entity")
        if not update.subject_ref.strip():
            return VeiledHypothesisResult(False, "veiled hypothesis requires a subject handle")
        if not update.proposition.strip() or len(update.proposition) > 500:
            return VeiledHypothesisResult(False, "veiled proposition must contain 1..500 characters")
        if not update.reason.strip() or len(update.reason) > 500:
            return VeiledHypothesisResult(False, "veiled revision reason must contain 1..500 characters")
        if not isfinite(update.weight) or not 0.0 < update.weight <= 1.0:
            return VeiledHypothesisResult(False, "subjective evidence weight must be in (0, 1]")
        if not update.evidence_knowledge_ids:
            return VeiledHypothesisResult(False, "veiled hypothesis revision requires subjective evidence")
        if len(set(update.evidence_knowledge_ids)) != len(update.evidence_knowledge_ids):
            return VeiledHypothesisResult(False, "duplicate subjective evidence ids")

        knowledge = {
            item.knowledge_id: item
            for item in self.heralds.knowledge_since(entity_id, 0)
        }
        missing = [item_id for item_id in update.evidence_knowledge_ids if item_id not in knowledge]
        if missing:
            return VeiledHypothesisResult(
                False,
                "veiled evidence was never present in this deity's subjective knowledge",
            )
        known_veils = {
            subject_ref
            for item in knowledge.values()
            for subject_ref in item.veiled_subject_refs
        }
        if update.subject_ref not in known_veils:
            return VeiledHypothesisResult(
                False,
                "veiled subject has never existed in this deity's subjective knowledge",
            )

        normalized_proposition = " ".join(update.proposition.split()).casefold()
        key = (update.subject_ref, normalized_proposition)
        previous = self._hypotheses[entity_id].get(key)
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
            return VeiledHypothesisResult(
                True,
                "no new subjective evidence; hypothesis confidence unchanged",
                hypothesis_id=previous.hypothesis_id if previous else None,
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
            self._hypothesis_sequence += 1
            revised = DivineVeiledHypothesis(
                hypothesis_id=self._hypothesis_sequence,
                entity_id=entity_id,
                subject_ref=update.subject_ref,
                proposition=" ".join(update.proposition.split()),
                confidence=after,
                status=hypothesis_status(after),
                created_minute=minute,
                updated_minute=minute,
                evidence=(evidence,),
            )
        else:
            revised = replace(
                previous,
                confidence=after,
                status=hypothesis_status(after),
                updated_minute=minute,
                evidence=previous.evidence + (evidence,),
            )
        self._hypotheses[entity_id][key] = revised
        return VeiledHypothesisResult(
            True,
            (
                f"veiled hypothesis revised from new evidence: {before:.3f} -> {after:.3f} "
                f"({revised.status.value})"
            ),
            hypothesis_id=revised.hypothesis_id,
            confidence_before=before,
            confidence_after=after,
            status=revised.status,
            applied=True,
            applied_evidence_knowledge_ids=novel_knowledge_ids,
            ignored_reused_knowledge_ids=reused_knowledge_ids,
        )

    @staticmethod
    def _alias(entity: str) -> str:
        return {"nature": "god_nature", "death": "god_death", "trade": "god_trade"}.get(entity, entity)

    def _entity_id(self, entity: str, *, strict: bool = True) -> str | None:
        entity_id = self._alias(entity)
        if entity_id in self._hypotheses:
            return entity_id
        if strict:
            raise KeyError(entity)
        return None
