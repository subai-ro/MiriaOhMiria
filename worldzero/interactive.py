from __future__ import annotations

import shlex

from .attention import AttentionDirective
from .divine import DivineRuntime
from .heralds import HeraldSystem
from .models import Action, ActionType
from .simulation import Simulation


HELP = """Commands:
  status                         show Arra and current region
  go REGION                      travel: northwood / ash_valley / red_march / underpeak
  visit SITE [secret]            visit a local site; optionally hide the visit
  fish [LAKE]                    fish with the silver rod
  wood                           harvest timber in Northwood
  sell ITEM [QTY]                sell timber / river_fish / silver_carp
  pray GOD                       nature / death / trade
  study                          study necromancy in Ash Valley
  raise                          attempt to raise a corpse
  say TEXT                       make a public diegetic statement
  whisper TEXT                   make a private diegetic statement
  answer PROBE_REF TEXT          explicitly answer a divine probe
  destroy TEMPLE [secret]        destroy a local temple
  wait [STEPS]                   let the world advance; 1 step = 10 game minutes
  history [N]                    show recent objective ledger events (debug view)
  archive [N]                    show recent semantic Archive entries (debug view)
  inbox GOD [N]                  inspect nature / death / trade Divine Inbox
  knowledge GOD [N]              inspect a God's subjective long-term knowledge
  beliefs GOD [N]                inspect a God's fallible hypotheses and evidence
  mysteries GOD [N]              inspect hypotheses about unidentified agency
  impressions GOD [N]            inspect a God's private memory marks
  resonances GOD [N]             inspect contextual motifs supplied at the last wake
  awareness GOD [N]              inspect recent perception/attention decisions
  presence GOD [LOCATION]        inspect current local concentration of consciousness
  threads GOD                    inspect personal divine attention threads
  focus GOD LOCATION INTENSITY   allocate spatial consciousness (debug control)
  focus GOD clear                clear a God's conscious focus
  god death [N]                  inspect the first God's mind and recent decisions
  omens [N]                      inspect manifestations received by Arra
  think death                    force one God wake cycle (debug control)
  calendar                       show active temporal observances
  help                           show commands
  quit                           leave World Zero
"""


DEITY_ALIASES = {
    "nature": "god_nature",
    "death": "god_death",
    "trade": "god_trade",
}


def _status(simulation: Simulation) -> None:
    world = simulation.world
    actor = world.actors["arra"]
    region = world.regions[actor.location_id]
    local_objects = sorted(
        (obj for obj in world.objects.values() if obj.location_id == actor.location_id),
        key=lambda obj: obj.id,
    )
    print(f"\n{world.formatted_time} — {region.name}")
    print(f"gold={actor.gold} inventory={actor.inventory or '{}'}")
    print(f"traits={actor.traits or '{}'}")
    print(f"neighbors={', '.join(region.neighbors)}")
    if local_objects:
        print("objects=" + ", ".join(f"{obj.id} ({obj.condition})" for obj in local_objects))


def _history(simulation: Simulation, count: int) -> None:
    events = simulation.engine.ledger.events[-max(1, count):]
    for event in events:
        actors = ",".join(event.actor_ids)
        print(
            f"#{event.event_id:04d} t={event.game_minute:05d} {event.event_type:<21} "
            f"actor={actors:<10} region={event.location_id:<11} publicity={event.publicity:.2f} secrecy={event.secrecy:.2f}"
        )


def _archive(heralds: HeraldSystem, count: int) -> None:
    print("\nDEBUG — ARCHIVE")
    for entry in heralds.archive.entries[-max(1, count):]:
        print(
            f"A#{entry.archive_id:04d} t={entry.game_minute:05d} {entry.kind:<7} "
            f"{entry.event_type:<25} {entry.summary}"
        )


def _inbox(heralds: HeraldSystem, deity: str, count: int) -> None:
    try:
        inbox = heralds.inbox(deity)
    except KeyError:
        print("Unknown divine inbox. Use nature, death, or trade.")
        return
    print(f"\nDEBUG — DIVINE INBOX: {deity}")
    reports = inbox.all_reports[-max(1, count):]
    if not reports:
        print("(empty)")
        return
    for report in reports:
        actors = ",".join(report.known_actor_ids) if report.known_actor_ids else "UNKNOWN"
        print(
            f"R#{report.report_id:04d} {report.priority.value:<9} score={report.attention_score:.3f} "
            f"known_actor={actors:<10} {report.summary}"
        )


