from __future__ import annotations

import argparse
from pathlib import Path

from worldzero.affordance_trials import run_affordance_acceptance


def _render(result) -> str:
    passed = sum(check.ok for check in result.checks)
    lines = [
        "WORLD ZERO V0.0-D.2.2 — P4 PHYSICAL AFFORDANCES + LOCAL PERCEPTION ACCEPTANCE",
        "Lab policies are interface probes, not canonical Nereid or Trade cognition.",
        "Subjects receive private local percepts; authoritative Hydrology owns outcomes.",
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
            f"Local percepts: {len(result.bridge.perceptions.all_percepts)}",
            f"World-facing action traces: {len(result.bridge.action_traces)}",
            f"Hydrology ticks in focal run: {len(result.hydrology.traces)}",
            (
                "Bank counterfactual exposure (reinforced/unreinforced): "
                f"{result.reinforced_hydrology.state.burial_bank.exposure_fraction:.3f}/"
                f"{result.unreinforced_hydrology.state.burial_bank.exposure_fraction:.3f}"
            ),
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="World Zero D.2.2 P4 affordance acceptance")
    parser.add_argument("--days", type=int, default=30)
    parser.add_argument("--log-file")
    parser.add_argument("--percepts")
    parser.add_argument("--observation-provenance")
    parser.add_argument("--action-trace")
    parser.add_argument("--forensic-graph")
    parser.add_argument("--subjects")
    parser.add_argument("--hydrology-trace")
    parser.add_argument("--hydrology-state")
    parser.add_argument("--ledger")
    args = parser.parse_args()

    result = run_affordance_acceptance(elapsed_days=args.days)
    rendered = _render(result)
    print(rendered, end="")
    if args.log_file:
        Path(args.log_file).write_text(rendered, encoding="utf-8")
    if args.percepts:
        result.bridge.perceptions.export_percepts_jsonl(args.percepts)
    if args.observation_provenance:
        result.bridge.perceptions.export_provenance_jsonl(args.observation_provenance)
    if args.action_trace:
        result.bridge.export_action_trace_jsonl(args.action_trace)
    if args.forensic_graph:
        result.bridge.export_forensic_graph_json(args.forensic_graph)
    if args.subjects:
        result.bridge.export_subjects_json(args.subjects)
    if args.hydrology_trace:
        result.hydrology.export_trace_jsonl(args.hydrology_trace)
    if args.hydrology_state:
        result.hydrology.export_state_json(args.hydrology_state)
    if args.ledger:
        result.ledger.export_jsonl(args.ledger)
    return 0 if result.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
