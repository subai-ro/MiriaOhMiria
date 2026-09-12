"""Opt-in bounded internal play with local Nereid, not the frozen I1 entry."""
import argparse
from pathlib import Path

from worldzero.neural import OllamaChatTransport
from worldzero.pilot_nereid_neural import local_model_preflight
from worldzero.pilot_nereid_playtest import CALL_LIMIT, MODEL_DIGEST, NereidPlaytest
from worldzero.pilot_playable import render_player_view


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--approved-local-playtest", action="store_true")
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()
    if not args.approved_local_playtest:
        parser.error("explicit approval of one bounded local playtest is required")
    root = Path(__file__).resolve().parent / "local_acceptance"
    output = Path(args.output_dir).resolve()
    if root.resolve() not in output.parents or output.exists():
        parser.error("choose a NEW child directory under local_acceptance")
    try:
        metadata = local_model_preflight()
    except Exception:
        parser.error("local model unavailable; no download, fallback or automatic retry")
    if metadata["digest"] != MODEL_DIGEST:
        parser.error("installed model differs from the approved baseline; no substitution")
    print(f"Internal playtest: at most {CALL_LIMIT} local calls including prehistory.", flush=True)
    print("Time advances through actions and waits, not while you type. No guaranteed outcome.", flush=True)
    print("Preparing the older-world opening...", flush=True)
    play = NereidPlaytest(output, provider=OllamaChatTransport(seed=42), provider_metadata=metadata)
    reason = "quit"
    checked = None
    try:
        play.start()
        print(render_player_view(play.loop.player_view()), flush=True)
        while not play.closed:
            try:
                command = input("\n> ").strip()
            except EOFError:
                reason = "EOF"
                break
            if command.casefold() in {"quit", "exit", "q"}:
                break
            print("Resolving your request...", flush=True)
            result = play.execute(command)
            if result is not None:
                print(result.message)
                if result.minutes_elapsed:
                    print(f"Elapsed: {result.minutes_elapsed} minutes.")
            print(render_player_view(play.loop.player_view()), flush=True)
    except KeyboardInterrupt:
        reason = "interrupted"
    except Exception:
        reason = "session error"
        print("The internal session was interrupted; no automatic restart.", flush=True)
    finally:
        try:
            checked = play.finish(reason)
            print("Internal session ended. No further world time is simulated.", flush=True)
            print(f"Post-session evidence: {output}", flush=True)
            print(f"Saved replay matches: {checked['matches']}", flush=True)
        except Exception:
            print("Evidence finalization failed. Keep the partial directory; do not restart over it.", flush=True)
            checked = None
    return 0 if checked and checked["matches"] and not play.stop_reason and reason in {"quit", "EOF"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
