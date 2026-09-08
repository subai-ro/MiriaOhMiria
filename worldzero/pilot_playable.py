from __future__ import annotations

import json
from dataclasses import dataclass, replace
from functools import wraps
from typing import Any

from .affordances import (
    BANK_TARGET,
    GALLERY_TARGET,
    GATE_SITE,
    GATE_TARGET,
    LocalSubjectState,
    PhysicalActionRequest,
    PhysicalActionType,
    SubjectivePercept,
)
from .divine import (
    DivineActionType,
    DivineCognitivePosture,
    DivineDecision,
    DivineIntent,
    DivineMindState,
    DivinePercept,
)
from .models import Action, ActionType
from .pilot import AshValleyDeathBrain, PilotSession, create_pilot_i0_session


PILOT_I1_PREHISTORY_MINUTES = 12 * 60
UPPER_REACH_SITE = "underpeak_upper_reach"
GALLERY_SITE = GALLERY_TARGET
MOVE_DURATION_MINUTES = 15


@dataclass(frozen=True)
class PilotSite:
    site_id: str
    name: str
    description: str
    region_id: str
    neighbor_ids: tuple[str, ...]
    visible_objects: tuple[str, ...]
    visible_subjects: tuple[tuple[str, str], ...] = ()


PILOT_I1_SITES: tuple[PilotSite, ...] = (
    PilotSite(
        site_id=UPPER_REACH_SITE,
        name="The Underpeak Reach",
        description=(
            "Cold water presses past a rain-cut bank beneath the mountain. "
            "Loose grey silt gathers between dark stones."
        ),
        region_id="underpeak",
        neighbor_ids=(GATE_SITE,),
        visible_objects=("the river bank", "the cold channel", "a scatter of dark stones"),
    ),
    PilotSite(
        site_id=GATE_SITE,
        name="The Sealed River Gate",
        description=(
            "An ancient stone gate divides the channel. Fresh survey stakes stand "
            "beside old debris and a stubborn iron mechanism."
        ),
        region_id="underpeak",
        neighbor_ids=(UPPER_REACH_SITE, GALLERY_SITE),
        visible_objects=("the sealed river gate", "survey stakes", "water-dark debris"),
        visible_subjects=(("trade_house_01", "Trade House surveyors"),),
    ),
    PilotSite(
        site_id=GALLERY_SITE,
        name="The Old Gallery",
        description=(
            "A low gallery bends into the mountain. Fallen masonry narrows the way, "
            "and shallow water gleams across the floor."
        ),
        region_id="underpeak",
        neighbor_ids=(GATE_SITE,),
        visible_objects=("the flooded gallery", "fallen masonry", "an old drainage cut"),
    ),
)


class AshValleyI1DeathBrain:
    """I1 policy: a false alarming claim can cause a real but fallible omen."""

    _ALARMING_PHRASES = (
        "exposed bones",
        "uncovered bones",
        "bones in the bank",
        "opened grave",
        "dead are calling",
    )

    def __init__(self) -> None:
        self._base = AshValleyDeathBrain()

    def decide(self, percept: DivinePercept, state: DivineMindState) -> DivineDecision:
        decision = self._base.decide(percept, state)
        if decision.intents:
            return decision

        alarming_claims = tuple(
            item
            for item in percept.knowledge
            if item.event_type == "DIEGETIC_SPEECH"
            and item.response_to_probe_ref is not None
            and item.known_actor_ids
            and any(phrase in item.summary.casefold() for phrase in self._ALARMING_PHRASES)
        )
        if not alarming_claims:
            return decision

        claim = min(alarming_claims, key=lambda item: item.knowledge_id)
        actor_id = claim.known_actor_ids[0]
        state.actor_interest[actor_id] = max(0.35, state.actor_interest.get(actor_id, 0.0))
        omen = DivineIntent(
            action_type=DivineActionType.SEND_OMEN,
            target_actor_id=actor_id,
            location_id=claim.location_id,
            significance=0.48,
            message=(
                "Your claim is heard, not proven. The weight of those words will remain "
                "under my gaze."
            ),
            reason=(
                "the mortal gave an alarming response about the dead; the response is "
                "subjective testimony, not verified world truth"
            ),
            causal_event_ids=claim.source_event_ids,
        )
        note = (
            "The mortal's response sounds grave enough to acknowledge, but nothing in the "
            "percept proves that the claimed remains exist or are exposed."
        )
        return replace(
            decision,
            goal="Hold the alarming testimony in attention without treating it as proven.",
            decision_note=f"{decision.decision_note} {note}".strip(),
            cognitive_posture=DivineCognitivePosture.INVESTIGATE,
            significance=max(decision.significance, omen.significance),
            intents=(omen,),
        )


