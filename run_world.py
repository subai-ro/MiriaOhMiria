from __future__ import annotations

import argparse
from collections import Counter
import sys

from worldzero.affordances import PhysicalAffordanceBridge, create_silver_thread_affordance_bridge
from worldzero.archive import Archive
from worldzero.divine import DivineRuntime, create_prototype_divine_runtime
from worldzero.engine import WorldEngine
from worldzero.heralds import HeraldSystem
from worldzero.ledger import EventLedger
from worldzero.interactive import interactive_loop
from worldzero.models import Action, ActionType
from worldzero.neural import (
    DEFAULT_LOCAL_CONTEXT_TOKENS,
    DEFAULT_LOCAL_MODEL,
    DEFAULT_OPENAI_MODEL,
    NeuralConfigurationError,
    NeuralDeathGodBrain,
    OLLAMA_CHAT_ENDPOINT,
    OllamaChatTransport,
    create_local_death_god_brain,
    create_openai_death_god_brain,
)
from worldzero.project_runtime import ProjectRuntime
from worldzero.projects import PersistentProjectStore, seed_silver_thread_projects
from worldzero.processes import HydrologyProcess, WorldProcessRuntime, create_silver_thread_hydrology
from worldzero.processes.aqueous_echo import (
    AqueousEchoSenseBridge,
    AqueousSilverEchoProcess,
    create_silver_thread_aqueous_echo,
    create_silver_thread_echo_sense_bridge,
)
from worldzero.provenance import CausalTrace
from worldzero.seed import create_world
from worldzero.simulation import Simulation, run_arra_demo


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="World Zero V0.0-D.2.3 — Aqueous Silver Echo")
    parser.add_argument("--seed", type=int, default=42, help="Deterministic world seed")
    parser.add_argument("--actors", type=int, default=30, help="Number of synthetic actors")
    parser.add_argument("--start-day", type=int, default=1, help="Initial game day (use 10 to test Day of the Dead)")
    parser.add_argument("--steps", type=int, default=0, help="Simulation steps after optional demo")
    parser.add_argument("--minutes-per-step", type=int, default=10, help="Game minutes per simulation step")
    parser.add_argument("--demo", action="store_true", help="Run Arra's scripted signal sequence first")
    parser.add_argument(
        "--belief-demo",
        action="store_true",
        help="Secretly destroy the Death temple with sim_002 so innocent Arra can become a false suspect",
    )
    parser.add_argument("--interactive", action="store_true", help="Control Arra from a small text interface")
    parser.add_argument("--no-divine-agent", action="store_true", help="Run without the God of Death thinking agent")
    parser.add_argument(
        "--brain",
        choices=("rule", "local", "openai", "neural"),
        default="rule",
        help="God of Death brain: rules, local Ollama, or OpenAI ('neural' remains an alias for openai)",
    )
    parser.add_argument(
        "--model",
        default=None,
        help=(
            "Model override. Defaults: "
            f"{DEFAULT_LOCAL_MODEL} for --brain local; {DEFAULT_OPENAI_MODEL} for --brain openai"
        ),
    )
    parser.add_argument(
        "--reasoning-effort",
        choices=("none", "low", "medium", "high", "xhigh", "max"),
        default="low",
        help="Reasoning effort for neural wake cycles (default: low)",
    )
    parser.add_argument(
        "--local-endpoint",
        default=OLLAMA_CHAT_ENDPOINT,
        help=f"Ollama /api/chat endpoint (default: {OLLAMA_CHAT_ENDPOINT})",
    )
    parser.add_argument(
        "--local-temperature",
        type=float,
        default=0.15,
        help="Sampling temperature for the local God Brain (default: 0.15)",
    )
    parser.add_argument(
        "--local-context",
        type=int,
        default=DEFAULT_LOCAL_CONTEXT_TOKENS,
        help=f"Ollama context window in tokens (default: {DEFAULT_LOCAL_CONTEXT_TOKENS})",
    )
    parser.add_argument(
        "--local-timeout",
        type=float,
        default=180.0,
        help="Seconds allowed for one local wake cycle (default: 180)",
    )
    parser.add_argument(
        "--neural-max-output-tokens",
        type=int,
        default=1800,
        help="Maximum model output tokens per neural wake cycle",
    )
    parser.add_argument("--ledger", type=str, default=None, help="Optional JSONL output path")
    parser.add_argument("--archive-jsonl", type=str, default=None, help="Optional Archive JSONL output path")
    parser.add_argument("--projects-jsonl", type=str, default=None, help="Optional PersistentProject JSONL output path")
    parser.add_argument("--causal-trace-jsonl", type=str, default=None, help="Optional project causal trace JSONL output path")
    parser.add_argument("--causal-graph-json", type=str, default=None, help="Optional project causal edge graph JSON output path")
    parser.add_argument("--hydrology-trace-jsonl", type=str, default=None, help="Optional hydrology process trace JSONL output path")
    parser.add_argument("--hydrology-state-json", type=str, default=None, help="Optional final hydrology state JSON output path")
    parser.add_argument("--local-percepts-jsonl", type=str, default=None, help="Optional private local percept JSONL output path")
    parser.add_argument("--observation-provenance-jsonl", type=str, default=None, help="Optional Creator-facing observation provenance JSONL output path")
    parser.add_argument("--physical-actions-jsonl", type=str, default=None, help="Optional world-facing physical action trace JSONL output path")
    parser.add_argument("--affordance-forensic-graph", type=str, default=None, help="Optional local perception/action/physics forensic graph JSON output path")
    parser.add_argument("--local-subjects-json", type=str, default=None, help="Optional local subject body/capability state JSON output path")
    parser.add_argument("--aqueous-echo-trace-jsonl", type=str, default=None, help="Optional hidden-metaphysics echo process trace JSONL output path")
    parser.add_argument("--aqueous-echo-state-json", type=str, default=None, help="Optional final aqueous echo field JSON output path")
    parser.add_argument("--aqueous-echo-sense-trace-jsonl", type=str, default=None, help="Optional local aqueous echo sensing trace JSONL output path")
    parser.add_argument("--aqueous-echo-forensic-graph", type=str, default=None, help="Optional material/contact/water/echo/perception graph JSON output path")
    parser.add_argument("--tail", type=int, default=12, help="Number of recent events to print")
    args = parser.parse_args()
    if args.start_day < 1:
        parser.error("--start-day must be >= 1")
    if args.neural_max_output_tokens < 256:
        parser.error("--neural-max-output-tokens must be >= 256")
    if not 0.0 <= args.local_temperature <= 2.0:
        parser.error("--local-temperature must be in [0, 2]")
    if args.local_context <= 0:
        parser.error("--local-context must be positive")
    if args.local_timeout <= 0.0:
        parser.error("--local-timeout must be positive")
    return args


