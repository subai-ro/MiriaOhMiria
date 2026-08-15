from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from .ledger import WorldEvent
from .models import WorldState


@dataclass(frozen=True)
class ArchiveEntry:
    archive_id: int
    game_minute: int
    kind: str
    event_type: str
    source_event_ids: tuple[int, ...]
    actor_ids: tuple[str, ...]
    target_ids: tuple[str, ...]
    location_id: str
    tags: tuple[str, ...]
    summary: str

    def as_dict(self) -> dict:
        return {
            "archive_id": self.archive_id,
            "game_minute": self.game_minute,
            "kind": self.kind,
            "event_type": self.event_type,
            "source_event_ids": list(self.source_event_ids),
            "actor_ids": list(self.actor_ids),
            "target_ids": list(self.target_ids),
            "location_id": self.location_id,
            "tags": list(self.tags),
            "summary": self.summary,
        }


def _actor_names(world: WorldState, actor_ids: Iterable[str]) -> str:
    names = [world.actors[actor_id].name if actor_id in world.actors else actor_id for actor_id in actor_ids]
    return ", ".join(names) if names else "An unknown actor"


def _object_name(world: WorldState, target_ids: tuple[str, ...]) -> str:
    if not target_ids:
        return "an unspecified target"
    target = target_ids[0]
    if target in world.objects:
        return world.objects[target].name
    if target in world.regions:
        return world.regions[target].name
    return target


def describe_event(world: WorldState, event: WorldEvent, perceived_actor_ids: tuple[str, ...] | None = None) -> str:
    actors = event.actor_ids if perceived_actor_ids is None else perceived_actor_ids
    actor = _actor_names(world, actors)
    target = _object_name(world, event.target_ids)
    region = world.regions.get(event.location_id)
    region_name = region.name if region else event.location_id
    data = event.data

    if event.event_type == "TEMPLE_DESTROYED":
        return f"{actor} destroyed {target} in {region_name}."
    if event.event_type == "DEAD_RAISED":
        return f"{actor} raised the dead in {region_name}."
    if event.event_type == "NECROMANCY_STUDIED":
        return f"{actor} practiced necromantic study in {region_name}."
    if event.event_type == "FISHED":
        return f"{actor} fished at {target} using {data.get('tool', 'an unknown method')}."
    if event.event_type == "WOOD_HARVESTED":
        return f"{actor} harvested {data.get('amount', '?')} timber in {region_name}."
    if event.event_type == "ITEM_SOLD":
        return f"{actor} sold {data.get('quantity', '?')} {data.get('item', 'item')} in {region_name}."
    if event.event_type == "PRAYER_OFFERED":
        return f"{actor} offered a prayer to {data.get('deity', 'an unknown deity')} in {region_name}."
    if event.event_type == "DIEGETIC_SPEECH":
        return f"{actor} said: {data.get('text', '')}"
    if event.event_type == "TRAVELLED":
        origin = world.regions.get(str(data.get("from")))
        return f"{actor} travelled from {origin.name if origin else data.get('from')} to {region_name}."
    if event.event_type == "SITE_VISITED":
        return f"{actor} visited {target} in {region_name}."
    if event.event_type == "DIVINE_OMEN_SENT":
        target_actor_id = str(data.get("target_actor_id", "unknown"))
        target_actor = world.actors.get(target_actor_id)
        return f"A divine omen manifested around {target_actor.name if target_actor else target_actor_id} in {region_name}."
    if event.event_type == "DIVINE_PROBE_MANIFESTED":
        target_actor_id = str(data.get("target_actor_id", "unknown"))
        target_actor = world.actors.get(target_actor_id)
        return (
            "A deliberate divine probe manifested around "
            f"{target_actor.name if target_actor else target_actor_id} in {region_name}."
        )
    if event.event_type == "DIVINE_FAVOR_GRANTED":
        target_actor_id = str(data.get("target_actor_id", "unknown"))
        target_actor = world.actors.get(target_actor_id)
        return f"Divine favor touched {target_actor.name if target_actor else target_actor_id} in {region_name}."
    if event.event_type == "DIVINE_DREAD_IMPOSED":
        target_actor_id = str(data.get("target_actor_id", "unknown"))
        target_actor = world.actors.get(target_actor_id)
        return f"Divine dread touched {target_actor.name if target_actor else target_actor_id} in {region_name}."
    return f"{actor} caused {event.event_type} in {region_name}."


class Archive:
    """Semantic, provenance-preserving layer above the objective World Ledger."""

    def __init__(self) -> None:
        self._entries: list[ArchiveEntry] = []
        self._event_to_archive: dict[int, int] = {}

    @property
    def entries(self) -> tuple[ArchiveEntry, ...]:
        return tuple(self._entries)

    def add_event(self, world: WorldState, event: WorldEvent) -> ArchiveEntry:
        existing = self._event_to_archive.get(event.event_id)
        if existing is not None:
            return self._entries[existing - 1]

        entry = ArchiveEntry(
            archive_id=len(self._entries) + 1,
            game_minute=event.game_minute,
            kind="event",
            event_type=event.event_type,
            source_event_ids=(event.event_id,),
            actor_ids=event.actor_ids,
            target_ids=event.target_ids,
            location_id=event.location_id,
            tags=event.tags,
            summary=describe_event(world, event),
        )
        self._entries.append(entry)
        self._event_to_archive[event.event_id] = entry.archive_id
        return entry

    def add_derived(
        self,
        *,
        game_minute: int,
        event_type: str,
        source_event_ids: Iterable[int],
        location_id: str,
        tags: Iterable[str],
        summary: str,
        actor_ids: Iterable[str] = (),
        target_ids: Iterable[str] = (),
    ) -> ArchiveEntry:
        entry = ArchiveEntry(
            archive_id=len(self._entries) + 1,
            game_minute=game_minute,
            kind="derived",
            event_type=event_type,
            source_event_ids=tuple(source_event_ids),
            actor_ids=tuple(actor_ids),
            target_ids=tuple(target_ids),
            location_id=location_id,
            tags=tuple(sorted(set(tags))),
            summary=summary,
        )
        self._entries.append(entry)
        return entry

    def find(
        self,
        *,
        tags: Iterable[str] = (),
        actor_id: str | None = None,
        location_id: str | None = None,
        limit: int = 20,
    ) -> tuple[ArchiveEntry, ...]:
        required_tags = set(tags)
        matches = []
        for entry in reversed(self._entries):
            if required_tags and not required_tags.issubset(entry.tags):
                continue
            if actor_id and actor_id not in entry.actor_ids:
                continue
            if location_id and location_id != entry.location_id:
                continue
            matches.append(entry)
            if len(matches) >= limit:
                break
        return tuple(matches)

    def export_jsonl(self, path: str | Path) -> None:
        destination = Path(path)
        with destination.open("w", encoding="utf-8") as handle:
            for entry in self._entries:
                handle.write(json.dumps(entry.as_dict(), ensure_ascii=False, sort_keys=True) + "\n")
