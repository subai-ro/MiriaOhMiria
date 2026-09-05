"""Offline lab acceptance runner; never connects to a model provider."""
import argparse

from worldzero.pilot_nereid_trials import export_lab_report, run_nereid_trials


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output-dir", help="new local_acceptance subdirectory; never overwrite evidence")
    args = parser.parse_args()
    branches, checks = run_nereid_trials(args.seed)
    print("OFFLINE LAB DOUBLES — NOT CANONICAL COGNITION / NOT HUMAN GATE")
    for check in checks:
        print(f'{"PASS" if check.ok else "FAIL"} {check.name}: {check.detail}')
    print(f"N1-N3 end-to-end: {sum(c.ok for c in checks)}/{len(checks)} checks")
    if args.output_dir:
        print(export_lab_report(args.output_dir, branches, checks))
    return 0 if all(c.ok for c in checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
