from __future__ import annotations

from dataclasses import dataclass, replace
from math import isfinite

from .heralds import HeraldSystem


@dataclass(frozen=True)
class DivineImpressionUpdate:
    """A private memory mark chosen by a deity, never a claim of objective truth."""

    summary: str
    significance: float
    reason: str
    evidence_knowledge_ids: tuple[int, ...]


@dataclass(frozen=True)
class DivineImpression:
    impression_id: int
    entity_id: str
    summary: str
    significance: float
    reason: str
    source_knowledge_ids: tuple[int, ...]
    source_event_ids: tuple[int, ...]
    created_minute: int
    updated_minute: int


@dataclass(frozen=True)
class ImpressionResult:
    ok: bool
    message: str
    impression_id: int | None = None
    significance_before: float | None = None
    significance_after: float | None = None
    applied: bool = False
    applied_evidence_knowledge_ids: tuple[int, ...] = ()
    ignored_reused_knowledge_ids: tuple[int, ...] = ()


class DivineImpressionStore:
    """Provenance-checked private bookmarks in a God's own subjective memory.

    An impression deliberately changes no actor, region, Ledger event, or
    Divine Power account.  It lets a God decide that something is worth
    remembering without needing to manifest an omen merely as a bookmark.
    """

    def __init__(self, heralds: HeraldSystem) -> None:
        self.heralds = heralds
        self._items: dict[str, dict[str, DivineImpression]] = {
            entity_id: {} for entity_id in heralds.profiles
        }
        self._sequence = 0

    def impressions(self, entity: str, *, limit: int | None = None) -> tuple[DivineImpression, ...]:
        entity_id = self._entity_id(entity)
        items = sorted(self._items[entity_id].values(), key=lambda item: item.impression_id)
        if limit is not None:
            if limit < 0:
                raise ValueError("impression limit cannot be negative")
            items = items[-limit:] if limit else []
        return tuple(items)

    def apply(
        self,
        entity: str,
        update: DivineImpressionUpdate,
        *,
        game_minute: int | None = None,
        allowed_knowledge_ids: set[int] | None = None,
    ) -> ImpressionResult:
        entity_id = self._entity_id(entity, strict=False)
        if entity_id is None:
            return ImpressionResult(False, "unknown divine entity")
        summary = " ".join(update.summary.split())
        if not summary or len(summary) > 500:
            return ImpressionResult(False, "impression summary must contain 1..500 characters")
        if not update.reason.strip() or len(update.reason) > 500:
            return ImpressionResult(False, "impression reason must contain 1..500 characters")
        if not isfinite(update.significance) or not 0.0 <= update.significance <= 1.0:
            return ImpressionResult(False, "impression significance must be in [0, 1]")
        if not update.evidence_knowledge_ids:
            return ImpressionResult(False, "impression requires subjective evidence")
        if len(set(update.evidence_knowledge_ids)) != len(update.evidence_knowledge_ids):
            return ImpressionResult(False, "duplicate subjective evidence ids")
        if allowed_knowledge_ids is not None and any(
            item_id not in allowed_knowledge_ids for item_id in update.evidence_knowledge_ids
        ):
            return ImpressionResult(
                False,
                "impression evidence was not available to this conscious decision",
            )

        knowledge = {
            item.knowledge_id: item
            for item in self.heralds.knowledge_since(entity_id, 0)
        }
        missing = [item_id for item_id in update.evidence_knowledge_ids if item_id not in knowledge]
        if missing:
            return ImpressionResult(
                False,
                "impression evidence was never present in this deity's subjective knowledge",
            )

        key = summary.casefold()
        previous = self._items[entity_id].get(key)
        used_ids = set(previous.source_knowledge_ids) if previous is not None else set()
        reused_ids = tuple(sorted(used_ids.intersection(update.evidence_knowledge_ids)))
        novel_ids = tuple(sorted(set(update.evidence_knowledge_ids) - used_ids))
        if not novel_ids:
            return ImpressionResult(
                True,
                "no new subjective evidence; private impression unchanged",
                impression_id=previous.impression_id if previous else None,
                significance_before=previous.significance if previous else None,
                significance_after=previous.significance if previous else None,
                applied=False,
                ignored_reused_knowledge_ids=reused_ids,
            )

        minute = self.heralds.world.game_minute if game_minute is None else game_minute
        source_knowledge_ids = tuple(
            sorted(used_ids | set(novel_ids))
        )
        source_event_ids = tuple(
            sorted(
                {
                    event_id
                    for knowledge_id in source_knowledge_ids
                    for event_id in knowledge[knowledge_id].source_event_ids
                }
            )
        )

        if previous is None:
            self._sequence += 1
            revised = DivineImpression(
                impression_id=self._sequence,
                entity_id=entity_id,
                summary=summary,
                significance=update.significance,
                reason=" ".join(update.reason.split()),
                source_knowledge_ids=source_knowledge_ids,
                source_event_ids=source_event_ids,
                created_minute=minute,
                updated_minute=minute,
            )
            before = 0.0
        else:
            before = previous.significance
            revised = replace(
                previous,
                significance=update.significance,
                reason=" ".join(update.reason.split()),
                source_knowledge_ids=source_knowledge_ids,
                source_event_ids=source_event_ids,
                updated_minute=minute,
            )
        self._items[entity_id][key] = revised
        return ImpressionResult(
            True,
            f"private impression marked: {before:.3f} -> {revised.significance:.3f}",
            impression_id=revised.impression_id,
            significance_before=before,
            significance_after=revised.significance,
            applied=True,
            applied_evidence_knowledge_ids=novel_ids,
            ignored_reused_knowledge_ids=reused_ids,
        )

    @staticmethod
    def _alias(entity: str) -> str:
        return {"nature": "god_nature", "death": "god_death", "trade": "god_trade"}.get(entity, entity)

    def _entity_id(self, entity: str, *, strict: bool = True) -> str | None:
        entity_id = self._alias(entity)
        if entity_id in self._items:
            return entity_id
        if strict:
            raise KeyError(entity)
        return None
