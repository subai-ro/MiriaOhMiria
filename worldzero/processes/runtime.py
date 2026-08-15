from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from ..models import WorldState


class WorldProcess(Protocol):
    """A deterministic authoritative process advanced on its own fixed clock."""

    process_id: str
    tick_interval_minutes: int

    def tick(self, game_minute: int) -> None: ...


@dataclass(frozen=True)
class ProcessRun:
    process_id: str
    game_minute: int


class WorldProcessRuntime:
    """Runs registered physical processes without skipping fixed-time boundaries.

    The runtime deliberately does not swallow exceptions. A failed divine or NPC
    thought may be survivable; silently skipping authoritative physics is not.
    """

    def __init__(self, *, start_minute: int = 0) -> None:
        if start_minute < 0:
            raise ValueError("start_minute cannot be negative")
        self.current_minute = start_minute
        self._processes: dict[str, WorldProcess] = {}
        self._next_tick: dict[str, int] = {}
        self._runs: list[ProcessRun] = []
        self._attached_world: WorldState | None = None

    @property
    def runs(self) -> tuple[ProcessRun, ...]:
        return tuple(self._runs)

    @property
    def process_ids(self) -> tuple[str, ...]:
        return tuple(sorted(self._processes))

    def register(self, process: WorldProcess) -> None:
        process_id = " ".join(process.process_id.split())
        if not process_id:
            raise ValueError("process_id cannot be empty")
        if process_id in self._processes:
            raise ValueError(f"World process already registered: {process_id}")
        if process.tick_interval_minutes <= 0:
            raise ValueError("world process tick interval must be positive")
        self._processes[process_id] = process
        interval = process.tick_interval_minutes
        self._next_tick[process_id] = ((self.current_minute // interval) + 1) * interval

    def attach(self, world: WorldState) -> None:
        if self._attached_world is not None and self._attached_world is not world:
            raise ValueError("WorldProcessRuntime is already attached to another world")
        if world.game_minute < self.current_minute:
            raise ValueError("cannot attach a process runtime ahead of the world clock")
        if world.game_minute > self.current_minute:
            self.advance_to(world.game_minute)
        self._attached_world = world
        world.subscribe_time_advance(self.advance_to)

    def advance_to(self, game_minute: int) -> tuple[ProcessRun, ...]:
        if game_minute < self.current_minute:
            raise ValueError("world process clock cannot move backward")

        start_index = len(self._runs)
        while self._processes:
            next_minute = min(self._next_tick.values())
            if next_minute > game_minute:
                break
            due_ids = sorted(
                process_id
                for process_id, minute in self._next_tick.items()
                if minute == next_minute
            )
            for process_id in due_ids:
                process = self._processes[process_id]
                process.tick(next_minute)
                self._runs.append(ProcessRun(process_id=process_id, game_minute=next_minute))
                self._next_tick[process_id] += process.tick_interval_minutes
        self.current_minute = game_minute
        return tuple(self._runs[start_index:])
