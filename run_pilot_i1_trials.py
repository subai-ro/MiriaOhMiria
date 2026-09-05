from __future__ import annotations

import argparse
from pathlib import Path

from worldzero.pilot_i1_trials import run_pilot_i1_acceptance


def _render(result) -> str:
    passed = sum(check.ok for check in result.checks)
    lines = [
        "WORLD ZERO PILOT 0.1 - I1 INTERNAL PLAYABLE LOOP",
        "One PilotSession; autonomous prehistory; lawful Player View.",
        "H0/H1/H2 differ through visible and persistent divine behavior.",
        "",
    ]
    lines.extend(
        f"  [{'LAW +' if check.ok else 'LAW -'}] {check.name}: {check.detail}"
        for check in result.checks
    )
    lines.extend(
        [
            "",
            f"LAWS: {passed}/{len(result.checks)}",
            f"H0 visible words: {len(result.h0.loop.player_view().received_words)}",
            f"H1 visible words: {len(result.h1.loop.player_view().received_words)}",
            f"H2 visible words: {len(result.h2.loop.player_view().received_words)}",
            f"Settled world minute: {result.h2.loop.session.world.game_minute}",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="World Zero Pilot 0.1 I1 internal playable-loop acceptance"
    )
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--log-file")
    args = parser.parse_args()

    result = run_pilot_i1_acceptance(seed=args.seed)
    rendered = _render(result)
    print(rendered, end="")
    if args.log_file:
        Path(args.log_file).write_text(rendered, encoding="utf-8")
    return 0 if result.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
