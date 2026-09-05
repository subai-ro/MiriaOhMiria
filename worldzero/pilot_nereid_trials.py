"""Explicit OFFLINE LAB only. Never import these policies in a playable entry point.

Controlled decisions test interfaces and counterfactual physics, not canonical
Nereid cognition. No policy below reads objective world state.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
import json
from pathlib import Path

from .affordances import GATE_TARGET, PhysicalActionRequest, PhysicalActionType
from .neural import NeuralModelResponse
from .pilot_nereid import NEREID, NEREID_PROJECT, create_pilot_nereid_loop
from .pilot_nereid_creator import causal_path, creator_graph, render_creator_report
from .pilot_playable import create_pilot_i1_loop, render_player_journal


def lab_reply(*, action=None, evidence=(), strategy="Lab-only deferral", hypotheses=None):
    return {"strategy": strategy, "evidence_refs": list(evidence), "review_after_minutes": 720,
            "hypotheses": hypotheses, "action": action}


def lab_action(verb, refs=(), target=GATE_TARGET):
    return {"verb": verb, "target": target, "effort": 1.0 if verb == "shift_local_silt" else 0,
            "evidence_refs": list(refs)}


class LabNereidTransport:
    """Bounded-payload test double, NOT a model, character brain or demo fallback."""
    def __init__(self, branch="attempt"):
        if branch not in ("attempt", "silent", "unknown"):
            raise ValueError("unknown lab branch")
        self.branch = branch
        self.requests = []

    def complete(self, request):
        data = request.input_payload
        self.requests.append(json.loads(json.dumps(data)))
        seen = [p for p in data["percepts"] if p["target_ref"] == GATE_TARGET]
        issued = data["own_intents"]
        if self.branch == "unknown":
            output = lab_reply(strategy="Lab: I lack evidence and defer")
        elif not seen:
            output = lab_reply(action=lab_action("inspect_gate"), strategy="Lab: inspect remembered local obstacle")
        elif self.branch == "silent":
            output = lab_reply(evidence=[seen[-1]["ref"]], strategy="Lab: defer despite local evidence")
        elif not any(i["verb"] == "shift_local_silt" for i in issued):
            output = lab_reply(action=lab_action("shift_local_silt", [seen[-1]["ref"]]),
                               strategy="Lab: try a small local clearing, without assuming success")
        elif len([i for i in issued if i["verb"] == "inspect_gate"]) < 2:
            output = lab_reply(action=lab_action("inspect_gate"), strategy="Lab: inspect again; attempted work is not knowledge")
        else:
            output = lab_reply(evidence=[seen[-1]["ref"]], strategy="Lab: reconsider from my latest inspection",
                               hypotheses=[{"claim": "A small clearing may still be insufficient to return home",
                                            "evidence_refs": [seen[-1]["ref"]]}])
        return NeuralModelResponse(output)


class LabReplayTransport:
    """Replays recorded outputs and verifies the exact delivered private input."""
    def __init__(self, invocations):
        self.invocations = tuple(invocations)
        self.index = 0

    def complete(self, request):
        invocation = self.invocations[self.index]
        self.index += 1
        if request.input_payload != json.loads(invocation.request_json):
            raise AssertionError("replay private input diverged")
        if invocation.request_envelope_json is not None and asdict(request) != json.loads(invocation.request_envelope_json):
            raise AssertionError("replay model/prompt/schema configuration diverged")
        if invocation.error:
            raise ValueError("cannot replay failed invocation as a successful decision")
        return NeuralModelResponse(json.loads(invocation.response_json))


@dataclass(frozen=True)
class LabBranch:
    name: str
    description: str
    loop: object
    before: object
    after: object
    transcript: str


@dataclass(frozen=True)
class LabCheck:
    name: str
    ok: bool
    detail: str


DESCRIPTIONS = {
    "attempt": "Общее T0: осмотр, одна ограниченная попытка, повторный осмотр. Лабораторные решения.",
    "silent": "То же T0, но после осмотра субъект откладывает работу. Лабораторные решения.",
    "blocked": "Явный контрфактический T0: нет ресурса усилия; тот же план не гарантирует результат.",
    "absent": "Удалена только когниция Нереиды; Бог Смерти и физические процессы остаются.",
    "unknown": "Субъект не осматривает затвор и откладывает решение при недостатке сведений.",
}


def run_branch(name="attempt", *, seed=42, transport=None) -> LabBranch:
    if name not in DESCRIPTIONS:
        raise ValueError("unknown lab history")
    if name == "absent":
        loop = create_pilot_i1_loop(seed=seed, prehistory_minutes=0, serial_actions=True)
    else:
        loop = create_pilot_nereid_loop(seed=seed, prehistory_minutes=0,
            transport=transport if transport is not None else LabNereidTransport("attempt" if name == "blocked" else name))
    if name == "blocked":
        next(b for b in loop.session.affordances.subjects if b.subject_id == NEREID).resources["effort"] = 0
    loop.session.advance(720)
    loop.started_minute = loop.session.world.game_minute
    for command in ("go gate", "inspect"):
        result = loop.execute(command)
        if not result.ok:
            raise AssertionError(result.message)
    before = loop.player_view()
    # Fixed comparison time selected by the acceptance contract, not from a
    # desired outcome. Work at 1080–1260 settles well beyond six hours.
    while loop.session.world.game_minute < 2160:
        result = loop.wait(min(360, 2160-loop.session.world.game_minute))
        if not result.ok:
            raise AssertionError(result.message)
    result = loop.inspect()
    if not result.ok:
        raise AssertionError(result.message)
    after = loop.player_view()
    transcript = (f"BEFORE — {before.time}\n{render_player_journal(before)}\n\n"
                  f"AFTER — {after.time}\n{render_player_journal(after)}")
    return LabBranch(name, DESCRIPTIONS[name], loop, before, after, transcript)


def history_signature(loop) -> dict:
    s = loop.session
    return {"minute": s.world.game_minute, "events": [e.as_dict() for e in s.ledger.events],
            "bodies": [b.as_dict() for b in s.affordances.subjects],
            "process_runs": [asdict(r) for r in s.world_process_runtime.runs],
            "projects": [p.as_dict() for p in s.projects.projects],
            "hydrology": s.hydrology.state.state_hash(), "echo": s.aqueous_echo.state.state_hash(),
            "percepts": [p.as_dict() for p in s.affordances.perceptions.all_percepts],
            "actions": [a.as_dict() for a in s.affordances.action_traces],
            "decisions": [d.as_dict() for d in s.project_trace.decisions],
            "resolutions": [r.as_dict() for r in s.project_trace.resolutions],
            "view": asdict(loop.player_view()), "graph": creator_graph(s)}


def run_nereid_trials(seed=42):
    branches = tuple(run_branch(name, seed=seed) for name in DESCRIPTIONS)
    attempt, silent, blocked, absent, unknown = branches
    s = attempt.loop.session
    work = [a for a in s.affordances.action_traces if a.subject_id == NEREID and a.action_type.value == "shift_local_silt"]
    graph = creator_graph(s)
    last_percept = s.affordances.perceptions.for_subject("arra")[-1]
    replay = run_branch(transport=LabReplayTransport(attempt.loop.nereid_mind.invocations), seed=seed)
    checks = [
        LabCheck("same T0 opening", attempt.before == silent.before, "Player opening and initial observation match"),
        LabCheck("equal final minute", all(b.loop.session.world.game_minute == 2205 for b in branches), "2205 in all five histories"),
        LabCheck("lawful visible difference", attempt.after.observations[-1] != silent.after.observations[-1], "light vs moderate debris, owned Arra inspections"),
        LabCheck("bounded settled work", len(work) == 1 and work[0].end_minute == 1260 and 2205-work[0].end_minute >= 360, "1080–1260 work; 945 minutes before final observation"),
        LabCheck("no automatic observation", not any(p.game_minute == 1260 for p in s.affordances.perceptions.all_percepts), "work produces no percept"),
        LabCheck("unfinished independent Project", all(b.loop.session.projects.get(NEREID_PROJECT).status.value == "active" for b in branches), "no success by text or mandatory helper"),
        LabCheck("blocked effort preserves world", blocked.after.observations[-1] == silent.after.observations[-1], "same local observation despite an attempted intent"),
        LabCheck("absent/unknown control", absent.after.observations[-1] == unknown.after.observations[-1] == silent.after.observations[-1], "no work is a valid history"),
        LabCheck("Creator action-to-observation", bool(work and causal_path(graph, work[0].ref, last_percept.ref)), "existing physical/result/process/provenance records"),
        LabCheck("recorded replay", history_signature(attempt.loop) == history_signature(replay.loop), "exact private inputs, decisions, world, graph and Player View"),
        LabCheck("healthy runtimes", all(not b.loop.session.clock.errors
            and not b.loop.session.project_runtime.errors and not b.loop.session.ledger.listener_errors
            for b in branches), "no swallowed runtime/listener error in valid histories"),
    ]
    # A separate diagnostic continuation demonstrates a real changed affordance
    # using exactly the same existing Trade House request in both histories.
    # Never folded back into the above player histories or called Trade cognition.
    moved = []
    for name in ("attempt", "silent"):
        probe = run_branch(name, seed=seed).loop.session
        result = probe.perform(PhysicalActionRequest("trade_house_01", PhysicalActionType.ADJUST_SLUICE,
            GATE_TARGET, params={"effort": 1.0, "delta": 1.0}))
        if not result.ok:
            raise AssertionError(result.message)
        moved.append(probe.affordances.action_traces[-1].effect["applied_delta"])
    checks.append(LabCheck("real affordance counterfactual", moved[0] > moved[1],
                           f"same Trade diagnostic request: movement {moved[0]} vs {moved[1]}"))
    return branches, tuple(checks)


def export_lab_report(destination, branches, checks):
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    paths = [destination / "creator_report.html", destination / "checks.json"]
    for branch in branches:
        paths.extend(destination / f"{branch.name}_{suffix}" for suffix in ("player.txt", "graph.json", "model_calls.json"))
    if any(path.exists() for path in paths):
        raise FileExistsError("refusing to overwrite earlier local acceptance evidence; choose a new output directory")
    paths[0].write_text(render_creator_report(branches, checks), encoding="utf-8")
    paths[1].write_text(json.dumps([asdict(c) for c in checks], ensure_ascii=False, indent=2), encoding="utf-8")
    for branch in branches:
        (destination / f"{branch.name}_player.txt").write_text(branch.transcript, encoding="utf-8")
        (destination / f"{branch.name}_graph.json").write_text(json.dumps(creator_graph(branch.loop.session), indent=2), encoding="utf-8")
        calls = getattr(branch.loop, "nereid_mind", None)
        (destination / f"{branch.name}_model_calls.json").write_text(
            json.dumps([asdict(c) for c in calls.invocations] if calls else [], ensure_ascii=False, indent=2), encoding="utf-8")
    return paths[0]
