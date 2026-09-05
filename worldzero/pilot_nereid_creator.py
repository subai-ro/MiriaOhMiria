"""Post-session Creator projection. Reads existing records; stores no world history."""
from __future__ import annotations

from html import escape
import json

from .pilot_nereid import NereidEvidenceProjection


def creator_graph(session) -> dict:
    nodes, edges = {}, set()
    for graph in (session.affordances.forensic_graph(), session.aqueous_echo_sensing.forensic_graph()):
        for node in graph["nodes"]:
            nodes.setdefault(node["ref"], {}).update(node)
        edges.update((e["source_ref"], e["target_ref"], e["kind"]) for e in graph["edges"])
    for project in session.projects.projects:
        nodes[project.ref] = {"ref": project.ref, "kind": "project", **project.as_dict()}
        for attempt in project.attempt_history:
            nodes[attempt.ref] = {"kind": "project_attempt", **attempt.as_dict()}
            for ref in attempt.intent_refs:
                edges.add((ref, attempt.ref, "own_issued_intent_memory"))
    for memory in NereidEvidenceProjection(session).snapshot().payload["memories"]:
        nodes[memory["ref"]] = {"kind": "authored_recollection_not_observation", **memory}
    for group in (session.project_trace.decisions, session.project_trace.intents, session.project_trace.resolutions):
        for item in group:
            nodes[item.ref] = {"kind": item.as_dict()["record_type"], **item.as_dict()}
    def normalized(ref):
        return "world_event:" + ref[6:] if ref.startswith("event:") else ref
    for edge in session.project_trace.edges():
        edges.add((normalized(edge.source_ref), normalized(edge.target_ref), edge.kind.value))
    by_event = {a.event_id: a.ref for a in session.affordances.action_traces if a.event_id is not None}
    by_event.update({s.event_id: s.ref for s in session.aqueous_echo_sensing.traces if s.event_id is not None})
    for result in session.project_trace.resolutions:
        for event_id in result.result_event_ids:
            if event_id in by_event:
                edges.add((result.intent_ref, by_event[event_id], "dispatched_as_existing_action"))
    missing = sorted({ref for source, target, _ in edges for ref in (source, target) if ref not in nodes})
    if missing:
        raise ValueError("unresolved Creator references: " + ", ".join(missing))
    return {"nodes": [nodes[key] for key in sorted(nodes)], "edges": [
        {"source_ref": source, "target_ref": target, "kind": kind}
        for source, target, kind in sorted(edges)]}


def causal_path(graph: dict, source: str, target: str) -> tuple[str, ...]:
    adjacency = {}
    for edge in graph["edges"]:
        adjacency.setdefault(edge["source_ref"], []).append(edge["target_ref"])
    queue, seen = [(source,)], {source}
    for path in queue:
        if path[-1] == target:
            return path
        for next_ref in adjacency.get(path[-1], ()):
            if next_ref not in seen:
                seen.add(next_ref)
                queue.append((*path, next_ref))
    return ()


def render_creator_report(branches, checks) -> str:
    """Static, escaped, post-session HTML; never served as Player View."""
    parts = ['<!doctype html><html lang="ru"><meta charset="utf-8">',
             '<title>World Zero — N1–N3 offline proof</title>',
             '<style>body{font:17px/1.6 system-ui;max-width:1040px;margin:40px auto;padding:0 24px;'
             'background:#141b21;color:#e4e8e9}h1,h2{color:#a4d9cb}article{border-top:1px solid #52616b;'
             'padding:18px 0}pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#202c34;padding:18px}'
             'summary{cursor:pointer}small{color:#b2bfc6}code{overflow-wrap:anywhere}</style>',
             '<h1>Нереида: от частного наблюдения к последствию</h1>',
             '<p>Офлайн-проверка N1–N3. Решения задаёт лабораторный двойник, '
             'а последствия — существующий мир. Это не живая модель, не внешний пилот и не HUMAN gate.</p>',
             '<p>Во всех историях игрок осматривает затвор до развилки и снова после ожидания. '
             'Никто не обязан объяснять Арре причину изменения. Затвор не открывается.</p>',
             '<h2>Проверки</h2><ul>']
    for check in checks:
        parts.append(f'<li>{"PASS" if check.ok else "FAIL"} — {escape(check.name)}: {escape(check.detail)}</li>')
    parts.append('</ul>')
    for branch in branches:
        graph = creator_graph(branch.loop.session)
        parts.extend([f'<article><h2>{escape(branch.name)}</h2>',
                      f'<p>{escape(branch.description)}</p>',
                      '<h3>Личный опыт Арры</h3>', f'<pre>{escape(branch.transcript)}</pre>',
                      '<h3>Только для создателя: причинная цепь</h3>'])
        session = branch.loop.session
        for decision in session.project_trace.decisions:
            issued = [i for i in session.project_trace.intents if i.decision_ref == decision.ref]
            label = ", ".join(i.params.get("verb", i.intent_type) for i in issued) or "отложить действие"
            parts.append(f'<p>Минута {decision.game_minute}: {escape(label)}. '
                         f'Ссылки использованных сведений: {escape(", ".join(decision.subjective_evidence_refs) or "нет")}.</p>')
        for action in session.affordances.action_traces:
            if action.subject_id == "nereid_01" and action.action_type.value == "shift_local_silt":
                target = session.affordances.perceptions.for_subject("arra")[-1].ref
                path = causal_path(graph, action.ref, target)
                resolution = next((r for r in session.project_trace.resolutions
                                   if action.event_id is not None and action.event_id in r.result_event_ids), None)
                if resolution and path:
                    intent = next(i for i in session.project_trace.intents if i.ref == resolution.intent_ref)
                    decision = next(d for d in session.project_trace.decisions if d.ref == intent.decision_ref)
                    path = (decision.project_ref, decision.ref, intent.ref, *path)
                parts.append(f'<p>Попытка {action.start_minute}–{action.end_minute}; '
                             f'осмотр {session.world.game_minute}; '
                             f'после работы прошло {session.world.game_minute-action.end_minute} минут.</p>')
                parts.append(f'<pre>{escape(" → ".join(path) or "Нет причинного пути: действие не изменило мир.")}</pre>')
        parts.append('<details><summary>Производный граф и исходные ссылки</summary><pre>')
        parts.append(escape(json.dumps(graph, ensure_ascii=False, indent=2)))
        parts.append('</pre></details></article>')
    parts.append('</html>')
    return '\n'.join(parts)
