from __future__ import annotations

from dataclasses import dataclass

from .models import Action, ActionType
from .pilot import (
    DEATH_PROJECT_ID,
    AshValleyDeathBrain,
    PilotSession,
    create_pilot_i0_session,
    inspect_arra_bank,
)
from .processes.aqueous_echo import EchoSenseRequest


@dataclass(frozen=True)
class PilotI0TrialCheck:
    name: str
    ok: bool
    detail: str


@dataclass(frozen=True)
class PilotI0AcceptanceResult:
    checks: tuple[PilotI0TrialCheck, ...]
    session: PilotSession

    @property
    def passed(self) -> bool:
        return all(check.ok for check in self.checks)


def _exercise_visible_branch(seed: int) -> tuple[PilotSession, object, object, object, tuple]:
    session = create_pilot_i0_session(seed=seed)
    inspection = inspect_arra_bank(session)
    if not inspection.ok or inspection.percept is None or inspection.event_id is None:
        raise AssertionError(inspection.message)
    prayer = session.apply(Action("arra", ActionType.PRAY, params={"deity": "death"}))
    if not prayer.ok or prayer.event_id is None:
        raise AssertionError(prayer.message)
    session.advance(60)
    probes = session.divine_runtime.gateway.probes_for("god_death")
    if len(probes) != 1:
        raise AssertionError(f"expected one probe, got {len(probes)}")
    probe = probes[0]
    response = session.apply(
        Action(
            "arra",
            ActionType.SPEAK,
            params={
                "text": "I saw exposed bones in the bank, and I think the dead are calling.",
                "audience": "private",
                "response_to_probe_ref": probe.probe_ref,
            },
        )
    )
    if not response.ok or response.event_id is None:
        raise AssertionError(response.message)
    session.advance(1)
    return session, inspection, prayer, response, probes


