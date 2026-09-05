from __future__ import annotations

import argparse
from pathlib import Path

from worldzero.pilot_trials import run_pilot_i0_acceptance


def _render(result) -> str:
    passed = sum(check.ok for check in result.checks)
    death = result.session.divine_runtime.agent("death")
    probes = result.session.divine_runtime.gateway.probes_for("god_death")
    lines = [
        "WORLD ZERO PILOT 0.1 - I0 DEATH GOD INTEGRATION SPIKE",
        "One PilotSession; one authoritative clock and Ledger; bounded divine inquiry.",
        "Arra has no water_sense and Death receives no Burial/Hydrology answer key.",
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
            f"World minute: {result.session.world.game_minute}",
            f"Death wake cycles: {death.state.wake_count}",
            f"Bounded probes: {len(probes)}",
            f"Ledger events: {len(result.session.ledger.events)}",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="World Zero Pilot 0.1 I0 Death God integration acceptance"
    )
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--log-file")
    args = parser.parse_args()

    result = run_pilot_i0_acceptance(seed=args.seed)
    rendered = _render(result)
    print(rendered, end="")
    if args.log_file:
        Path(args.log_file).write_text(rendered, encoding="utf-8")
    return 0 if result.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