def _knowledge(heralds: HeraldSystem, deity: str, count: int) -> None:
    try:
        items = heralds.knowledge(deity, limit=max(1, count))
    except KeyError:
        print("Unknown divine knowledge view. Use nature, death, or trade.")
        return
    print(f"\nDEBUG — SUBJECTIVE KNOWLEDGE: {deity}")
    if not items:
        print("(empty)")
        return
    for item in reversed(items):
        actors = ",".join(item.known_actor_ids) if item.known_actor_ids else "UNKNOWN"
        veils = ",".join(item.veiled_subject_refs) if item.veiled_subject_refs else "none"
        print(
            f"K#{item.knowledge_id:04d} confidence={item.confidence:.2f} known_actor={actors:<10} "
            f"veiled={veils} probe_response={item.response_to_probe_ref or 'none'} {item.summary}"
        )


def _beliefs(runtime: DivineRuntime, deity: str, count: int) -> None:
    try:
        items = runtime.beliefs.beliefs(deity)[-max(1, count):]
    except KeyError:
        print("Unknown deity. Use nature, death, or trade.")
        return
    print(f"\nDEBUG — FALLIBLE DIVINE BELIEFS: {deity}")
    if not items:
        print("(no inferred beliefs; observations may still exist in knowledge)")
        return
    world = runtime.gateway.world
    for item in items:
        actor = world.actors.get(item.subject_actor_id)
        actor_name = actor.name if actor else item.subject_actor_id
        print(
            f"B#{item.belief_id:03d} {item.belief_type.value:<15} "
            f"subject={actor_name} ({item.subject_actor_id}) object={item.object_ref} "
            f"confidence={item.confidence:.3f} status={item.status.value}"
        )
        print(f"  proposition: {item.proposition}")
        for evidence in item.evidence:
            sign = "+" if evidence.direction.value == "support" else "-"
            print(
                f"  E#{evidence.evidence_id:03d} {sign} weight={evidence.weight:.2f} "
                f"{evidence.confidence_before:.3f}->{evidence.confidence_after:.3f} "
                f"K={evidence.source_knowledge_ids} world_events={evidence.source_event_ids}"
            )
            print(f"    {evidence.reason}")


def _mysteries(runtime: DivineRuntime, deity: str, count: int) -> None:
    try:
        items = runtime.mysteries.hypotheses(deity)[-max(1, count):]
    except KeyError:
        print("Unknown deity. Use nature, death, or trade.")
        return
    print(f"\nDEBUG — VEILED DIVINE HYPOTHESES: {deity}")
    if not items:
        print("(no hypotheses about unresolved agency)")
        return
    for item in items:
        print(
            f"V#{item.hypothesis_id:03d} subject={item.subject_ref} "
            f"confidence={item.confidence:.3f} status={item.status.value}"
        )
        print(f"  proposition: {item.proposition}")
        for evidence in item.evidence:
            sign = "+" if evidence.direction.value == "support" else "-"
            print(
                f"  E#{evidence.evidence_id:03d} {sign} weight={evidence.weight:.2f} "
                f"{evidence.confidence_before:.3f}->{evidence.confidence_after:.3f} "
                f"K={evidence.source_knowledge_ids} world_events={evidence.source_event_ids}"
            )
            print(f"    {evidence.reason}")


def _impressions(runtime: DivineRuntime, deity: str, count: int) -> None:
    try:
        items = runtime.impressions.impressions(deity, limit=max(1, count))
    except KeyError:
        print("Unknown deity. Use nature, death, or trade.")
        return
    print(f"\nDEBUG — PRIVATE DIVINE IMPRESSIONS: {deity}")
    if not items:
        print("(no private memory marks)")
        return
    for item in items:
        print(
            f"I#{item.impression_id:03d} significance={item.significance:.2f} "
            f"K={item.source_knowledge_ids} world_events={item.source_event_ids}"
        )
        print(f"  {item.summary}")
        print(f"  reason: {item.reason}")