def run_pilot_i0_acceptance(*, seed: int = 42) -> PilotI0AcceptanceResult:
    session, inspection, prayer, response, probes = _exercise_visible_branch(seed)
    repeat, _, _, _, repeat_probes = _exercise_visible_branch(seed)
    probe = probes[0]
    death_knowledge = session.heralds.knowledge("death")
    arra = next(item for item in session.affordances.subjects if item.subject_id == "arra")

    echo_before = (
        session.world.game_minute,
        session.aqueous_echo.state.state_hash(),
        len(session.ledger.events),
    )
    echo_rejection = session.sense_echo(EchoSenseRequest("arra", "underpeak_upper_reach"))
    echo_after = (
        session.world.game_minute,
        session.aqueous_echo.state.state_hash(),
        len(session.ledger.events),
    )

    hidden = create_pilot_i0_session(seed=seed)
    hidden.world.actors["arra"].traits["divine_event_veil"] = 1.0
    hidden_prayer = hidden.apply(
        Action("arra", ActionType.PRAY, params={"deity": "death"})
    )
    hidden.advance(60)

    subjective_payload = " ".join(
        " ".join((item.event_type, item.location_id, item.summary, *item.tags))
        for item in death_knowledge
    ).casefold()
    forbidden_truth = (
        "underpeak_burial_shelf",
        "exposure_fraction",
        "cover_depth_equiv",
        "state_hash",
        "aqueous",
        "silver echo",
        "ordinary_bank",
    )
    inspection_event_id = inspection.event_id
    prayer_event_id = prayer.event_id
    response_event = session.ledger.events[response.event_id - 1]
    response_knowledge = next(
        item for item in death_knowledge if response.event_id in item.source_event_ids
    )
    probe_window = probe.followup_game_minute - probe.opened_game_minute

    checks = (
        PilotI0TrialCheck(
            "PilotSession is composition, not a parallel world engine",
            session.engine.world is session.world
            and session.hydrology.world is session.world
            and session.aqueous_echo.world is session.world
            and session.divine_runtime.gateway.world is session.world,
            f"world_identities_shared={session.engine.world is session.hydrology.world is session.world}",
        ),
        PilotI0TrialCheck(
            "Ledger and subjective evidence reuse existing stores",
            session.engine.ledger is session.ledger
            and session.project_trace.ledger is session.ledger
            and session.affordances.perceptions is session.aqueous_echo_sensing.perceptions,
            "one Ledger; one LocalPerceptionStore shared by physical and Echo bridges",
        ),
        PilotI0TrialCheck(
            "Death participates as the existing D.1.4.2 divine agent",
            session.divine_runtime.agent("death").entity_id == "god_death"
            and isinstance(session.divine_runtime.agent("death").brain, AshValleyDeathBrain)
            and session.projects.get(DEATH_PROJECT_ID).owner_id == "god_death",
            f"agent={session.divine_runtime.agent('death').entity_id}; project={DEATH_PROJECT_ID}",
        ),
        PilotI0TrialCheck(
            "Arra has ordinary sight but no water_sense",
            arra.faculties == ("sight",) and not echo_rejection.ok and echo_before == echo_after,
            f"faculties={','.join(arra.faculties)}; rejected_atomically={echo_before == echo_after}",
        ),
        PilotI0TrialCheck(
            "Arra's bank view contains only ordinary local cues",
            set(inspection.percept.cues) == {"surface_signs", "visible_stability"}
            and all(
                token not in f"{inspection.percept.summary} {inspection.percept.cues}".casefold()
                for token in ("echo", "impulse", "intensity", "source")
            ),
            f"cues={','.join(sorted(inspection.percept.cues))}",
        ),
        PilotI0TrialCheck(
            "Private bank inspection is not delivered to Death",
            not any(inspection_event_id in item.source_event_ids for item in death_knowledge),
            f"inspection_event={inspection_event_id}; death_knowledge={len(death_knowledge)}",
        ),
        PilotI0TrialCheck(
            "A perceived death prayer can justify exactly one bounded probe",
            len(probes) == 1
            and probe.causal_event_ids == (prayer_event_id,)
            and probe_window == 60,
            f"prayer={prayer_event_id}; probe={probe.probe_ref}; window={probe_window}",
        ),
        PilotI0TrialCheck(
            "Death receives no Hydrology Burial or Echo answer key",
            all(token not in subjective_payload for token in forbidden_truth),
            f"forbidden_tokens_absent={all(token not in subjective_payload for token in forbidden_truth)}",
        ),
        PilotI0TrialCheck(
            "A metaphysical veil can make Death miss the prayer",
            hidden_prayer.ok
            and not hidden.heralds.knowledge("death")
            and not hidden.divine_runtime.gateway.probes_for("god_death"),
            f"archive_entries={len(hidden.archive.entries)}; death_knowledge={len(hidden.heralds.knowledge('death'))}",
        ),
        PilotI0TrialCheck(
            "Mortal testimony remains a claim rather than verified truth",
            response_knowledge.response_to_probe_ref == probe.probe_ref
            and "exposed bones" in response_knowledge.summary
            and session.hydrology.state.burial_bank.exposure_fraction == 0.0
            and "verified" not in response_event.data
            and "truth" not in response_event.data,
            "Death heard the claim while objective burial exposure remained 0.0",
        ),
        PilotI0TrialCheck(
            "Prayer probe and response preserve recoverable causal parentage",
            session.ledger.events[probe.manifestation_event_id - 1].causal_parent_ids
            == (prayer_event_id,)
            and response_event.causal_parent_ids == (probe.manifestation_event_id,),
            f"event:{prayer_event_id} -> event:{probe.manifestation_event_id} -> event:{response.event_id}",
        ),
        PilotI0TrialCheck(
            "Identical state seed intent and history resolve identically",
            tuple(event.as_dict() for event in session.ledger.events)
            == tuple(event.as_dict() for event in repeat.ledger.events)
            and probes == repeat_probes
            and session.divine_runtime.agent("death").thoughts
            == repeat.divine_runtime.agent("death").thoughts,
            f"events={len(session.ledger.events)}; probes={len(probes)}",
        ),
        PilotI0TrialCheck(
            "I0 runtimes stayed healthy",
            not session.clock.errors
            and not session.ledger.listener_errors
            and not session.project_runtime.errors,
            (
                f"clock_errors={len(session.clock.errors)}; "
                f"listener_errors={len(session.ledger.listener_errors)}; "
                f"project_errors={len(session.project_runtime.errors)}"
            ),
        ),
    )
    return PilotI0AcceptanceResult(checks=checks, session=session)
