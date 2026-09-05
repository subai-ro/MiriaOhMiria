from __future__ import annotations

from dataclasses import dataclass

from .affordances import GATE_TARGET, PhysicalActionRequest, PhysicalActionType
from .pilot_playable import (
    PILOT_I1_PREHISTORY_MINUTES,
    PilotLoop,
    PilotPlayerView,
    create_pilot_i1_loop,
)


@dataclass(frozen=True)
class PilotI1TrialCheck:
    name: str
    ok: bool
    detail: str


@dataclass(frozen=True)
class PilotI1Branch:
    name: str
    loop: PilotLoop
    pre_answer_view: PilotPlayerView | None
    words_before_settling: tuple[str, ...]


@dataclass(frozen=True)
class PilotI1AcceptanceResult:
    checks: tuple[PilotI1TrialCheck, ...]
    h0: PilotI1Branch
    h1: PilotI1Branch
    h2: PilotI1Branch
    exploration: PilotLoop

    @property
    def passed(self) -> bool:
        return all(check.ok for check in self.checks)


def _run_branch(name: str, seed: int) -> PilotI1Branch:
    loop = create_pilot_i1_loop(seed=seed)
    inspection = loop.inspect()
    if not inspection.ok:
        raise AssertionError(inspection.message)

    pre_answer_view: PilotPlayerView | None = None
    if name == "H0":
        for minutes in (60, 1):
            result = loop.wait(minutes)
            if not result.ok:
                raise AssertionError(result.message)
    else:
        prayer = loop.pray_to_death()
        if not prayer.ok:
            raise AssertionError(prayer.message)
        waiting = loop.wait(60)
        if not waiting.ok:
            raise AssertionError(waiting.message)
        pre_answer_view = loop.player_view()
        if name == "H1":
            answer = loop.answer("The bank looked ordinary. I found nothing unusual.")
        elif name == "H2":
            answer = loop.answer(
                "I saw exposed bones in the bank, and I think the dead are calling."
            )
        else:
            raise ValueError(f"unknown I1 branch: {name}")
        if not answer.ok:
            raise AssertionError(answer.message)

    words_before_settling = loop.player_view().received_words
    settled = loop.wait(360)
    if not settled.ok:
        raise AssertionError(settled.message)
    return PilotI1Branch(name, loop, pre_answer_view, words_before_settling)


def _causal_chain(loop: PilotLoop) -> tuple[int, int, int, int] | None:
    event_by_type = {
        event.event_type: event
        for event in loop.session.ledger.events
        if event.event_type
        in {
            "PRAYER_OFFERED",
            "DIVINE_PROBE_MANIFESTED",
            "DIEGETIC_SPEECH",
            "DIVINE_OMEN_SENT",
        }
    }
    if len(event_by_type) != 4:
        return None
    prayer = event_by_type["PRAYER_OFFERED"]
    probe = event_by_type["DIVINE_PROBE_MANIFESTED"]
    response = event_by_type["DIEGETIC_SPEECH"]
    omen = event_by_type["DIVINE_OMEN_SENT"]
    if (
        probe.causal_parent_ids != (prayer.event_id,)
        or response.causal_parent_ids != (probe.event_id,)
        or omen.causal_parent_ids != (response.event_id,)
    ):
        return None
    return prayer.event_id, probe.event_id, response.event_id, omen.event_id