@dataclass(frozen=True)
class PilotMovementResult:
    ok: bool
    message: str
    duration_minutes: int = 0
    event_id: int | None = None


class PilotNavigation:
    """Authoritative local movement using the existing mutable local body state."""

    def __init__(
        self,
        session: PilotSession,
        *,
        subject_id: str = "arra",
        sites: tuple[PilotSite, ...] = PILOT_I1_SITES,
    ) -> None:
        self.session = session
        self.subject_id = subject_id
        self._sites = {site.site_id: site for site in sites}
        if len(self._sites) != len(sites):
            raise ValueError("pilot site ids must be unique")
        _ = self.current_site

    @property
    def sites(self) -> tuple[PilotSite, ...]:
        return tuple(self._sites[key] for key in sorted(self._sites))

    @property
    def current_site(self) -> PilotSite:
        subject = self._subject()
        if len(subject.present_site_ids) != 1:
            raise ValueError("playable subject must occupy exactly one pilot site")
        site_id = subject.present_site_ids[0]
        try:
            return self._sites[site_id]
        except KeyError as exc:
            raise ValueError(f"subject is outside the playable pilot sites: {site_id}") from exc

    def move(self, destination_site_id: str) -> PilotMovementResult:
        start = self.session.world.game_minute
        result = self.session.clock.run_action(lambda: self._move(destination_site_id))
        if self.session.clock.serial_actions:
            result = replace(result, duration_minutes=self.session.world.game_minute - start)
        return result

    def _move(self, destination_site_id: str) -> PilotMovementResult:
        destination_site_id = " ".join(str(destination_site_id).split())
        destination = self._sites.get(destination_site_id)
        if destination is None:
            return PilotMovementResult(False, "That place is not reachable from here.")

        origin = self.current_site
        if destination.site_id == origin.site_id:
            return PilotMovementResult(False, f"You are already at {origin.name}.")
        if destination.site_id not in origin.neighbor_ids:
            return PilotMovementResult(False, "There is no direct path there from here.")

        actor = self.session.world.actors.get(self.subject_id)
        if actor is None:
            return PilotMovementResult(False, "The traveller has no body in this world.")
        if origin.region_id != actor.location_id or destination.region_id != actor.location_id:
            return PilotMovementResult(False, "That path leaves the traveller's present region.")

        subject = self._subject()
        start_minute = self.session.world.game_minute
        self.session.advance(MOVE_DURATION_MINUTES)
        subject.present_site_ids = (destination.site_id,)
        event = self.session.ledger.append(
            game_minute=self.session.world.game_minute,
            event_type="LOCAL_SITE_TRAVERSED",
            actor_ids=(self.subject_id,),
            location_id=destination.region_id,
            tags=("locality", "movement", "travel"),
            publicity=0.55,
            secrecy=0.0,
            data={
                "from_site_id": origin.site_id,
                "to_site_id": destination.site_id,
                "duration_minutes": self.session.world.game_minute - start_minute,
            },
        )
        return PilotMovementResult(
            True,
            f"You walk to {destination.name}.",
            duration_minutes=MOVE_DURATION_MINUTES,
            event_id=event.event_id,
        )

    def _subject(self) -> LocalSubjectState:
        subject = next(
            (item for item in self.session.affordances.subjects if item.subject_id == self.subject_id),
            None,
        )
        if subject is None:
            raise ValueError(f"unknown local subject: {self.subject_id}")
        return subject