def _resonances(runtime: DivineRuntime, deity: str, count: int) -> None:
    try:
        agent = runtime.agent(deity)
    except KeyError:
        print("No thinking agent is active for that deity.")
        return
    print(f"\nDEBUG — LAST-WAKE CONTEXTUAL RESONANCE: {deity}")
    if not agent.thoughts:
        print("(the God has not woken yet)")
        return
    items = agent.thoughts[-1].contextual_resonances[-max(1, count):]
    if not items:
        print("(no motif conjunctions were supplied at the last wake)")
        return
    for item in items:
        print(
            f"{item.motif_id} location={item.location_id} pairs={item.matched_pairs} "
            f"K={item.evidence_knowledge_ids} known_actors={item.known_actor_ids or 'none'}"
        )
        print(f"  {item.summary}")


def _presence(simulation: Simulation, heralds: HeraldSystem, deity: str, location_id: str | None) -> None:
    entity_id = DEITY_ALIASES.get(deity, deity)
    if entity_id not in heralds.presence.profiles:
        print("Unknown deity. Use nature, death, or trade.")
        return

    world = simulation.world
    requested = location_id or world.actors["arra"].location_id
    target_id: str | None = None
    if requested in world.objects:
        target = world.objects[requested]
        region_id = target.location_id
        target_id = target.id
        label = f"{target.name} ({target.id})"
    elif requested in world.regions:
        region_id = requested
        label = f"{world.regions[requested].name} ({requested})"
    else:
        print("Unknown location. Use a region id or world-object id.")
        return

    snapshot = heralds.presence.snapshot_at(entity_id, region_id=region_id, target_id=target_id)
    profile = heralds.presence.profiles[entity_id]
    allocations = heralds.presence.focus_allocations(entity_id)
    thread_allocations = heralds.attention.allocations(entity_id)
    used_focus = sum(allocations.values())
    used_threads = sum(thread_allocations.values())
    observances = ", ".join(snapshot.active_observances) or "none"
    print(f"\nDEBUG — DIVINE PRESENCE: {deity}")
    print(f"time={world.formatted_time} location={label}")
    print(
        f"base={snapshot.base:.2f} anchor={snapshot.anchor:.2f} focus={snapshot.focus:.2f} "
        f"temporal={snapshot.temporal:.2f} => PRESENCE={snapshot.total:.2f}"
    )
    print(f"active_observances={observances}")
    print(
        f"consciousness={used_focus + used_threads:.2f}/{profile.consciousness_budget:.2f} "
        f"spatial={allocations or '{}'} personal={thread_allocations or '{}'}"
    )


def _awareness(heralds: HeraldSystem, deity: str, count: int) -> None:
    entity_id = DEITY_ALIASES.get(deity, deity)
    if entity_id not in heralds.profiles:
        print("Unknown deity. Use nature, death, or trade.")
        return

    decisions = [decision for decision in heralds.decisions if decision.entity_id == entity_id][-max(1, count):]
    event_types = {
        entry.source_event_ids[0]: entry.event_type
        for entry in heralds.archive.entries
        if entry.kind == "event" and len(entry.source_event_ids) == 1
    }
    print(f"\nDEBUG — DIVINE AWARENESS: {deity}")
    if not decisions:
        print("(nothing perceived strongly enough to enter awareness)")
        return
    for decision in decisions:
        actor = "KNOWN" if decision.actor_identity_known else "UNKNOWN"
        print(
            f"E#{decision.event_id:04d} {event_types.get(decision.event_id, '?'):<21} "
            f"{decision.priority.value:<12} P={decision.presence:.2f} R={decision.relevance:.2f} "
            f"M={decision.magnitude:.2f} C={decision.contextual_salience:.2f} "
            f"T={decision.personal_attention:.2f} "
            f"perceive={decision.perception_score:.2f} attention={decision.attention_score:.3f} "
            f"actor={actor} — {decision.reason}"
        )


