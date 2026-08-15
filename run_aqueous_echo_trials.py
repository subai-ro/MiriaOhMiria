from __future__ import annotations

import argparse
from pathlib import Path

from worldzero.aqueous_echo_trials import run_aqueous_echo_acceptance


def _render(result) -> str:
    passed = sum(check.ok for check in result.checks)
    lines = [
        "WORLD ZERO V0.0-D.2.3 — P4-B AQUEOUS SILVER ECHO ACCEPTANCE",
        "Hidden metaphysics is objective; local sensing is private and imperfect.",
        "The process reads material contact, never FISHED -> Nereid or quest logic.",
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
            f"Hydrology/Echo ticks: {len(result.hydrology.traces)}/{len(result.echo.traces)}",
            f"Resonant contacts in focal first tick: {len(result.echo.traces[0].resonant_contact_refs)}",
            f"Private echo-sense traces in exported focal run: {len(result.sensing.traces)}",
            (
                "Mirror/Whisper junction echo: "
                f"{result.diagnostics['mirror_junction']:.6f}/"
                f"{result.diagnostics['whisper_junction']:.6f}"
            ),
            (
                "Closed/Open deep-river echo: "
                f"{result.diagnostics['closed_deep']:.6f}/"
                f"{result.diagnostics['opened_deep']:.6f}"
            ),
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="World Zero D.2.3 P4-B aqueous silver echo acceptance"
    )
    parser.add_argument("--days", type=int, default=30)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--log-file")
    parser.add_argument("--echo-trace")
    parser.add_argument("--echo-state")
    parser.add_argument("--sense-trace")
    parser.add_argument("--forensic-graph")
    parser.add_argument("--percepts")
    parser.add_argument("--observation-provenance")
    parser.add_argument("--hydrology-trace")
    parser.add_argument("--ledger")
    args = parser.parse_args()

    result = run_aqueous_echo_acceptance(
        elapsed_days=args.days,
        seed=args.seed,
    )
    rendered = _render(result)
    print(rendered, end="")
    if args.log_file:
        Path(args.log_file).write_text(rendered, encoding="utf-8")
    if args.echo_trace:
        result.echo.export_trace_jsonl(args.echo_trace)
    if args.echo_state:
        result.echo.export_state_json(args.echo_state)
    if args.sense_trace:
        result.sensing.export_trace_jsonl(args.sense_trace)
    if args.forensic_graph:
        result.sensing.export_forensic_graph_json(args.forensic_graph)
    if args.percepts:
        result.bridge.perceptions.export_percepts_jsonl(args.percepts)
    if args.observation_provenance:
        result.bridge.perceptions.export_provenance_jsonl(
            args.observation_provenance
        )
    if args.hydrology_trace:
        result.hydrology.export_trace_jsonl(args.hydrology_trace)
    if args.ledger:
        result.ledger.export_jsonl(args.ledger)
    return 0 if result.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
