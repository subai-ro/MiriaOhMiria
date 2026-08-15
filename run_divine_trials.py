from __future__ import annotations

import argparse
import sys
from collections.abc import Callable
from pathlib import Path
from typing import TextIO

from worldzero.neural import (
    DEFAULT_LOCAL_CONTEXT_TOKENS,
    DEFAULT_LOCAL_MODEL,
    DEFAULT_OPENAI_MODEL,
    OLLAMA_CHAT_ENDPOINT,
    NeuralConfigurationError,
    NeuralDeathGodBrain,
    create_local_death_god_brain,
    create_openai_death_god_brain,
)
from worldzero.trials import TRIAL_IDS, DivineTrialResult, DivineTrialRunner


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="World Zero V0.0-D.1.4.2 — Stabilize & Freeze: plural divine-inquiry lab"
    )
    parser.add_argument("--backend", choices=("local", "openai"), default="local")
    parser.add_argument("--model", default=None, help="Model override for the selected backend")
    parser.add_argument(
        "--trial",
        action="append",
        choices=TRIAL_IDS,
        help="Run only this trial (repeat the flag to select several)",
    )
    parser.add_argument("--repeat", type=int, default=1, help="Repeat the selected suite N times")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--local-seed",
        type=int,
        default=None,
        help="Base Ollama sampling seed (default: use --seed; each repeat adds 1)",
    )
    parser.add_argument("--max-output-tokens", type=int, default=1800)
    parser.add_argument(
        "--reasoning-effort",
        choices=("none", "low", "medium", "high", "xhigh", "max"),
        default="low",
        help="OpenAI backend only",
    )
    parser.add_argument("--local-endpoint", default=OLLAMA_CHAT_ENDPOINT)
    parser.add_argument("--local-temperature", type=float, default=0.15)
    parser.add_argument(
        "--local-context",
        type=int,
        default=DEFAULT_LOCAL_CONTEXT_TOKENS,
        help=f"Ollama context window in tokens (default: {DEFAULT_LOCAL_CONTEXT_TOKENS})",
    )
    parser.add_argument("--local-timeout", type=float, default=180.0)
    parser.add_argument(
        "--log-file",
        default=None,
        help="Also write the complete trial log directly as UTF-8, bypassing shell recoding",
    )
    parser.add_argument("--list", action="store_true", help="List trial ids and exit")
    args = parser.parse_args()
    if args.repeat < 1:
        parser.error("--repeat must be >= 1")
    if args.max_output_tokens < 256:
        parser.error("--max-output-tokens must be >= 256")
    if not 0.0 <= args.local_temperature <= 2.0:
        parser.error("--local-temperature must be in [0, 2]")
    if args.local_context <= 0:
        parser.error("--local-context must be positive")
    if args.local_timeout <= 0.0:
        parser.error("--local-timeout must be positive")
    if args.local_seed is not None and args.local_seed < 0:
        parser.error("--local-seed must be non-negative")
    return args


class TeeTextIO:
    """Mirror Python text to the console and a directly encoded forensic log."""

    def __init__(self, console: TextIO, log: TextIO) -> None:
        self.console = console
        self.log = log

    def write(self, value: str) -> int:
        self.console.write(value)
        self.log.write(value)
        return len(value)

    def flush(self) -> None:
        self.console.flush()
        self.log.flush()

    def isatty(self) -> bool:
        return self.console.isatty()


def make_brain_factory(
    args: argparse.Namespace,
    *,
    local_seed: int | None = None,
) -> tuple[str, Callable[[], NeuralDeathGodBrain]]:
    if args.backend == "local":
        model = args.model or DEFAULT_LOCAL_MODEL

        def create() -> NeuralDeathGodBrain:
            return create_local_death_god_brain(
                model=model,
                max_output_tokens=args.max_output_tokens,
                endpoint=args.local_endpoint,
                timeout_seconds=args.local_timeout,
                temperature=args.local_temperature,
                context_tokens=args.local_context,
                seed=local_seed,
            )

        return model, create

    model = args.model or DEFAULT_OPENAI_MODEL

    def create() -> NeuralDeathGodBrain:
        return create_openai_death_god_brain(
            model=model,
            reasoning_effort=args.reasoning_effort,
            max_output_tokens=args.max_output_tokens,
        )

    return model, create