def _threads(heralds: HeraldSystem, deity: str) -> None:
    entity_id = DEITY_ALIASES.get(deity, deity)
    if entity_id not in heralds.profiles:
        print("Unknown deity. Use nature, death, or trade.")
        return
    items = heralds.attention.threads(entity_id)
    budget = heralds.presence.profiles[entity_id].consciousness_budget
    spatial = sum(heralds.presence.focus_allocations(entity_id).values())
    personal = sum(item.intensity for item in items)
    print(f"\nDEBUG — PERSONAL ATTENTION: {deity}")
    print(f"consciousness={spatial + personal:.2f}/{budget:.2f} spatial={spatial:.2f} personal={personal:.2f}")
    if not items:
        print("(no mortal is currently held in the active gaze)")
        return
    for item in items:
        actor = heralds.world.actors.get(item.actor_id)
        label = actor.name if actor else item.actor_id
        print(
            f"G#{item.thread_id:03d} actor={label} ({item.actor_id}) intensity={item.intensity:.2f} "
            f"since=t{item.created_minute:05d} causes={item.causal_event_ids or 'memory'}"
        )
        print(f"  reason: {item.reason or 'sustained personal attention'}")


def _calendar(simulation: Simulation, heralds: HeraldSystem) -> None:
    minute = simulation.world.game_minute
    active = [observance for observance in heralds.presence.observances if observance.active(minute)]
    print(f"\nDEBUG — DIVINE CALENDAR: {simulation.world.formatted_time}")
    if not active:
        print("active_observances=none")
        return
    for observance in active:
        print(f"{observance.name} — {observance.entity_id}")


def _set_focus(
    heralds: HeraldSystem,
    runtime: DivineRuntime | None,
    deity: str,
    location: str,
    intensity: str | None,
) -> None:
    entity_id = DEITY_ALIASES.get(deity, deity)
    if entity_id not in heralds.presence.profiles:
        print("Unknown deity. Use nature, death, or trade.")
        return
    if location != "clear" and intensity is None:
        print("Usage: focus GOD LOCATION INTENSITY, or focus GOD clear")
        return

    allocations = heralds.presence.focus_allocations(entity_id)
    try:
        if location == "clear":
            allocations = {}
        else:
            value = float(intensity)
            if value == 0.0:
                allocations.pop(location, None)
            else:
                allocations[location] = value

        if runtime is not None:
            threads = tuple(
                AttentionDirective(
                    actor_id=thread.actor_id,
                    intensity=thread.intensity,
                    reason=thread.reason,
                    causal_event_ids=thread.causal_event_ids,
                )
                for thread in heralds.attention.threads(entity_id)
            )
            result = runtime.gateway.allocate_consciousness(
                entity_id,
                tuple(sorted(allocations.items())),
                threads,
            )
            if not result.ok:
                print(f"Consciousness allocation rejected: {result.message}")
                return
        else:
            heralds.presence.replace_focus(entity_id, allocations)
    except (ValueError, KeyError) as exc:
        print(f"Focus rejected: {exc}")
        return
    allocations = heralds.presence.focus_allocations(entity_id)
    budget = heralds.presence.profiles[entity_id].consciousness_budget
    personal = heralds.attention.allocations(entity_id)
    used = sum(allocations.values()) + sum(personal.values())
    print(
        f"Spatial focus set. Consciousness {used:.2f}/{budget:.2f}: "
        f"spatial={allocations or '{}'} personal={personal or '{}'}"
    )