def print_summary(engine: WorldEngine, simulation: Simulation, tail: int) -> None:
    world = engine.world
    print("\nWORLD ZERO V0.0-D.2.3 — AQUEOUS SILVER ECHO")
    print(f"Seed: {world.seed}")
    print(f"Time: {world.formatted_time} ({world.game_minute} game minutes)")
    print(f"Actors: {len(world.actors)}")
    print(f"Ledger events: {len(engine.ledger.events)}")

    counts = Counter(event.event_type for event in engine.ledger.events)
    print("\nEVENT COUNTS")
    for event_type, count in sorted(counts.items()):
        print(f"  {event_type:<22} {count:>5}")

    print("\nREGIONS")
    for region_id in sorted(world.regions):
        region = world.regions[region_id]
        access = "open" if region.accessible else "sealed"
        metrics = ", ".join(f"{k}={v:.3f}" for k, v in sorted(region.metrics.items()))
        print(f"  {region.name:<12} [{access}] {metrics}")

    print("\nARRA")
    arra = world.actors["arra"]
    print(f"  location={arra.location_id} gold={arra.gold} inventory={arra.inventory} traits={arra.traits}")

    print(f"\nLAST {min(tail, len(engine.ledger.events))} EVENTS")
    for event in engine.ledger.events[-tail:]:
        actors = ",".join(event.actor_ids)
        print(
            f"  #{event.event_id:04d} t={event.game_minute:05d} "
            f"{event.event_type:<22} actor={actors:<10} region={event.location_id}"
        )