@dataclass(frozen=True)
class PilotPlayerView:
    time: str
    location: str
    location_id: str
    description: str
    visible_subjects: tuple[str, ...]
    visible_objects: tuple[str, ...]
    observations: tuple[str, ...]
    received_words: tuple[str, ...]
    spoken_words: tuple[str, ...]
    available_actions: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "time": self.time,
            "location": self.location,
            "location_id": self.location_id,
            "description": self.description,
            "visible_subjects": list(self.visible_subjects),
            "visible_objects": list(self.visible_objects),
            "observations": list(self.observations),
            "received_words": list(self.received_words),
            "spoken_words": list(self.spoken_words),
            "available_actions": list(self.available_actions),
        }


@dataclass(frozen=True)
class PilotCommandResult:
    ok: bool
    message: str
    minutes_elapsed: int = 0


def _player_action(method):
    """Keep nested navigation/session calls inside the whole player commit."""
    @wraps(method)
    def wrapped(self, *args, **kwargs):
        start = self.session.world.game_minute
        result = self.session.clock.run_action(lambda: method(self, *args, **kwargs))
        if self.session.clock.serial_actions:
            result = replace(result, minutes_elapsed=self.session.world.game_minute - start)
        return result
    return wrapped


class PilotLoop:
    """Small guided terminal loop over one authoritative PilotSession."""

    _SITE_ALIASES = {
        "bank": UPPER_REACH_SITE,
        "reach": UPPER_REACH_SITE,
        "gate": GATE_SITE,
        "gallery": GALLERY_SITE,
    }

    def __init__(self, session: PilotSession, navigation: PilotNavigation) -> None:
        if navigation.session is not session:
            raise ValueError("pilot loop and navigation must share one PilotSession")
        self.session = session
        self.navigation = navigation
        self.started_minute = session.world.game_minute

    def player_view(self) -> PilotPlayerView:
        site = self.navigation.current_site
        subject_view = self.session.affordances.subject_view("arra")
        local_subjects = {
            item.subject_id: item for item in self.session.affordances.subjects
        }
        visible_subjects = tuple(
            label
            for subject_id, label in site.visible_subjects
            if subject_id in local_subjects
            and site.site_id in local_subjects[subject_id].present_site_ids
        )
        observations = tuple(_present_percept(item) for item in subject_view.percepts)
        received_words = tuple(
            item.message
            for item in self.session.divine_runtime.gateway.manifestations_for("arra")
        )
        spoken_words = tuple(
            text
            for event in self.session.ledger.events
            if event.event_type == "DIEGETIC_SPEECH" and "arra" in event.actor_ids
            for text in (event.data.get("text"),)
            if isinstance(text, str) and text.strip()
        )
        actions = ["Inspect this place", "Pray to Death", "Wait and let time pass"]
        actions.extend(
            f"Walk to {self._site(destination).name}"
            for destination in site.neighbor_ids
        )
        if self._latest_unanswered_probe_ref() is not None:
            actions.append("Answer the grave-cold voice")
        if site.site_id == GATE_SITE:
            actions.append("Work the gate's silt")
        return PilotPlayerView(
            time=self.session.world.formatted_time,
            location=site.name,
            location_id=site.site_id,
            description=site.description,
            visible_subjects=visible_subjects,
            visible_objects=site.visible_objects,
            observations=observations,
            received_words=received_words,
            spoken_words=spoken_words,
            available_actions=tuple(actions),
        )

    @_player_action
    def inspect(self) -> PilotCommandResult:
        site_id = self.navigation.current_site.site_id
        requests = {
            UPPER_REACH_SITE: PhysicalActionRequest(
                "arra", PhysicalActionType.INSPECT_BANK, BANK_TARGET
            ),
            GATE_SITE: PhysicalActionRequest(
                "arra", PhysicalActionType.INSPECT_GATE, GATE_TARGET
            ),
            GALLERY_SITE: PhysicalActionRequest(
                "arra", PhysicalActionType.SURVEY_GALLERY, GALLERY_TARGET
            ),
        }
        request = requests[site_id]
        result = self.session.perform(request)
        if not result.ok or result.percept is None:
            return PilotCommandResult(False, result.message)
        return PilotCommandResult(
            True,
            _present_percept(result.percept),
            minutes_elapsed=result.duration_minutes,
        )

    @_player_action
    def move(self, destination: str) -> PilotCommandResult:
        key = " ".join(str(destination).strip().casefold().split())
        destination_id = self._SITE_ALIASES.get(key, key)
        result = self.navigation.move(destination_id)
        return PilotCommandResult(result.ok, result.message, result.duration_minutes)

    @_player_action
    def work_gate_silt(self, argument: str = "") -> PilotCommandResult:
        if self.navigation.current_site.site_id != GATE_SITE:
            return PilotCommandResult(False, "You can only work on the gate silt from the gate itself.")
        effort = self._parse_effort(argument)
        if effort is None:
            return PilotCommandResult(False, "Effort must be a number between 0 and 1, for example: work gate 0.5.")
        result = self.session.perform(
            PhysicalActionRequest(
                "arra",
                PhysicalActionType.SHIFT_LOCAL_SILT,
                GATE_TARGET,
                params={"effort": effort},
            )
        )
        if not result.ok:
            return PilotCommandResult(False, result.message)
        return PilotCommandResult(True, result.message, result.duration_minutes)

    @_player_action
    def pray_to_death(self) -> PilotCommandResult:
        result = self.session.apply(
            Action("arra", ActionType.PRAY, params={"deity": "death"})
        )
        if not result.ok:
            return PilotCommandResult(False, result.message)
        return PilotCommandResult(True, "You offer a quiet prayer to Death.")

    def wait(self, minutes: int = 60) -> PilotCommandResult:
        if isinstance(minutes, bool) or not isinstance(minutes, int) or not 1 <= minutes <= 360:
            return PilotCommandResult(False, "Choose a wait between 1 and 360 minutes.")
        start = self.session.world.game_minute
        self.session.advance(minutes)
        elapsed = self.session.world.game_minute - start if self.session.clock.serial_actions else minutes
        return PilotCommandResult(
            True,
            f"You wait for {elapsed} minutes while the world continues.",
            minutes_elapsed=elapsed,
        )

    @_player_action
    def answer(self, text: str) -> PilotCommandResult:
        probe_ref = self._latest_unanswered_probe_ref()
        if probe_ref is None:
            return PilotCommandResult(False, "No voice is waiting for an answer.")
        statement = " ".join(str(text).split())
        if not statement:
            return PilotCommandResult(False, "Your answer cannot be empty.")
        result = self.session.apply(
            Action(
                "arra",
                ActionType.SPEAK,
                params={
                    "text": statement,
                    "audience": "private",
                    "response_to_probe_ref": probe_ref,
                },
            )
        )
        if not result.ok:
            return PilotCommandResult(False, result.message)
        self.session.advance(1)
        return PilotCommandResult(True, "You answer the grave-cold voice.", minutes_elapsed=1)

    def execute(self, command: str) -> PilotCommandResult:
        cleaned = " ".join(str(command).strip().split())
        if not cleaned:
            return PilotCommandResult(False, "Enter an action or type help.")
        verb, _, argument = cleaned.partition(" ")
        verb = verb.casefold()
        if verb in {"look", "l"}:
            target_error = self._target_error(argument, verb="look")
            if target_error is not None:
                return target_error
            return PilotCommandResult(True, self.navigation.current_site.description)
        if verb in {"inspect", "i"}:
            target_error = self._target_error(argument, verb="inspect")
            if target_error is not None:
                return target_error
            return self.inspect()
        if verb in {"go", "move", "walk"}:
            if not argument:
                return PilotCommandResult(False, "Choose bank, gate, or gallery.")
            return self.move(argument)
        if verb in {"pray", "p"}:
            return self.pray_to_death()
        if verb in {"map", "viz", "v"}:
            return PilotCommandResult(True, "\n".join(render_player_map(self.player_view())))
        if verb in {"work", "shift", "clear"}:
            return self.work_gate_silt(argument)
        if verb in {"wait", "w"}:
            if not argument:
                return self.wait()
            try:
                minutes = int(argument)
            except ValueError:
                return PilotCommandResult(False, "Waiting time must be a whole number of minutes.")
            return self.wait(minutes)
        if verb in {"answer", "say"}:
            return self.answer(argument)
        if verb in {"journal", "j"}:
            return PilotCommandResult(True, render_player_journal(self.player_view()))
        if verb in {"help", "h", "?"}:
            return PilotCommandResult(
                True,
                "Commands: look, map, inspect, go bank/gate/gallery, work gate [effort], "
                "pray, wait [minutes], answer <words>, journal, quit.",
            )
        return PilotCommandResult(False, "You cannot do that here. Type help.")

    def _target_error(self, argument: str, *, verb: str) -> PilotCommandResult | None:
        if not argument:
            return None
        key = " ".join(argument.strip().casefold().split())
        destination_id = self._SITE_ALIASES.get(key)
        if destination_id is None:
            return PilotCommandResult(
                False,
                f"{verb.title()} describes the place you are standing in. "
                "Use go bank, go gate, or go gallery to travel.",
            )
        current = self.navigation.current_site
        if destination_id == current.site_id:
            return None
        destination = self._site(destination_id)
        if verb == "look":
            message = f"You cannot see {destination.name} from here. Walk there first."
        else:
            message = f"You must be at {destination.name} before you can inspect it."
        return PilotCommandResult(False, message)

    def _latest_unanswered_probe_ref(self) -> str | None:
        answered = {
            str(event.data["response_to_probe_ref"])
            for event in self.session.ledger.events
            if event.event_type == "DIEGETIC_SPEECH"
            and isinstance(event.data.get("response_to_probe_ref"), str)
            and "arra" in event.actor_ids
        }
        for probe in reversed(self.session.divine_runtime.gateway.probes_for("god_death")):
            if probe.target_actor_id == "arra" and probe.probe_ref not in answered:
                return probe.probe_ref
        return None

    @staticmethod
    def _parse_effort(argument: str) -> float | None:
        argument = " ".join(str(argument).strip().casefold().split())
        if not argument:
            return 1.0

        allowed_tokens = {"gate", "silt", "debris", "throat", "work", "shift"}
        for part in argument.split():
            if part in allowed_tokens:
                continue
            try:
                effort = float(part)
            except (TypeError, ValueError):
                continue
            if not 0.0 < effort <= 1.0:
                return None
            return effort
        if any(part in allowed_tokens for part in argument.split()):
            return 1.0
        return None

    def _site(self, site_id: str) -> PilotSite:
        return next(site for site in self.navigation.sites if site.site_id == site_id)