def _god(runtime: DivineRuntime, deity: str, count: int) -> None:
    try:
        agent = runtime.agent(deity)
    except KeyError:
        print("No thinking agent is active for that deity. V0.0-D.2.0 currently runs only the God of Death.")
        return
    power = runtime.gateway.power(agent.entity_id)
    focus = agent.heralds.presence.focus_allocations(agent.entity_id)
    threads = agent.heralds.attention.allocations(agent.entity_id)
    beliefs = runtime.beliefs.beliefs(agent.entity_id)
    mysteries = runtime.mysteries.hypotheses(agent.entity_id)
    impressions = runtime.impressions.impressions(agent.entity_id)
    budget = agent.heralds.presence.profiles[agent.entity_id].consciousness_budget
    consciousness = sum(focus.values()) + sum(threads.values())
    print(f"\nDEBUG — DIVINE MIND: {deity}")
    brain_config = getattr(agent.brain, "config", None)
    if brain_config is not None:
        transport = getattr(agent.brain, "transport", None)
        provider = type(transport).__name__ if transport is not None else "unknown"
        print(
            f"brain=neural provider={provider} model={brain_config.model} reasoning={brain_config.reasoning_effort} "
            f"calls={len(getattr(agent.brain, 'invocations', ()))}"
        )
        invocations = getattr(agent.brain, "invocations", ())
        if invocations:
            latest = invocations[-1]
            compacted = ",".join(latest.context_omissions) if latest.context_omissions else "none"
            print(
                f"request={latest.request_fingerprint or 'unknown'} "
                f"context_estimate={latest.estimated_input_tokens or 'n/a'}/"
                f"{latest.input_budget_tokens or 'n/a'} compacted={compacted}"
            )
    else:
        print("brain=deterministic-reference")
    print(
        f"wake_cycles={agent.state.wake_count} power={power.current:.2f}/{power.maximum:.2f} "
        f"consciousness={consciousness:.2f}/{budget:.2f} focus={focus or '{}'} threads={threads or '{}'} "
        f"beliefs={len(beliefs)} mysteries={len(mysteries)} impressions={len(impressions)}"
    )
    print(f"goal={agent.state.last_goal}")
    print(f"investigation={agent.state.investigation_location or 'none'}")
    print(f"actor_interest={agent.state.actor_interest or '{}'}")
    thoughts = agent.thoughts[-max(1, count):]
    if not thoughts:
        print("thoughts=(sleeping; no wake cycle yet)")
        return
    for thought in thoughts:
        print(f"T#{thought.thought_id:03d} t={thought.game_minute:05d} wake={thought.wake_reason}")
        print(
            f"  cognitive posture: {thought.cognitive_posture.value}; "
            f"world posture (derived): {thought.world_posture.value}; "
            f"subjective significance: {thought.significance:.2f}"
        )
        if thought.consciousness_plan is not None:
            print(
                f"  consciousness plan: engagement={thought.consciousness_plan.engagement:.2f}; "
                f"personal fraction={thought.consciousness_plan.personal_fraction:.2f}"
            )
        print(f"  goal: {thought.goal}")
        print(f"  note: {thought.decision_note}")
        for probe in thought.probe_memories:
            print(
                f"  probe memory: {probe.probe_ref} target={probe.target_actor_id} "
                f"status={probe.status.value} responses={probe.response_knowledge_ids or 'none'}"
            )
        print(f"  focus: {dict(thought.focus_allocations) or '{}'}")
        print(
            "  threads: "
            + str({item.actor_id: item.intensity for item in thought.attention_threads} or "{}")
        )
        cognition = "OK" if thought.consciousness_result.ok else f"REJECTED ({thought.consciousness_result.message})"
        print(f"  consciousness: {cognition}")
        for index, update in enumerate(thought.belief_updates):
            result = thought.belief_results[index]
            if result.ok and result.applied:
                status = f"{result.confidence_before:.3f}->{result.confidence_after:.3f} {result.status.value}"
            elif result.ok:
                status = f"NO-OP ({result.message})"
            else:
                status = f"REJECTED ({result.message})"
            print(
                f"  belief: {update.direction.value} {update.belief_type.value} "
                f"subject={update.subject_actor_id} weight={update.weight:.2f} -> {status}"
            )
        for index, update in enumerate(thought.veiled_hypothesis_updates):
            result = thought.veiled_hypothesis_results[index]
            if result.ok and result.applied:
                status = f"{result.confidence_before:.3f}->{result.confidence_after:.3f} {result.status.value}"
            elif result.ok:
                status = f"NO-OP ({result.message})"
            else:
                status = f"REJECTED ({result.message})"
            print(
                f"  mystery: {update.direction.value} subject={update.subject_ref} "
                f"weight={update.weight:.2f} -> {status}"
            )
            print(f"    proposition: {update.proposition}")
            print(f"    reason: {update.reason}")
        for index, update in enumerate(thought.impression_updates):
            result = thought.impression_results[index]
            if result.ok and result.applied:
                status = "OK"
            elif result.ok:
                status = f"NO-OP ({result.message})"
            else:
                status = f"REJECTED ({result.message})"
            print(
                f"  impression: significance={update.significance:.2f} "
                f"evidence={update.evidence_knowledge_ids} -> {status}"
            )
            print(f"    {update.summary}")
            print(f"    reason: {update.reason}")
        for index, intent in enumerate(thought.intents):
            result = thought.action_results[index]
            status = "OK" if result.ok else f"REJECTED ({result.message})"
            target = intent.target_actor_id or f"region:{intent.location_id}"
            print(
                f"  action: {intent.action_type.value} target={target} "
                f"significance={intent.significance:.2f} strength={intent.strength:.2f} "
                f"causes={intent.causal_event_ids or 'proactive'} -> {status}"
            )