def print_herald_summary(heralds: HeraldSystem, tail: int) -> None:
    print("\nARCHIVE, HERALDS & DIVINE PRESENCE")
    print(f"Archive entries: {len(heralds.archive.entries)}")
    decision_counts = Counter(decision.priority.value for decision in heralds.decisions)
    print(
        "Routing decisions: "
        + ", ".join(f"{key}={decision_counts.get(key, 0)}" for key in ("immediate", "digest", "archive_only"))
    )

    for deity in ("nature", "death", "trade"):
        inbox = heralds.inbox(deity)
        print(f"  {deity:<7} immediate={len(inbox.immediate):>3} digest={len(inbox.digest):>3}")

    reports = sorted(
        (report for inbox in heralds.inboxes.values() for report in inbox.all_reports),
        key=lambda report: report.report_id,
    )
    print(f"\nLAST {min(tail, len(reports))} DIVINE REPORTS")
    for report in reports[-tail:]:
        actor = ",".join(report.known_actor_ids) if report.known_actor_ids else "UNKNOWN"
        print(
            f"  R#{report.report_id:04d} {report.entity_id:<11} {report.priority.value:<9} "
            f"score={report.attention_score:.3f} actor={actor:<10} {report.summary}"
        )


def print_divine_summary(runtime: DivineRuntime, tail: int) -> None:
    agent = runtime.agent("death")
    account = runtime.gateway.power(agent.entity_id)
    focus = agent.heralds.presence.focus_allocations(agent.entity_id)
    threads = agent.heralds.attention.allocations(agent.entity_id)
    budget = agent.heralds.presence.profiles[agent.entity_id].consciousness_budget
    consciousness = sum(focus.values()) + sum(threads.values())
    beliefs = runtime.beliefs.beliefs(agent.entity_id)
    mysteries = runtime.mysteries.hypotheses(agent.entity_id)
    impressions = runtime.impressions.impressions(agent.entity_id)
    print("\nDIVINE AGENT — GOD OF DEATH")
    if isinstance(agent.brain, NeuralDeathGodBrain):
        input_tokens = sum(item.input_tokens or 0 for item in agent.brain.invocations)
        output_tokens = sum(item.output_tokens or 0 for item in agent.brain.invocations)
        provider = "local/Ollama" if isinstance(agent.brain.transport, OllamaChatTransport) else "OpenAI"
        print(
            f"Brain: neural/{provider} ({agent.brain.config.model}, reasoning={agent.brain.config.reasoning_effort}) | "
            f"completed={agent.brain.completed_calls} silence={agent.brain.silence_count} | "
            f"tokens in/out={input_tokens}/{output_tokens}"
        )
        if isinstance(agent.brain.transport, OllamaChatTransport):
            print(f"Ollama context: {agent.brain.transport.context_tokens} tokens")
            load_seconds = sum(item.load_seconds or 0.0 for item in agent.brain.invocations)
            prompt_seconds = sum(item.prompt_eval_seconds or 0.0 for item in agent.brain.invocations)
            generation_seconds = sum(item.generation_seconds or 0.0 for item in agent.brain.invocations)
            if any(item.load_seconds is not None for item in agent.brain.invocations):
                print(
                    f"Ollama phases: load={load_seconds:.2f}s prompt={prompt_seconds:.2f}s "
                    f"generation={generation_seconds:.2f}s"
                )
        failed = [item for item in agent.brain.invocations if item.error_message]
        if failed:
            print(f"Last Divine Silence: {failed[-1].error_message}")
    else:
        print("Brain: deterministic reference rules")
    print(
        f"Wake cycles: {agent.state.wake_count} | Divine Power: {account.current:.2f}/{account.maximum:.2f} "
        f"| consciousness={consciousness:.2f}/{budget:.2f}"
    )
    print(f"Spatial focus: {focus or '{}'} | Personal threads: {threads or '{}'}")
    print(f"Fallible beliefs: {len(beliefs)}")
    for belief in beliefs[-3:]:
        print(
            f"  B#{belief.belief_id:03d} {belief.belief_type.value} subject={belief.subject_actor_id} "
            f"confidence={belief.confidence:.3f} status={belief.status.value} object={belief.object_ref}"
        )
    print(f"Veiled hypotheses: {len(mysteries)}")
    for hypothesis in mysteries[-3:]:
        print(
            f"  V#{hypothesis.hypothesis_id:03d} subject={hypothesis.subject_ref} "
            f"confidence={hypothesis.confidence:.3f} status={hypothesis.status.value}"
        )
    print(f"Private impressions: {len(impressions)}")
    for impression in impressions[-3:]:
        print(
            f"  I#{impression.impression_id:03d} significance={impression.significance:.2f} "
            f"evidence={impression.source_knowledge_ids} {impression.summary}"
        )
    print(f"Goal: {agent.state.last_goal}")
    if agent.state.investigation_location:
        print(f"Investigation: {agent.state.investigation_location}")
    recent = agent.thoughts[-max(1, tail):]
    print(f"LAST {len(recent)} DIVINE DECISIONS")
    for thought in recent:
        actions = ", ".join(intent.action_type.value for intent in thought.intents) or "none"
        print(
            f"  T#{thought.thought_id:03d} t={thought.game_minute:05d} wake={thought.wake_reason:<24} "
            f"mind={thought.cognitive_posture.value:<11} world(derived)={thought.world_posture.value:<12} "
            f"significance={thought.significance:.2f} actions={actions}"
        )


