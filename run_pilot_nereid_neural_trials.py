"""Run only the explicitly approved initial N4 local-model batch."""
import argparse
import json
from pathlib import Path

from worldzero.pilot_nereid_neural import local_model_preflight, run_experiment


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--approved-local-experiment", action="store_true",
                        help="operator acknowledgement; never infer user approval from this flag")
    parser.add_argument("--output-dir", required=True, help="new directory under local_acceptance")
    args = parser.parse_args()
    if not args.approved_local_experiment:
        parser.error("explicit approval of the N4 plan is required before running a provider")
    output = Path(args.output_dir).resolve()
    local = (Path(__file__).resolve().parent / "local_acceptance").resolve()
    if local not in output.parents:
        parser.error("output must be a new child directory under this repository's local_acceptance")
    metadata = local_model_preflight()
    summary = run_experiment(output, progress=lambda line: print(line, flush=True), provider_metadata=metadata)
    print(json.dumps(summary, ensure_ascii=True, indent=2), flush=True)
    return 0 if summary["structural_floor_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