def _omens(runtime: DivineRuntime, count: int) -> None:
    items = runtime.gateway.manifestations_for("arra")[-max(1, count):]
    print("\nDIVINE MANIFESTATIONS — ARRA")
    if not items:
        print("(none)")
        return
    for item in items:
        print(
            f"M#{item.manifestation_id:03d} t={item.game_minute:05d} {item.source_entity_id} "
            f"{item.kind} significance={item.significance:.2f}: {item.message}"
        )
        if item.probe_ref:
            print(f"  probe_ref={item.probe_ref} — answer with: answer {item.probe_ref} TEXT")


def _new_manifestations(runtime: DivineRuntime | None, after_id: int) -> int:
    if runtime is None:
        return after_id
    items = [
        item
        for item in runtime.gateway.manifestations_for("arra")
        if item.manifestation_id > after_id
    ]
    for item in items:
        print(f"\n*** DIVINE MANIFESTATION — {item.kind.upper()} ***")
        print(item.message)
        if item.probe_ref:
            print(f"Probe ref: {item.probe_ref}")
            print(f"To answer explicitly: answer {item.probe_ref} TEXT")
    return max((item.manifestation_id for item in items), default=after_id)


def interactive_loop(
    simulation: Simulation,
    heralds: HeraldSystem | None = None,
    divine_runtime: DivineRuntime | None = None,
) -> None:
    engine = simulation.engine
    manifestation_cursor = max(
        (item.manifestation_id for item in divine_runtime.gateway.manifestations_for("arra")),
        default=0,
    ) if divine_runtime else 0
    print("\nWORLD ZERO V0.0-D.2.0 — THE UNFINISHED FUTURE")
    print("The God of Death can form fallible beliefs, author probes, and receive only subjectively available responses.")
    print("Type 'help' for commands.")
    _status(simulation)

    while True:
        try:
            raw = input("\nworld> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nLeaving World Zero.")
            return

        if not raw:
            continue
        try:
            parts = shlex.split(raw)
        except ValueError as exc:
            print(f"Input error: {exc}")
            continue

        command = parts[0].lower()
        args = parts[1:]
        action: Action | None = None

        if command in {"quit", "exit"}:
            print("Leaving World Zero.")
            return
        if command == "help":
            print(HELP)
            continue
        if command == "status":
            _status(simulation)
            continue
        if command == "history":
            count = int(args[0]) if args and args[0].isdigit() else 10
            _history(simulation, count)
            continue
        if command == "archive" and heralds is not None:
            count = int(args[0]) if args and args[0].isdigit() else 10
            _archive(heralds, count)
            continue
        if command == "inbox" and heralds is not None and args:
            count = int(args[1]) if len(args) > 1 and args[1].isdigit() else 10
            _inbox(heralds, args[0].lower(), count)
            continue
        if command == "knowledge" and heralds is not None and args:
            count = int(args[1]) if len(args) > 1 and args[1].isdigit() else 10
            _knowledge(heralds, args[0].lower(), count)
            continue
        if command == "beliefs" and divine_runtime is not None and args:
            count = int(args[1]) if len(args) > 1 and args[1].isdigit() else 10
            _beliefs(divine_runtime, args[0].lower(), count)
            continue
        if command == "mysteries" and divine_runtime is not None and args:
            count = int(args[1]) if len(args) > 1 and args[1].isdigit() else 10
            _mysteries(divine_runtime, args[0].lower(), count)
            continue
        if command == "impressions" and divine_runtime is not None and args:
            count = int(args[1]) if len(args) > 1 and args[1].isdigit() else 10
            _impressions(divine_runtime, args[0].lower(), count)
            continue
        if command == "resonances" and divine_runtime is not None and args:
            count = int(args[1]) if len(args) > 1 and args[1].isdigit() else 10
            _resonances(divine_runtime, args[0].lower(), count)
            continue
        if command == "awareness" and heralds is not None and args:
            count = int(args[1]) if len(args) > 1 and args[1].isdigit() else 10
            _awareness(heralds, args[0].lower(), count)
            continue
        if command == "presence" and heralds is not None and args:
            location_id = args[1].lower() if len(args) > 1 else None
            _presence(simulation, heralds, args[0].lower(), location_id)
            continue
        if command == "threads" and heralds is not None and args:
            _threads(heralds, args[0].lower())
            continue
        if command == "focus" and heralds is not None and len(args) >= 2:
            intensity = args[2] if len(args) > 2 else None
            _set_focus(heralds, divine_runtime, args[0].lower(), args[1].lower(), intensity)
            continue
        if command == "calendar" and heralds is not None:
            _calendar(simulation, heralds)
            continue
        if command == "god" and divine_runtime is not None and args:
            count = int(args[1]) if len(args) > 1 and args[1].isdigit() else 5
            _god(divine_runtime, args[0].lower(), count)
            continue
        if command == "omens" and divine_runtime is not None:
            count = int(args[0]) if args and args[0].isdigit() else 10
            _omens(divine_runtime, count)
            continue
        if command == "think" and divine_runtime is not None and args:
            try:
                thought = divine_runtime.agent(args[0].lower()).maybe_think(force=True)
            except KeyError:
                print("No thinking agent is active for that deity.")
                continue
            print(f"Forced wake completed: T#{thought.thought_id if thought else 0:03d}.")
            manifestation_cursor = _new_manifestations(divine_runtime, manifestation_cursor)
            continue
        if command == "wait":
            steps = int(args[0]) if args and args[0].isdigit() else 1
            simulation.run(max(1, min(steps, 500)))
            print(f"Time passes. It is now {simulation.world.formatted_time}.")
            manifestation_cursor = _new_manifestations(divine_runtime, manifestation_cursor)
            continue
        if command == "go" and args:
            action = Action("arra", ActionType.TRAVEL, target_id=args[0].lower())
        elif command == "visit" and args:
            action = Action(
                "arra",
                ActionType.VISIT_SITE,
                target_id=args[0].lower(),
                params={"secret": len(args) > 1 and args[1].lower() == "secret"},
            )
        elif command == "fish":
            lake = args[0].lower() if args else "lake_mirror"
            action = Action("arra", ActionType.FISH, target_id=lake, params={"tool": "silver_rod"})
        elif command == "wood":
            action = Action("arra", ActionType.HARVEST_WOOD)
        elif command == "sell" and args:
            quantity = int(args[1]) if len(args) > 1 and args[1].isdigit() else 1
            action = Action("arra", ActionType.TRADE, params={"item": args[0], "quantity": quantity})
        elif command == "pray" and args:
            action = Action("arra", ActionType.PRAY, params={"deity": args[0]})
        elif command == "study":
            action = Action("arra", ActionType.STUDY_NECROMANCY, target_id="old_ash_graveyard")
        elif command == "raise":
            action = Action("arra", ActionType.RAISE_DEAD, target_id="grave_interactive")
        elif command == "say" and args:
            action = Action("arra", ActionType.SPEAK, params={"text": " ".join(args), "audience": "public"})
        elif command == "whisper" and args:
            action = Action("arra", ActionType.SPEAK, params={"text": " ".join(args), "audience": "private"})
        elif command == "answer" and len(args) >= 2:
            action = Action(
                "arra",
                ActionType.SPEAK,
                params={
                    "text": " ".join(args[1:]),
                    "audience": "private",
                    "response_to_probe_ref": args[0],
                },
            )
        elif command == "destroy" and args:
            action = Action(
                "arra",
                ActionType.DESTROY_TEMPLE,
                target_id=args[0],
                params={"secret": len(args) > 1 and args[1].lower() == "secret"},
            )
        else:
            print("Unknown or incomplete command. Type 'help'.")
            continue

        result = engine.apply(action)
        if not result.ok:
            print(f"REJECTED: {result.message}")
            continue

        print(f"OK: {result.message} (event #{result.event_id})")
        simulation.run(1)
        manifestation_cursor = _new_manifestations(divine_runtime, manifestation_cursor)