def print_project_summary(projects: PersistentProjectStore, trace: CausalTrace) -> None:
    print("\nPERSISTENT PROJECTS")
    for project in projects.projects:
        print(
            f"  {project.project_id:<31} owner={project.owner_id:<16} "
            f"status={project.status.value:<9} revision={project.revision:<3} "
            f"attempts={len(project.attempt_history)}"
        )
        print(f"    desire: {project.desire}")
        print(f"    strategy: {project.current_strategy}")
    print(
        f"Causal trace: decisions={len(trace.decisions)} intents={len(trace.intents)} "
        f"resolutions={len(trace.resolutions)} edges={len(trace.edges())}"
    )


def print_hydrology_summary(hydrology: HydrologyProcess) -> None:
    state = hydrology.state
    print("\nSILVER THREAD HYDROLOGY")
    print(
        f"  ticks={len(hydrology.traces)} gate={state.gate.sluice_position:.2f} "
        f"effective={state.gate.effective_opening:.3f} debris={state.gate.debris_load:.2f} "
        f"integrity={state.gate.structure_integrity:.2f}"
    )
    print(
        f"  aquatic_route={'viable' if state.aquatic_route_viable else 'blocked'} "
        f"gallery={state.gallery.route_state.value} "
        f"burial_exposure={state.burial_bank.exposure_fraction:.3f}"
    )
    levels = " ".join(
        f"{node_id}={state.nodes[node_id].level:.3f}"
        for node_id in ("lake_mirror", "lake_whisper", "underpeak_gallery_sump", "underpeak_deep_river")
    )
    print(f"  levels: {levels}")


def print_affordance_summary(bridge: PhysicalAffordanceBridge) -> None:
    print("\nPHYSICAL AFFORDANCES & LOCAL PERCEPTION")
    print(
        f"  local_subjects={len(bridge.subjects)} "
        f"private_percepts={len(bridge.perceptions.all_percepts)} "
        f"action_traces={len(bridge.action_traces)}"
    )
    for subject in bridge.subjects:
        sites = ",".join(subject.present_site_ids)
        print(
            f"  {subject.subject_id:<16} kind={subject.subject_kind:<24} "
            f"sites={sites}"
        )