def run_pilot_i1_acceptance(*, seed: int = 42) -> PilotI1AcceptanceResult:
    h0 = _run_branch("H0", seed)
    h1 = _run_branch("H1", seed)
    h2 = _run_branch("H2", seed)
    repeat_h2 = _run_branch("H2", seed)

    exploration = create_pilot_i1_loop(seed=seed)
    before_same_site = (
        exploration.session.world.game_minute,
        exploration.navigation.current_site.site_id,
        len(exploration.session.ledger.events),
    )
    same_site = exploration.execute("go bank")
    after_same_site = (
        exploration.session.world.game_minute,
        exploration.navigation.current_site.site_id,
        len(exploration.session.ledger.events),
    )
    before_remote_target = after_same_site
    remote_look = exploration.execute("look gallery")
    remote_inspection = exploration.execute("inspect gallery")
    after_remote_target = (
        exploration.session.world.game_minute,
        exploration.navigation.current_site.site_id,
        len(exploration.session.ledger.events),
    )
    before_invalid = (
        exploration.session.world.game_minute,
        exploration.navigation.current_site.site_id,
        len(exploration.session.ledger.events),
    )
    invalid = exploration.move("gallery")
    after_invalid = (
        exploration.session.world.game_minute,
        exploration.navigation.current_site.site_id,
        len(exploration.session.ledger.events),
    )
    upper_inspection = exploration.inspect()
    gate_move = exploration.move("gate")
    gate_inspection = exploration.inspect()
    owned_before_foreign = exploration.player_view().observations
    foreign_inspection = exploration.session.perform(
        PhysicalActionRequest(
            "nereid_01",
            PhysicalActionType.INSPECT_GATE,
            GATE_TARGET,
        )
    )
    gate_view = exploration.player_view()
    gallery_move = exploration.move("gallery")
    gallery_inspection = exploration.inspect()
    exploration_view = exploration.player_view()
    h1_view = h1.loop.player_view()
    h1_journal = h1.loop.execute("journal")

    h0_words = h0.loop.player_view().received_words
    h1_words = h1.loop.player_view().received_words
    h2_words = h2.loop.player_view().received_words
    branch_minutes = {
        h0.loop.session.world.game_minute,
        h1.loop.session.world.game_minute,
        h2.loop.session.world.game_minute,
    }
    chain = _causal_chain(h2.loop)
    false_response = next(
        event
        for event in h2.loop.session.ledger.events
        if event.event_type == "DIEGETIC_SPEECH"
    )
    arra = next(
        item for item in exploration.session.affordances.subjects if item.subject_id == "arra"
    )
    safe_view_payload = str(exploration_view.as_dict()).casefold()
    forbidden_view_tokens = (
        "aqueous",
        "echo",
        "impulse",
        "intensity",
        "source",
        "hydrology",
        "ledger",
        "state_hash",
        "god_death",
        "underpeak_gallery_sump",
    )
    forbidden_event_types = ("QUEST", "ENDING", "STORY_DIRECTOR")

    checks = (
        PilotI1TrialCheck(
            "the world advances through autonomous prehistory before player action",
            h0.loop.started_minute == PILOT_I1_PREHISTORY_MINUTES
            and len(
                [
                    run
                    for run in h0.loop.session.world_process_runtime.runs
                    if run.game_minute <= h0.loop.started_minute
                ]
            )
            == 4
            and not any(
                "arra" in event.actor_ids
                for event in h0.loop.session.ledger.events
                if event.game_minute <= h0.loop.started_minute
            ),
            (
                f"start_minute={h0.loop.started_minute}; "
                "prehistory_process_runs="
                f"{len([run for run in h0.loop.session.world_process_runtime.runs if run.game_minute <= h0.loop.started_minute])}"
            ),
        ),
        PilotI1TrialCheck(
            "I1 remains an adapter over one frozen PilotSession",
            exploration.navigation.session is exploration.session
            and exploration.session.engine.world is exploration.session.world
            and exploration.session.project_trace.ledger is exploration.session.ledger,
            "navigation, world, clock, Project trace and Ledger share one composition",
        ),
        PilotI1TrialCheck(
            "Nereid Death and Trade motives predate the player loop",
            all(
                exploration.session.projects.get(project_id).created_minute == 0
                for project_id in (
                    "nereid_return_underpeak",
                    "death_preserve_truthful_memory",
                    "trade_house_underpeak_route",
                )
            ),
            "three independent Projects were created at minute 0",
        ),
        PilotI1TrialCheck(
            "invalid local movement rejects before time state or Ledger mutation",
            not invalid.ok and before_invalid == after_invalid,
            f"rejected_atomically={before_invalid == after_invalid}",
        ),
        PilotI1TrialCheck(
            "movement to the current place reports already here and remains atomic",
            not same_site.ok
            and "already at" in same_site.message
            and before_same_site == after_same_site,
            f"clear_current_place={not same_site.ok}; atomic={before_same_site == after_same_site}",
        ),
        PilotI1TrialCheck(
            "look and inspect never ignore a remote place argument",
            not remote_look.ok
            and "cannot see" in remote_look.message
            and not remote_inspection.ok
            and "must be at" in remote_inspection.message
            and before_remote_target == after_remote_target,
            f"remote_targets_rejected_atomically={before_remote_target == after_remote_target}",
        ),
        PilotI1TrialCheck(
            "three authored places form one playable movement and inspection loop",
            upper_inspection.ok
            and gate_move.ok
            and gate_inspection.ok
            and gallery_move.ok
            and gallery_inspection.ok
            and len(exploration_view.observations) == 3,
            f"owned_observations={len(exploration_view.observations)}",
        ),
        PilotI1TrialCheck(
            "visible local presence does not expose every hidden subject",
            gate_view.visible_subjects == ("Trade House surveyors",)
            and foreign_inspection.ok
            and foreign_inspection.percept is not None
            and gate_view.observations == owned_before_foreign,
            f"visible_subjects={','.join(gate_view.visible_subjects)}; foreign_percept_withheld=True",
        ),
        PilotI1TrialCheck(
            "Arra still has no water_sense",
            arra.faculties == ("sight",),
            f"faculties={','.join(arra.faculties)}",
        ),
        PilotI1TrialCheck(
            "Player View exposes no technical or hidden-state vocabulary",
            all(token not in safe_view_payload for token in forbidden_view_tokens),
            f"forbidden_tokens_absent={all(token not in safe_view_payload for token in forbidden_view_tokens)}",
        ),
        PilotI1TrialCheck(
            "the journal separates observations received words and Arra's own replies",
            h1_journal.ok
            and len(h1_view.observations) == 1
            and len(h1_view.received_words) == 1
            and len(h1_view.spoken_words) == 1
            and all(
                heading in h1_journal.message
                for heading in ("Observations:", "Words received:", "Your replies:")
            ),
            "journal_sections=observations/received/replies; parallel_store=False",
        ),
        PilotI1TrialCheck(
            "I1 presents gate and gallery observations as natural player prose",
            gate_inspection.ok
            and gallery_inspection.ok
            and "the outflow is" in gate_inspection.message
            and "The route is blocked." in gallery_inspection.message
            and "the route blocked" not in gallery_inspection.message.casefold(),
            "presentation_adapter_uses_owned_cues=True",
        ),
        PilotI1TrialCheck(
            "H0 H1 and H2 share T0 and settle to the same world minute",
            len(branch_minutes) == 1,
            f"settled_minute={next(iter(branch_minutes)) if len(branch_minutes) == 1 else sorted(branch_minutes)}",
        ),
        PilotI1TrialCheck(
            "a lawful divine probe creates a real answer affordance",
            h1.pre_answer_view is not None
            and "Answer the grave-cold voice" in h1.pre_answer_view.available_actions,
            "H1 can answer only after the probe reached Arra",
        ),
        PilotI1TrialCheck(
            "H0 H1 and H2 have player-visible behavioral differences",
            len(h0_words) == 0 and len(h1_words) == 1 and len(h2_words) == 2,
            f"received_words={len(h0_words)}/{len(h1_words)}/{len(h2_words)}",
        ),
        PilotI1TrialCheck(
            "branch differences survive a six-hour autonomous settling period",
            h0.words_before_settling == h0_words
            and h1.words_before_settling == h1_words
            and h2.words_before_settling == h2_words,
            "visible manifestation histories remained 0/1/2 after settling",
        ),
        PilotI1TrialCheck(
            "false testimony can change Death behavior without becoming objective truth",
            len(h2_words) == 2
            and "heard, not proven" in h2_words[-1]
            and h2.loop.session.hydrology.state.burial_bank.exposure_fraction == 0.0
            and "verified" not in false_response.data
            and "truth" not in false_response.data,
            "Death emitted an additional omen while objective exposure remained 0.0",
        ),
        PilotI1TrialCheck(
            "H2 has a recoverable prayer probe response omen chain",
            chain is not None,
            " -> ".join(f"event:{event_id}" for event_id in chain) if chain else "broken",
        ),
        PilotI1TrialCheck(
            "identical I1 state seed intent and history resolve identically",
            tuple(event.as_dict() for event in h2.loop.session.ledger.events)
            == tuple(event.as_dict() for event in repeat_h2.loop.session.ledger.events)
            and h2.loop.player_view() == repeat_h2.loop.player_view()
            and h2.loop.session.divine_runtime.agent("death").thoughts
            == repeat_h2.loop.session.divine_runtime.agent("death").thoughts,
            f"events={len(h2.loop.session.ledger.events)}; visible_words={len(h2_words)}",
        ),
        PilotI1TrialCheck(
            "no Story Director quest or prescribed ending entered the history",
            not any(
                token in event.event_type
                for event in h2.loop.session.ledger.events
                for token in forbidden_event_types
            ),
            f"ledger_events={len(h2.loop.session.ledger.events)}; forbidden_events=0",
        ),
        PilotI1TrialCheck(
            "I1 informational runtimes stayed healthy",
            all(
                not loop.session.clock.errors
                and not loop.session.ledger.listener_errors
                and not loop.session.project_runtime.errors
                for loop in (h0.loop, h1.loop, h2.loop, exploration)
            ),
            "clock_errors=0; listener_errors=0; project_errors=0",
        ),
    )
    return PilotI1AcceptanceResult(checks, h0, h1, h2, exploration)
