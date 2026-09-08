from __future__ import annotations

import argparse
from typing import Final

from worldzero.pilot_playable import create_pilot_i1_loop, render_player_view

STATUS_ONLY_COMMANDS: Final[set[str]] = {
    "help",
    "h",
    "?",
    "map",
    "viz",
    "v",
    "hud",
    "status",
    "panel",
    "journal",
    "j",
}


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Play the internal World Zero Pilot 0.1 I1 terminal loop"
    )
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--prehistory-minutes", type=int, default=12 * 60)
    parser.add_argument("--serial-actions", action="store_true")
    args = parser.parse_args()

    loop = create_pilot_i1_loop(
        seed=args.seed,
        prehistory_minutes=args.prehistory_minutes,
        serial_actions=args.serial_actions,
    )
    print("WORLD ZERO PILOT 0.1 - THE UNDERPEAK REACH")
    print("The world has already been moving without you. Type help for commands.")
    print()
    print(render_player_view(loop.player_view()))

    while True:
        try:
            command = input("\n> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nYou leave. The world does not stop.")
            return 0
        if command.casefold() in {"quit", "exit", "q"}:
            print("You leave. The world does not stop.")
            return 0
        normalized = " ".join(command.strip().split())
        verb = normalized.casefold().partition(" ")[0]
        result = loop.execute(command)
        print(result.message)
        if result.ok and verb not in STATUS_ONLY_COMMANDS:
            print()
            print(render_player_view(loop.player_view()))


if __name__ == "__main__":
    raise SystemExit(main())