def print_aqueous_echo_summary(
    echo: AqueousSilverEchoProcess,
    sensing: AqueousEchoSenseBridge,
) -> None:
    print("\nAQUEOUS SILVER ECHO")
    print(
        f"  echo_ticks={len(echo.traces)} "
        f"local_sense_traces={len(sensing.traces)} "
        f"active_contact_events={len(echo.active_contact_event_ids)}"
    )
    bands = " ".join(
        f"{node_id}={echo.state.band_states[node_id]}"
        for node_id in (
            "lake_mirror",
            "lake_whisper",
            "northwood_junction",
            "underpeak_deep_river",
        )
    )
    print(f"  bands: {bands}")


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="backslashreplace")
    args = parse_args()
    world = create_world(seed=args.seed, synthetic_actors=args.actors)
    world.game_minute = (args.start_day - 1) * 24 * 60
    ledger = EventLedger()
    archive = Archive()
    heralds = HeraldSystem(world, archive)
    heralds.attach(ledger)
    engine = WorldEngine(world, ledger=ledger, seed=args.seed + 1)
    hydrology = create_silver_thread_hydrology(world, ledger)
    affordance_bridge = create_silver_thread_affordance_bridge(world, ledger, hydrology)
    aqueous_echo = create_silver_thread_aqueous_echo(world, ledger, hydrology)
    aqueous_echo_sensing = create_silver_thread_echo_sense_bridge(
        world,
        ledger,
        aqueous_echo,
        affordance_bridge,
    )
    world_process_runtime = WorldProcessRuntime(start_minute=world.game_minute)
    world_process_runtime.register(hydrology)
    world_process_runtime.register(aqueous_echo)
    world_process_runtime.attach(world)
    simulation = Simulation(engine, minutes_per_step=args.minutes_per_step, seed=args.seed + 2)
    projects = seed_silver_thread_projects(world.game_minute)
    project_trace = CausalTrace(ledger)
    project_runtime = ProjectRuntime(projects, project_trace)
    simulation.subscribe_tick(lambda: project_runtime.tick(world.game_minute))
    divine_runtime = None
    if not args.no_divine_agent:
        death_brain = None
        if args.brain in {"neural", "openai"}:
            try:
                death_brain = create_openai_death_god_brain(
                    model=args.model or DEFAULT_OPENAI_MODEL,
                    reasoning_effort=args.reasoning_effort,
                    max_output_tokens=args.neural_max_output_tokens,
                )
            except NeuralConfigurationError as exc:
                raise SystemExit(f"Neural brain configuration error: {exc}") from exc
        elif args.brain == "local":
            try:
                death_brain = create_local_death_god_brain(
                    model=args.model or DEFAULT_LOCAL_MODEL,
                    max_output_tokens=args.neural_max_output_tokens,
                    endpoint=args.local_endpoint,
                    timeout_seconds=args.local_timeout,
                    temperature=args.local_temperature,
                    context_tokens=args.local_context,
                )
            except NeuralConfigurationError as exc:
                raise SystemExit(f"Local brain configuration error: {exc}") from exc
        divine_runtime = create_prototype_divine_runtime(
            world,
            ledger,
            heralds,
            death_brain=death_brain,
        )
    if divine_runtime is not None:
        simulation.subscribe_tick(divine_runtime.tick)

    if args.belief_demo:
        if divine_runtime is None:
            raise SystemExit("--belief-demo requires the divine agent; remove --no-divine-agent")
        if "sim_002" not in world.actors:
            raise SystemExit("--belief-demo requires at least two synthetic actors; use --actors 2 or more")
        setup = engine.apply(
            Action(
                "sim_002",
                ActionType.DESTROY_TEMPLE,
                target_id="temple_last_gate",
                params={"secret": True},
            )
        )
        if not setup.ok:
            raise SystemExit(f"belief demo setup failed: {setup.message}")
        divine_runtime.tick()
        print("BELIEF DEMO SETUP")
        print("  Objective debug truth: sim_002 secretly destroyed Temple of the Last Gate.")
        print("  Subjective divine truth: the God of Death perceived the destruction, but not the culprit.")

    if args.demo:
        print("ARRA DEMO")
        for line in run_arra_demo(engine, after_advance=divine_runtime.tick if divine_runtime else None):
            print(f"  {line}")

    simulation.run(args.steps)
    if args.interactive:
        interactive_loop(simulation, heralds, divine_runtime)
    print_summary(engine, simulation, args.tail)
    print_herald_summary(heralds, args.tail)
    print_project_summary(projects, project_trace)
    print_hydrology_summary(hydrology)
    print_affordance_summary(affordance_bridge)
    print_aqueous_echo_summary(aqueous_echo, aqueous_echo_sensing)
    if divine_runtime is not None:
        print_divine_summary(divine_runtime, args.tail)

    if ledger.listener_errors:
        print("\nHERALD ERRORS")
        for error in ledger.listener_errors:
            print(f"  {error}")
    if simulation.tick_errors:
        print("\nSIMULATION LISTENER ERRORS")
        for error in simulation.tick_errors:
            print(f"  {error}")
    if project_runtime.errors:
        print("\nPROJECT RUNTIME ERRORS")
        for error in project_runtime.errors:
            print(f"  {error}")

    if args.ledger:
        engine.ledger.export_jsonl(args.ledger)
        print(f"\nLedger written to: {args.ledger}")
    if args.archive_jsonl:
        heralds.archive.export_jsonl(args.archive_jsonl)
        print(f"Archive written to: {args.archive_jsonl}")
    if args.projects_jsonl:
        projects.export_jsonl(args.projects_jsonl)
        print(f"Projects written to: {args.projects_jsonl}")
    if args.causal_trace_jsonl:
        project_trace.export_jsonl(args.causal_trace_jsonl)
        print(f"Project causal trace written to: {args.causal_trace_jsonl}")
    if args.causal_graph_json:
        project_trace.export_graph_json(args.causal_graph_json)
        print(f"Project causal graph written to: {args.causal_graph_json}")
    if args.hydrology_trace_jsonl:
        hydrology.export_trace_jsonl(args.hydrology_trace_jsonl)
        print(f"Hydrology trace written to: {args.hydrology_trace_jsonl}")
    if args.hydrology_state_json:
        hydrology.export_state_json(args.hydrology_state_json)
        print(f"Hydrology state written to: {args.hydrology_state_json}")
    if args.local_percepts_jsonl:
        affordance_bridge.perceptions.export_percepts_jsonl(args.local_percepts_jsonl)
        print(f"Local percepts written to: {args.local_percepts_jsonl}")
    if args.observation_provenance_jsonl:
        affordance_bridge.perceptions.export_provenance_jsonl(args.observation_provenance_jsonl)
        print(f"Observation provenance written to: {args.observation_provenance_jsonl}")
    if args.physical_actions_jsonl:
        affordance_bridge.export_action_trace_jsonl(args.physical_actions_jsonl)
        print(f"Physical action trace written to: {args.physical_actions_jsonl}")
    if args.affordance_forensic_graph:
        affordance_bridge.export_forensic_graph_json(args.affordance_forensic_graph)
        print(f"Affordance forensic graph written to: {args.affordance_forensic_graph}")
    if args.local_subjects_json:
        affordance_bridge.export_subjects_json(args.local_subjects_json)
        print(f"Local subjects written to: {args.local_subjects_json}")
    if args.aqueous_echo_trace_jsonl:
        aqueous_echo.export_trace_jsonl(args.aqueous_echo_trace_jsonl)
        print(f"Aqueous echo trace written to: {args.aqueous_echo_trace_jsonl}")
    if args.aqueous_echo_state_json:
        aqueous_echo.export_state_json(args.aqueous_echo_state_json)
        print(f"Aqueous echo state written to: {args.aqueous_echo_state_json}")
    if args.aqueous_echo_sense_trace_jsonl:
        aqueous_echo_sensing.export_trace_jsonl(args.aqueous_echo_sense_trace_jsonl)
        print(f"Aqueous echo sense trace written to: {args.aqueous_echo_sense_trace_jsonl}")
    if args.aqueous_echo_forensic_graph:
        aqueous_echo_sensing.export_forensic_graph_json(args.aqueous_echo_forensic_graph)
        print(f"Aqueous echo forensic graph written to: {args.aqueous_echo_forensic_graph}")


if __name__ == "__main__":
    main()