def create_pilot_i1_loop(
    *,
    seed: int = 42,
    prehistory_minutes: int = PILOT_I1_PREHISTORY_MINUTES,
    serial_actions: bool = False,
) -> PilotLoop:
    if (
        isinstance(prehistory_minutes, bool)
        or not isinstance(prehistory_minutes, int)
        or prehistory_minutes < 0
    ):
        raise ValueError("prehistory_minutes must be a non-negative integer")

    session = create_pilot_i0_session(seed=seed, synthetic_actors=0, serial_actions=serial_actions)
    session.divine_runtime.agent("death").brain = AshValleyI1DeathBrain()
    arra = next(item for item in session.affordances.subjects if item.subject_id == "arra")
    arra.capability_levels.update(
        {
            PhysicalActionType.INSPECT_GATE.value: 0.58,
            PhysicalActionType.SURVEY_GALLERY.value: 0.52,
            PhysicalActionType.SHIFT_LOCAL_SILT.value: 0.35,
        }
    )
    if prehistory_minutes:
        session.advance(prehistory_minutes)
    navigation = PilotNavigation(session)
    return PilotLoop(session, navigation)


def render_player_view(view: PilotPlayerView) -> str:
    lines = [f"{view.time} - {view.location}", *render_player_map(view)]
    lines.append(view.description)
    if view.visible_subjects:
        lines.append("People here: " + ", ".join(view.visible_subjects))
    if view.visible_objects:
        lines.append("You can see: " + ", ".join(view.visible_objects))
    journal = _journal_lines(view)
    if journal:
        lines.append("Your journal:")
        lines.extend(f"  {item}" for item in journal)
    lines.append("Possible actions:")
    lines.extend(f"  - {item}" for item in view.available_actions)
    return "\n".join(lines)



