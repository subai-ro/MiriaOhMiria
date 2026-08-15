from __future__ import annotations

import argparse
from pathlib import Path

from worldzero.project_trials import run_no_player_prehistory_trial


def _render(result) -> str:
    passed = sum(1 for check in result.checks if check.ok)
    lines = [
        "WORLD ZERO V0.0-D.2.0 — PERSISTENT PROJECT ACCEPTANCE",
        f"Prehistory: {result.elapsed_days} elapsed days; player-controlled actions: 0",
        "LabNereidMind is an acceptance double, not canonical Nereid behavior.",
        "",
    ]
    for check in result.checks:
        lines.append(f"  [{'LAW +' if check.ok else 'LAW -'}] {check.name}: {check.detail}")
    nereid = result.projects.get("nereid_return_underpeak")
    trade = result.projects.get("trade_house_underpeak_route")
    lines.extend(
        [
            "",
            f"LAWS: {passed}/{len(result.checks)}",
            f"Nereid project: status={nereid.status.value}; attempts={len(nereid.attempt_history)}; revision={nereid.revision}",
            f"Trade House project: status={trade.status.value}; attempts={len(trade.attempt_history)}; revision={trade.revision}",
            f"Trace: decisions={len(result.trace.decisions)}; intents={len(result.trace.intents)}; resolutions={len(result.trace.resolutions)}; edges={len(result.trace.edges())}",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="World Zero D.2.0 — offline PersistentProject + causal provenance acceptance"
    )
    parser.add_argument("--days", type=int, default=30)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--log-file")
    parser.add_argument("--trace-file")
    parser.add_argument("--graph-file")
    parser.add_argument("--projects-file")
    parser.add_argument("--ledger-file")
    args = parser.parse_args()

    result = run_no_player_prehistory_trial(seed=args.seed, elapsed_days=args.days)
    rendered = _render(result)
    print(rendered, end="")

    if args.log_file:
        Path(args.log_file).write_text(rendered, encoding="utf-8")
    if args.trace_file:
        result.trace.export_jsonl(args.trace_file)
    if args.graph_file:
        result.trace.export_graph_json(args.graph_file)
    if args.projects_file:
        result.projects.export_jsonl(args.projects_file)
    if args.ledger_file:
        result.engine.ledger.export_jsonl(args.ledger_file)
    return 0 if result.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
