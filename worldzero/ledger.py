from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterable

from .perception import PerceptualBarrier


@dataclass(frozen=True)
class WorldEvent:
    event_id: int
    game_minute: int
    event_type: str
    actor_ids: tuple[str, ...]
    target_ids: tuple[str, ...]
    location_id: str
    tags: tuple[str, ...]
    witness_ids: tuple[str, ...]
    publicity: float
    secrecy: float
    data_json: str
    causal_parent_ids: tuple[int, ...] = ()
    perceptual_barriers: tuple[PerceptualBarrier, ...] = ()

    @property
    def data(self) -> dict[str, Any]:
        return json.loads(self.data_json)

    def as_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "game_minute": self.game_minute,
            "event_type": self.event_type,
            "actor_ids": list(self.actor_ids),
            "target_ids": list(self.target_ids),
            "location_id": self.location_id,
            "tags": list(self.tags),
            "witness_ids": list(self.witness_ids),
            "publicity": self.publicity,
            "secrecy": self.secrecy,
            "data": self.data,
            "causal_parent_ids": list(self.causal_parent_ids),
            "perceptual_barriers": [item.as_dict() for item in self.perceptual_barriers],
        }


class EventLedger:
    """Append-only objective history of meaningful world events."""

    def __init__(self) -> None:
        self._events: list[WorldEvent] = []
        self._listeners: list[Callable[[WorldEvent], None]] = []
        self._listener_errors: list[str] = []

    @property
    def events(self) -> tuple[WorldEvent, ...]:
        return tuple(self._events)

    @property
    def listener_errors(self) -> tuple[str, ...]:
        return tuple(self._listener_errors)

    def subscribe(self, listener: Callable[[WorldEvent], None]) -> None:
        self._listeners.append(listener)

    def append(
        self,
        *,
        game_minute: int,
        event_type: str,
        actor_ids: Iterable[str],
        target_ids: Iterable[str] = (),
        location_id: str,
        tags: Iterable[str] = (),
        witness_ids: Iterable[str] = (),
        publicity: float = 0.5,
        secrecy: float = 0.0,
        data: dict[str, Any] | None = None,
        causal_parent_ids: Iterable[int] = (),
        perceptual_barriers: Iterable[PerceptualBarrier] = (),
    ) -> WorldEvent:
        if not 0.0 <= publicity <= 1.0 or not 0.0 <= secrecy <= 1.0:
            raise ValueError("publicity and secrecy must be in [0, 1]")

        event = WorldEvent(
            event_id=len(self._events) + 1,
            game_minute=game_minute,
            event_type=event_type,
            actor_ids=tuple(actor_ids),
            target_ids=tuple(target_ids),
            location_id=location_id,
            tags=tuple(sorted(set(tags))),
            witness_ids=tuple(sorted(set(witness_ids))),
            publicity=publicity,
            secrecy=secrecy,
            data_json=json.dumps(data or {}, sort_keys=True, separators=(",", ":")),
            causal_parent_ids=tuple(causal_parent_ids),
            perceptual_barriers=tuple(perceptual_barriers),
        )
        self._events.append(event)
        for listener in tuple(self._listeners):
            try:
                listener(event)
            except Exception as exc:  # informational layers may not corrupt authoritative state
                self._listener_errors.append(f"event #{event.event_id}: {type(exc).__name__}: {exc}")
        return event

    def export_jsonl(self, path: str | Path) -> None:
        destination = Path(path)
        with destination.open("w", encoding="utf-8") as handle:
            for event in self._events:
                handle.write(json.dumps(event.as_dict(), ensure_ascii=False, sort_keys=True) + "\n")
