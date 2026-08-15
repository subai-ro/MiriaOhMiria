from __future__ import annotations

import argparse
from pathlib import Path

from worldzero.hydrology_trials import run_hydrology_acceptance


def _render(result) -> str:
    passed = sum(check.ok for check in result.checks)
    lines = [
        "WORLD ZERO V0.0-D.2.1 — P3 WORLD PROCESS + HYDROLOGY ACCEPTANCE",
        "Lab Nereid cognition remains an acceptance double; physics is authoritative.",
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
            f"Hydrology ticks: {len(result.hydrology.traces)}",
            f"Project decisions/intents/resolutions: {len(result.project_trace.decisions)}/{len(result.project_trace.intents)}/{len(result.project_trace.resolutions)}",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="World Zero D.2.1 P3 hydrology acceptance")
    parser.add_argument("--days", type=int, default=30)
    parser.add_argument("--log-file")
    parser.add_argument("--hydrology-trace")
    parser.add_argument("--hydrology-state")
    parser.add_argument("--project-trace")
    parser.add_argument("--project-graph")
    parser.add_argument("--projects")
    parser.add_argument("--ledger")
    args = parser.parse_args()

    result = run_hydrology_acceptance(elapsed_days=args.days)
    rendered = _render(result)
    print(rendered, end="")
    if args.log_file:
        Path(args.log_file).write_text(rendered, encoding="utf-8")
    if args.hydrology_trace:
        result.hydrology.export_trace_jsonl(args.hydrology_trace)
    if args.hydrology_state:
        result.hydrology.export_state_json(args.hydrology_state)
    if args.project_trace:
        result.project_trace.export_jsonl(args.project_trace)
    if args.project_graph:
        result.project_trace.export_graph_json(args.project_graph)
    if args.projects:
        result.projects.export_jsonl(args.projects)
    if args.ledger:
        result.ledger.export_jsonl(args.ledger)
    return 0 if result.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