def render_player_map(view: PilotPlayerView) -> tuple[str, ...]:
    reach = _map_node(UPPER_REACH_SITE, view.location_id, "The Underpeak Reach")
    gate = _map_node(GATE_SITE, view.location_id, "The Sealed River Gate")
    gallery = _map_node(GALLERY_SITE, view.location_id, "The Old Gallery")
    return (
        "Navigation map:",
        f"{reach} -- walk -- {gate} -- walk -- {gallery}",
        "  * = your current location",
    )


def _map_node(site_id: str, current_site_id: str, label: str) -> str:
    if site_id == current_site_id:
        return f"[{label}*]"
    return f"[{label}]"

def render_player_journal(view: PilotPlayerView) -> str:
    lines = _journal_lines(view)
    return "\n".join(lines) if lines else "Your journal is still empty."


def _journal_lines(view: PilotPlayerView) -> list[str]:
    lines: list[str] = []
    for heading, entries in (
        ("Observations:", view.observations),
        ("Words received:", view.received_words),
        ("Your replies:", view.spoken_words),
    ):
        if not entries:
            continue
        lines.append(heading)
        lines.extend(f"  - {item}" for item in entries)
    return lines


def _present_percept(percept: SubjectivePercept) -> str:
    try:
        cues = json.loads(percept.cues_json)
    except (TypeError, ValueError, json.JSONDecodeError):
        return percept.summary
    if not isinstance(cues, dict):
        return percept.summary

    if percept.observation_type == PhysicalActionType.INSPECT_GATE.value:
        position = _cue_words(cues, "visible_sluice")
        debris = _cue_words(cues, "visible_debris")
        condition = _cue_words(cues, "mechanism_condition")
        flow = _cue_words(cues, "outflow_cue")
        if all((position, debris, condition, flow)):
            return (
                f"The sluice appears {position}. Debris around it is {debris}. "
                f"The mechanism looks {condition}, and the outflow is {flow}."
            )

    if percept.observation_type == PhysicalActionType.SURVEY_GALLERY.value:
        rubble = str(cues.get("visible_rubble", ""))
        wetness = _cue_words(cues, "visible_wetness")
        route_value = str(cues.get("route_impression", ""))
        route = {
            "blocked": "is blocked",
            "appears_passable": "appears passable",
            "appears_hazardous": "appears hazardous",
            "appears_impassable": "appears impassable",
        }.get(route_value, route_value.replace("_", " "))
        rubble_words = {
            "clear": "clear",
            "scattered": "scattered with rubble",
            "difficult": "difficult to cross",
            "heavy_blockage": "heavily blocked",
        }.get(rubble, rubble.replace("_", " "))
        if all((rubble_words, wetness, route)):
            return f"The gallery is {rubble_words} and {wetness}. The route {route}."

    return percept.summary


def _cue_words(cues: dict[str, Any], key: str) -> str:
    value = cues.get(key)
    return value.replace("_", " ") if isinstance(value, str) else ""