def print_result(result: DivineTrialResult, index: int) -> None:
    status = "LAW PASS" if result.hard_pass else "LAW FAIL"
    print(f"\n[{index:02d}] {result.title} ({result.trial_id}) — {status}")
    print(f"  {result.premise}")
    print(f"  Wake: {result.wake_reason} | game minute={result.wake_game_minute}")
    for check in result.checks:
        kind = "LAW" if check.required else "SIGNAL"
        mark = "+" if check.passed else "-"
        print(f"  [{kind} {mark}] {check.name}: {check.detail}")
    print(f"  Goal: {result.goal}")
    print(f"  Judgment: {result.decision_note}")
    for observation in result.observations:
        print(f"  · {observation}")
    performance = []
    if result.latency_seconds is not None:
        performance.append(f"wake={result.latency_seconds:.2f}s")
    if result.load_seconds is not None:
        performance.append(f"load={result.load_seconds:.2f}s")
    if result.prompt_eval_seconds is not None:
        prompt = f"prompt={result.prompt_eval_seconds:.2f}s"
        if result.prompt_tokens_per_second is not None:
            prompt += f" ({result.prompt_tokens_per_second:.1f} tok/s)"
        performance.append(prompt)
    if result.generation_seconds is not None:
        generation = f"generation={result.generation_seconds:.2f}s"
        if result.generation_tokens_per_second is not None:
            generation += f" ({result.generation_tokens_per_second:.1f} tok/s)"
        performance.append(generation)
    if result.input_tokens is not None or result.output_tokens is not None:
        performance.append(f"tokens={result.input_tokens or 0}/{result.output_tokens or 0}")
    if result.finish_reason is not None:
        performance.append(f"finish={result.finish_reason}")
    if performance:
        print(f"  Performance: {' | '.join(performance)}")
    if result.request_fingerprints:
        print(f"  Requests: {','.join(result.request_fingerprints)}")
    if result.context_omissions:
        print(f"  Context compaction: {','.join(result.context_omissions)}")


def main() -> None:
    # Preserve the host-selected stream encoding. Forcing UTF-8 bytes here is
    # unsafe under legacy Windows PowerShell pipelines, which may decode native
    # stdout using an OEM code page before Tee-Object sees it.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="backslashreplace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(errors="backslashreplace")
    args = parse_args()
    original_stdout = sys.stdout
    log_handle: TextIO | None = None
    if args.log_file:
        log_path = Path(args.log_file).expanduser()
        log_handle = log_path.open("w", encoding="utf-8", errors="strict", newline="\n")
        sys.stdout = TeeTextIO(original_stdout, log_handle)  # type: ignore[assignment]
    try:
        _run(args)
    finally:
        if log_handle is not None:
            sys.stdout = original_stdout
            log_handle.close()


def _run(args: argparse.Namespace) -> None:
    if args.list:
        print("\n".join(TRIAL_IDS))
        return
    base_local_seed = args.seed if args.local_seed is None else args.local_seed
    try:
        model, factory = make_brain_factory(args, local_seed=base_local_seed)
        # Construct once to surface configuration errors (for example a missing
        # OpenAI key) before a multi-trial run. No network request occurs here.
        factory()
    except NeuralConfigurationError as exc:
        raise SystemExit(f"Brain configuration error: {exc}") from exc

    selected = tuple(args.trial) if args.trial else TRIAL_IDS
    print("WORLD ZERO V0.0-D.1.4.2 — DIVINE TRIALS: STABILIZE & FREEZE")
    print(f"Backend: {args.backend} | model: {model} | trials: {len(selected)} x {args.repeat}")
    if args.backend == "local":
        print(
            f"Ollama: {args.local_endpoint} | temperature={args.local_temperature:.2f} "
            f"| context={args.local_context} | sampling seed base={base_local_seed}"
        )
    print("LAW checks are invariants. SIGNAL checks are behavioral diagnostics, not correctness rules.")

    all_results: list[DivineTrialResult] = []
    for repetition in range(args.repeat):
        experiment_seed = args.seed + repetition
        local_seed = base_local_seed + repetition
        _, repetition_factory = make_brain_factory(args, local_seed=local_seed)
        if args.backend == "local":
            print(
                f"\nEXPERIMENT REPEAT {repetition + 1}/{args.repeat} "
                f"| world seed={experiment_seed} | Ollama seed={local_seed}"
            )
        else:
            print(
                f"\nEXPERIMENT REPEAT {repetition + 1}/{args.repeat} "
                f"| world seed={experiment_seed}"
            )
        runner = DivineTrialRunner(repetition_factory, seed=experiment_seed)
        batch = runner.run(selected)
        for result in batch:
            all_results.append(result)
            print_result(result, len(all_results))

    laws_passed = sum(item.laws_passed for item in all_results)
    laws_total = sum(item.laws_total for item in all_results)
    signals_positive = sum(item.signals_positive for item in all_results)
    signals_total = sum(item.signals_total for item in all_results)
    total_latency = sum(item.latency_seconds or 0.0 for item in all_results)
    total_load = sum(item.load_seconds or 0.0 for item in all_results)
    total_prompt_eval = sum(item.prompt_eval_seconds or 0.0 for item in all_results)
    total_generation = sum(item.generation_seconds or 0.0 for item in all_results)
    total_input = sum(item.input_tokens or 0 for item in all_results)
    total_output = sum(item.output_tokens or 0 for item in all_results)
    print("\nDIVINE TRIALS SUMMARY")
    print(f"  Laws: {laws_passed}/{laws_total}")
    print(f"  Behavioral signals: {signals_positive}/{signals_total} (fingerprint, not a pass grade)")
    print(f"  Model wake time: {total_latency:.2f}s")
    if any(item.load_seconds is not None for item in all_results):
        print(
            f"  Ollama phases: load={total_load:.2f}s | prompt={total_prompt_eval:.2f}s "
            f"| generation={total_generation:.2f}s"
        )
    if total_input or total_output:
        print(f"  Tokens in/out: {total_input}/{total_output}")


if __name__ == "__main__":
    main()
