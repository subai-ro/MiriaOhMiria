from __future__ import annotations

from dataclasses import dataclass

from .ledger import WorldEvent


@dataclass(frozen=True)
class AttentionDirective:
    actor_id: str
    intensity: float
    reason: str = ""
    causal_event_ids: tuple[int, ...] = ()


@dataclass(frozen=True)
class PersonalAttentionThread:
    thread_id: int
    entity_id: str
    actor_id: str
    intensity: float
    created_minute: int
    updated_minute: int
    reason: str
    causal_event_ids: tuple[int, ...]


class PersonalAttentionField:
    """Weak person-bound strands of divine attention; not a location oracle."""

    def __init__(self) -> None:
        self._threads: dict[str, dict[str, PersonalAttentionThread]] = {}
        self._sequence = 0

    def threads(self, entity_id: str) -> tuple[PersonalAttentionThread, ...]:
        values = self._threads.get(entity_id, {}).values()
        return tuple(sorted(values, key=lambda item: item.actor_id))

    def allocations(self, entity_id: str) -> dict[str, float]:
        return {item.actor_id: item.intensity for item in self.threads(entity_id)}

    def strength_for_actor(self, entity_id: str, actor_id: str) -> float:
        thread = self._threads.get(entity_id, {}).get(actor_id)
        return thread.intensity if thread else 0.0

    def strength_for_event(self, entity_id: str, event: WorldEvent) -> float:
        return max(
            (self.strength_for_actor(entity_id, actor_id) for actor_id in event.actor_ids),
            default=0.0,
        )

    def replace(
        self,
        entity_id: str,
        directives: tuple[AttentionDirective, ...],
        game_minute: int,
    ) -> None:
        previous = self._threads.get(entity_id, {})
        replacement: dict[str, PersonalAttentionThread] = {}
        for directive in directives:
            if directive.intensity <= 0.0:
                continue
            old = previous.get(directive.actor_id)
            if old is None:
                self._sequence += 1
                thread_id = self._sequence
                created_minute = game_minute
            else:
                thread_id = old.thread_id
                created_minute = old.created_minute
            replacement[directive.actor_id] = PersonalAttentionThread(
                thread_id=thread_id,
                entity_id=entity_id,
                actor_id=directive.actor_id,
                intensity=directive.intensity,
                created_minute=created_minute,
                updated_minute=game_minute,
                reason=directive.reason,
                causal_event_ids=directive.causal_event_ids,
            )
        self._threads[entity_id] = replacement
