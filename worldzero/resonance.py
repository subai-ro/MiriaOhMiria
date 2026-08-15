from __future__ import annotations

from dataclasses import dataclass
import re

from .heralds import DivineKnowledge


@dataclass(frozen=True)
class MythicMotif:
    """A cheap search lens for potentially interesting conjunctions.

    A motif is not a metaphysical truth and carries no divine significance by
    itself.  It only tells the subjective Archive which co-occurrences are
    worth presenting together for a deity's own judgment.
    """

    motif_id: str
    cue_event_type: str
    cue_terms: tuple[str, ...]
    context_event_types: tuple[str, ...]
    window_minutes: int
    label: str


@dataclass(frozen=True)
class ContextualResonance:
    resonance_id: str
    motif_id: str
    label: str
    location_id: str
    cue_knowledge_ids: tuple[int, ...]
    context_knowledge_ids: tuple[int, ...]
    evidence_knowledge_ids: tuple[int, ...]
    known_actor_ids: tuple[str, ...]
    matched_pairs: int
    summary: str


DEATH_MOTIFS = (
    MythicMotif(
        motif_id="liminal_chill_near_dead",
        cue_event_type="DIEGETIC_SPEECH",
        cue_terms=(
            "cold",
            "colder",
            "chill",
            "chilled",
            "chilly",
            "freezing",
            "frost",
            "холод",
            "холодно",
            "холоднее",
            "мороз",
            "морозно",
            "озноб",
        ),
        context_event_types=("DEAD_RAISED",),
        window_minutes=60,
        label="chill-language near a perceived disturbance of the dead",
    ),
)


class ContextualResonanceEngine:
    """Find conjunctions in already-subjective knowledge, never WorldState.

    D.1.3 deliberately starts with one designer-seeded mythic lens.  The
    mechanism is generic: later lenses can be sourced from World Zero history,
    deity-specific doctrine, statistical associations, or curated occult and
    folkloric inspiration without changing the epistemic boundary.
    """

    def __init__(self, motifs: tuple[MythicMotif, ...] = DEATH_MOTIFS) -> None:
        self.motifs = motifs

    def detect(
        self,
        entity_id: str,
        knowledge: tuple[DivineKnowledge, ...],
    ) -> tuple[ContextualResonance, ...]:
        # The entity id is intentionally used only as part of a stable opaque
        # resonance handle. There is no lookup back into objective world state.
        ordered = tuple(
            sorted(
                {item.knowledge_id: item for item in knowledge}.values(),
                key=lambda item: item.knowledge_id,
            )
        )
        found: list[ContextualResonance] = []
        for motif in self.motifs:
            cues = tuple(
                item
                for item in ordered
                if item.event_type == motif.cue_event_type
                and any(_contains_term(item.summary, term) for term in motif.cue_terms)
            )
            contexts = tuple(
                item for item in ordered if item.event_type in motif.context_event_types
            )
            locations = sorted({item.location_id for item in cues if item.location_id})
            for location_id in locations:
                pairs = [
                    (cue, context)
                    for cue in cues
                    for context in contexts
                    if cue.location_id == location_id
                    and context.location_id == location_id
                    and abs(cue.game_minute - context.game_minute) <= motif.window_minutes
                ]
                if not pairs:
                    continue
                cue_ids = tuple(sorted({cue.knowledge_id for cue, _ in pairs}))
                context_ids = tuple(sorted({context.knowledge_id for _, context in pairs}))
                evidence_ids = tuple(sorted(set(cue_ids + context_ids)))
                known_actor_ids = tuple(
                    sorted(
                        {
                            actor_id
                            for item in ordered
                            if item.knowledge_id in evidence_ids
                            for actor_id in item.known_actor_ids
                        }
                    )
                )
                found.append(
                    ContextualResonance(
                        resonance_id=f"resonance:{entity_id}:{motif.motif_id}:{location_id}",
                        motif_id=motif.motif_id,
                        label=motif.label,
                        location_id=location_id,
                        cue_knowledge_ids=cue_ids,
                        context_knowledge_ids=context_ids,
                        evidence_knowledge_ids=evidence_ids,
                        known_actor_ids=known_actor_ids,
                        matched_pairs=len(pairs),
                        summary=(
                            f"{len(cue_ids)} chill-related utterance(s) in {location_id} occurred within "
                            f"{motif.window_minutes} minutes of {len(context_ids)} subjectively perceived "
                            f"disturbance(s) of the dead; {len(pairs)} matched pairing(s)."
                        ),
                    )
                )
        return tuple(found)


def _contains_term(text: str, term: str) -> bool:
    """Match a lexical cue without accidental substrings such as 'scolded'."""
    return re.search(rf"(?<!\w){re.escape(term.casefold())}(?!\w)", text.casefold()) is not None
