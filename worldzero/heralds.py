from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .attention import PersonalAttentionField
from .archive import Archive, ArchiveEntry, describe_event
from .ledger import EventLedger, WorldEvent
from .models import WorldState
from .perception import PerceptualAspect, opposition_blocks
from .presence import DivinePresenceField, PresenceSnapshot


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, value))


class ReportPriority(str, Enum):
    IMMEDIATE = "immediate"
    DIGEST = "digest"
    ARCHIVE_ONLY = "archive_only"


@dataclass(frozen=True)
class ObserverProfile:
    entity_id: str
    name: str
    domain_weights: dict[str, float]
    sensory_tags: frozenset[str]
    sensory_strength: float


@dataclass(frozen=True)
class DivineReport:
    report_id: int
    entity_id: str
    priority: ReportPriority
    archive_entry_id: int
    game_minute: int
    source_event_ids: tuple[int, ...]
    known_actor_ids: tuple[str, ...]
    attention_score: float
    reason: str
    summary: str


@dataclass(frozen=True)
class RoutingDecision:
    event_id: int
    entity_id: str
    priority: ReportPriority
    relevance: float
    observability: float
    magnitude: float
    presence: float
    contextual_salience: float
    perception_score: float
    focus: float
    personal_attention: float
    attention_score: float
    actor_identity_known: bool
    reason: str


@dataclass(frozen=True)
class DivineKnowledge:
    knowledge_id: int
    entity_id: str
    archive_entry_id: int
    game_minute: int
    event_type: str
    source_event_ids: tuple[int, ...]
    tags: tuple[str, ...]
    location_id: str
    known_actor_ids: tuple[str, ...]
    confidence: float
    summary: str
    # A veiled subject is deliberately *not* an actor id. It is an opaque
    # cognitive handle for "someone was involved here, but I did not perceive
    # who".  Brains may reason about the handle, but actor-targeted server
    # faculties will never accept it as a mortal identity.
    veiled_subject_refs: tuple[str, ...] = ()
    # D.1.4 exposes this only for an explicitly linked response to this deity's
    # own probe, and only if the causal link itself survived perception.
    response_to_probe_ref: str | None = None


class DivineInbox:
    def __init__(self, entity_id: str) -> None:
        self.entity_id = entity_id
        self._immediate: list[DivineReport] = []
        self._digest: list[DivineReport] = []

    @property
    def immediate(self) -> tuple[DivineReport, ...]:
        return tuple(self._immediate)

    @property
    def digest(self) -> tuple[DivineReport, ...]:
        return tuple(self._digest)

    @property
    def all_reports(self) -> tuple[DivineReport, ...]:
        return tuple(sorted((*self._immediate, *self._digest), key=lambda report: report.report_id))

    def enqueue(self, report: DivineReport) -> None:
        if report.priority is ReportPriority.IMMEDIATE:
            self._immediate.append(report)
        elif report.priority is ReportPriority.DIGEST:
            self._digest.append(report)


DEFAULT_PROFILES: tuple[ObserverProfile, ...] = (
    ObserverProfile(
        entity_id="god_nature",
        name="God of Nature",
        domain_weights={
            "nature": 1.0,
            "logging": 1.0,
            "water": 0.75,
            "fishing": 0.35,
            "resource": 0.30,
            "lake": 0.20,
        },
        sensory_tags=frozenset({"nature", "logging", "water"}),
        sensory_strength=0.55,
    ),
    ObserverProfile(
        entity_id="god_death",
        name="God of Death",
        domain_weights={
            "death": 1.0,
            "necromancy": 1.0,
            "undead": 1.0,
            "temple": 0.55,
            "religion": 0.25,
            "magic": 0.35,
            "graveyard": 0.25,
        },
        sensory_tags=frozenset({"death", "necromancy", "undead"}),
        sensory_strength=0.55,
    ),
    ObserverProfile(
        entity_id="god_trade",
        name="God of Trade",
        domain_weights={
            "trade": 1.0,
            "economy": 1.0,
            "resource": 0.55,
            "religion": 0.15,
            "market": 0.25,
        },
        sensory_tags=frozenset({"trade", "economy"}),
        sensory_strength=0.40,
    ),
)


EVENT_MAGNITUDE: dict[str, float] = {
    "TEMPLE_DESTROYED": 0.95,
    "DEAD_RAISED": 0.68,
    "NECROMANCY_STUDIED": 0.22,
    "WOOD_HARVESTED": 0.06,
    "ITEM_SOLD": 0.04,
    "FISHED": 0.025,
    "PRAYER_OFFERED": 0.08,
    "DIEGETIC_SPEECH": 0.03,
    "TRAVELLED": 0.01,
    "SITE_VISITED": 0.01,
    "DIVINE_OMEN_SENT": 0.45,
    "DIVINE_PROBE_MANIFESTED": 0.45,
    "DIVINE_AREA_OMEN_MANIFESTED": 0.50,
    "DIVINE_FAVOR_GRANTED": 0.55,
    "DIVINE_DREAD_IMPOSED": 0.55,
}

OWNERSHIP_SENSITIVE_EVENTS = frozenset({"TEMPLE_DESTROYED"})


class HeraldSystem:
    """Turns objective events into Archive records and subjective divine reports."""

    def __init__(
        self,
        world: WorldState,
        archive: Archive | None = None,
        profiles: tuple[ObserverProfile, ...] = DEFAULT_PROFILES,
        presence_field: DivinePresenceField | None = None,
        attention_field: PersonalAttentionField | None = None,
    ) -> None:
        self.world = world
        self.archive = archive or Archive()
        self.profiles = {profile.entity_id: profile for profile in profiles}
        self.presence = presence_field or DivinePresenceField(world)
        self.attention = attention_field or PersonalAttentionField()
        self.inboxes = {entity_id: DivineInbox(entity_id) for entity_id in self.profiles}
        self.decisions: list[RoutingDecision] = []
        self._knowledge: dict[str, list[DivineKnowledge]] = {entity_id: [] for entity_id in self.profiles}
        self._processed_event_ids: set[int] = set()
        self._report_sequence = 0
        self._knowledge_sequence = 0
        self._trend_buckets: dict[tuple, list[WorldEvent]] = {}
        self._attached = False

    def attach(self, ledger: EventLedger) -> None:
        if self._attached:
            return
        for event in ledger.events:
            self.process_event(event)
        ledger.subscribe(self.process_event)
        self._attached = True

    def inbox(self, entity: str) -> DivineInbox:
        aliases = {
            "nature": "god_nature",
            "death": "god_death",
            "trade": "god_trade",
        }
        entity_id = aliases.get(entity, entity)
        return self.inboxes[entity_id]

    def knowledge(
        self,
        entity: str,
        *,
        tags: tuple[str, ...] = (),
        actor_id: str | None = None,
        location_id: str | None = None,
        limit: int = 20,
    ) -> tuple[DivineKnowledge, ...]:
        aliases = {"nature": "god_nature", "death": "god_death", "trade": "god_trade"}
        entity_id = aliases.get(entity, entity)
        required_tags = set(tags)
        results: list[DivineKnowledge] = []
        for item in reversed(self._knowledge[entity_id]):
            if required_tags and not required_tags.issubset(item.tags):
                continue
            if actor_id and actor_id not in item.known_actor_ids:
                continue
            if location_id and item.location_id != location_id:
                continue
            results.append(item)
            if len(results) >= limit:
                break
        return tuple(results)

    def knowledge_since(self, entity: str, knowledge_id: int = 0) -> tuple[DivineKnowledge, ...]:
        """Chronological subjective knowledge stream for a divine agent."""
        aliases = {"nature": "god_nature", "death": "god_death", "trade": "god_trade"}
        entity_id = aliases.get(entity, entity)
        return tuple(item for item in self._knowledge[entity_id] if item.knowledge_id > knowledge_id)

    def reports_since(self, entity: str, report_id: int = 0) -> tuple[DivineReport, ...]:
        """Chronological active-attention reports for a divine agent."""
        return tuple(report for report in self.inbox(entity).all_reports if report.report_id > report_id)

    def process_event(self, event: WorldEvent) -> None:
        if event.event_id in self._processed_event_ids:
            return
        self._processed_event_ids.add(event.event_id)

        entry = self.archive.add_event(self.world, event)
        for profile in self.profiles.values():
            self._route_event(event, entry, profile)
        self._update_trends(event)

    def _route_event(self, event: WorldEvent, entry: ArchiveEntry, profile: ObserverProfile) -> None:
        # A deity already knows what it deliberately did. Do not route its own
        # manifestations back through Heralds and accidentally create a loop.
        if event.data.get("source_entity_id") == profile.entity_id:
            return
        relevance, owned_target, direct_address = self._relevance(event, profile)
        magnitude = self._magnitude(event)
        observability = self._mundane_observability(event)
        presence = self.presence.snapshot_for_event(profile.entity_id, event)
        contextual_salience = self.presence.contextual_salience(profile.entity_id, event)
        personal_attention = self.attention.strength_for_event(profile.entity_id, event)
        salience = self._event_salience(
            event,
            profile,
            relevance=relevance,
            magnitude=magnitude,
            contextual_salience=contextual_salience,
            owned_target=owned_target,
            direct_address=direct_address,
        )
        perceptual_penetration = self._perceptual_penetration(
            presence,
            relevance=relevance,
            personal_attention=personal_attention,
            direct_address=direct_address,
        )
        if self._event_opposed(event, profile.entity_id, perceptual_penetration):
            return
        perception = self._perception_score(
            presence.total,
            salience,
            observability,
            personal_attention,
        )
        binding = owned_target or direct_address

        # Very diffuse consciousness can miss a truly mundane event entirely.
        if perception < 0.45 and not binding:
            return

        consciousness_budget = self.presence.profiles[profile.entity_id].consciousness_budget
        focus_ratio = _clamp(presence.focus / consciousness_budget) if consciousness_budget else 0.0
        score = _clamp(
            perception
            * (
                0.60 * salience
                + 0.18 * contextual_salience
                + 0.22 * focus_ratio
                + 0.20 * personal_attention
                + (0.15 if binding else 0.0)
            )
        )

        # Ordinary prayers enter peripheral awareness and are aggregated unless
        # the deity is unusually concentrated there or the calendar makes the
        # moment itself significant.
        if event.event_type == "PRAYER_OFFERED" and presence.total < 0.75 and contextual_salience < 0.50:
            priority = ReportPriority.ARCHIVE_ONLY
            reason = "individual prayer retained for aggregation"
        else:
            if score >= 0.68:
                priority = ReportPriority.IMMEDIATE
            elif score >= 0.25:
                priority = ReportPriority.DIGEST
            else:
                priority = ReportPriority.ARCHIVE_ONLY
            reason = self._reason(
                event,
                profile,
                owned_target,
                direct_address,
                presence,
                contextual_salience,
                personal_attention,
            )

        known_actor_ids = self._known_actor_ids(
            event,
            direct_address,
            presence,
            profile.entity_id,
            relevance,
            personal_attention,
        )
        veiled_subject_refs = self._veiled_subject_refs(event, known_actor_ids)
        response_to_probe_ref = self._response_to_probe_ref(
            event,
            profile.entity_id,
            known_actor_ids,
            perceptual_penetration,
        )
        perceived_summary = describe_event(self.world, event, perceived_actor_ids=known_actor_ids)
        self.decisions.append(
            RoutingDecision(
                event_id=event.event_id,
                entity_id=profile.entity_id,
                priority=priority,
                relevance=relevance,
                observability=observability,
                magnitude=magnitude,
                presence=presence.total,
                contextual_salience=contextual_salience,
                perception_score=perception,
                focus=presence.focus,
                personal_attention=personal_attention,
                attention_score=score,
                actor_identity_known=bool(known_actor_ids),
                reason=reason,
            )
        )
        self._remember(
            entity_id=profile.entity_id,
            entry=entry,
            event_type=event.event_type,
            source_event_ids=(event.event_id,),
            tags=event.tags,
            location_id=event.location_id,
            known_actor_ids=known_actor_ids,
            confidence=perception,
            summary=perceived_summary,
            veiled_subject_refs=veiled_subject_refs,
            response_to_probe_ref=response_to_probe_ref,
        )

        if priority is ReportPriority.ARCHIVE_ONLY:
            return

        report = self._make_report(
            entity_id=profile.entity_id,
            priority=priority,
            entry=entry,
            game_minute=event.game_minute,
            source_event_ids=(event.event_id,),
            known_actor_ids=known_actor_ids,
            attention_score=score,
            reason=reason,
            summary=perceived_summary,
        )
        self.inboxes[profile.entity_id].enqueue(report)

    def _remember(
        self,
        *,
        entity_id: str,
        entry: ArchiveEntry,
        event_type: str,
        source_event_ids: tuple[int, ...],
        tags: tuple[str, ...],
        location_id: str,
        known_actor_ids: tuple[str, ...],
        confidence: float,
        summary: str,
        veiled_subject_refs: tuple[str, ...] = (),
        response_to_probe_ref: str | None = None,
    ) -> DivineKnowledge:
        self._knowledge_sequence += 1
        knowledge = DivineKnowledge(
            knowledge_id=self._knowledge_sequence,
            entity_id=entity_id,
            archive_entry_id=entry.archive_id,
            game_minute=entry.game_minute,
            event_type=event_type,
            source_event_ids=source_event_ids,
            tags=tags,
            location_id=location_id,
            known_actor_ids=known_actor_ids,
            confidence=_clamp(confidence),
            summary=summary,
            veiled_subject_refs=veiled_subject_refs,
            response_to_probe_ref=response_to_probe_ref,
        )
        self._knowledge[entity_id].append(knowledge)
        return knowledge

    def _relevance(self, event: WorldEvent, profile: ObserverProfile) -> tuple[float, bool, bool]:
        relevance = max((profile.domain_weights.get(tag, 0.0) for tag in event.tags), default=0.0)
        owned_target = False
        if event.event_type in OWNERSHIP_SENSITIVE_EVENTS:
            for target_id in event.target_ids:
                obj = self.world.objects.get(target_id)
                if obj and obj.owner_id == profile.entity_id:
                    owned_target = True
                    relevance = 1.0

        deity_alias = {
            "nature": "god_nature",
            "death": "god_death",
            "trade": "god_trade",
        }
        direct_address = (
            event.event_type == "PRAYER_OFFERED"
            and deity_alias.get(str(event.data.get("deity"))) == profile.entity_id
        )
        if (
            event.event_type == "DIEGETIC_SPEECH"
            and event.data.get("response_to_entity_id") == profile.entity_id
        ):
            direct_address = True
        if direct_address:
            relevance = 1.0
        return relevance, owned_target, direct_address

    def _magnitude(self, event: WorldEvent) -> float:
        magnitude = EVENT_MAGNITUDE.get(event.event_type, 0.05)
        importance = event.data.get("importance")
        if isinstance(importance, (int, float)):
            magnitude = max(magnitude, float(importance))
        return _clamp(magnitude)

    def _mundane_observability(self, event: WorldEvent) -> float:
        witnesses = min(1.0, len(event.witness_ids) * 0.12)
        return _clamp(max(event.publicity, witnesses))

    def _event_salience(
        self,
        event: WorldEvent,
        profile: ObserverProfile,
        *,
        relevance: float,
        magnitude: float,
        contextual_salience: float,
        owned_target: bool,
        direct_address: bool,
    ) -> float:
        domain_resonance = relevance
        if set(event.tags) & profile.sensory_tags:
            domain_resonance = max(domain_resonance, profile.sensory_strength)
        magnitude_component = magnitude * (0.20 + 0.80 * relevance)
        domain_component = 0.38 * domain_resonance
        binding_component = 0.95 if owned_target else 0.0
        address_component = 0.70 if direct_address else 0.0
        return _clamp(
            max(
                magnitude_component,
                domain_component,
                contextual_salience,
                binding_component,
                address_component,
            )
        )

    def _perception_score(
        self,
        presence: float,
        salience: float,
        observability: float,
        personal_attention: float,
    ) -> float:
        # A personal thread is an additional weak sensing path. It amplifies a
        # mortal's "signature" but does not reveal their location by itself.
        thread_signal = 0.65 * personal_attention
        return _clamp(
            1.0
            - (1.0 - presence)
            * (1.0 - salience)
            * (1.0 - 0.35 * observability)
            * (1.0 - thread_signal)
        )

    def _known_actor_ids(
        self,
        event: WorldEvent,
        direct_address: bool,
        presence: PresenceSnapshot,
        entity_id: str,
        relevance: float,
        personal_attention: float,
    ) -> tuple[str, ...]:
        if direct_address:
            candidates = event.actor_ids
        # High concentration may pierce *mundane* secrecy. It is deliberately
        # only a candidate-discovery path; perceptual opposition below remains
        # an independent gate and therefore Presence is not omniscience.
        elif presence.total >= 0.85:
            candidates = event.actor_ids
        elif event.publicity >= 0.55 and event.secrecy <= 0.70:
            candidates = event.actor_ids
        elif event.witness_ids and event.secrecy <= 0.45:
            candidates = event.actor_ids
        else:
            # A thread identifies only the already-known signature it belongs
            # to. It must never reveal unknown companions in the same event.
            candidates = tuple(
                actor_id
                for actor_id in event.actor_ids
                if self.attention.strength_for_actor(entity_id, actor_id) >= 0.20
            )

        penetration = self._perceptual_penetration(
            presence,
            relevance=relevance,
            personal_attention=personal_attention,
            direct_address=direct_address,
        )
        return tuple(
            actor_id
            for actor_id in candidates
            if not opposition_blocks(
                event.perceptual_barriers,
                entity_id,
                PerceptualAspect.IDENTITY,
                penetration,
                actor_id=actor_id,
            )
        )

    def _perceptual_penetration(
        self,
        presence: PresenceSnapshot,
        *,
        relevance: float,
        personal_attention: float,
        direct_address: bool,
    ) -> float:
        """Prototype composite for opposing non-mundane perceptual barriers.

        The coefficients are experimental, not metaphysical constants.  The
        important invariant is structural: Presence contributes, but cannot
        act as a universal override by itself.
        """
        budget = self.presence.profiles[presence.entity_id].consciousness_budget
        focus_ratio = _clamp(presence.focus / budget) if budget else 0.0
        return _clamp(
            0.50 * presence.total
            + 0.20 * focus_ratio
            + 0.15 * relevance
            + 0.10 * personal_attention
            + (0.05 if direct_address else 0.0)
        )

    @staticmethod
    def _event_opposed(event: WorldEvent, entity_id: str, penetration: float) -> bool:
        if opposition_blocks(
            event.perceptual_barriers,
            entity_id,
            PerceptualAspect.EVENT,
            penetration,
        ):
            return True
        return any(
            opposition_blocks(
                event.perceptual_barriers,
                entity_id,
                PerceptualAspect.EVENT,
                penetration,
                actor_id=actor_id,
            )
            for actor_id in event.actor_ids
        )

    @staticmethod
    def _response_to_probe_ref(
        event: WorldEvent,
        entity_id: str,
        known_actor_ids: tuple[str, ...],
        penetration: float,
    ) -> str | None:
        probe_ref = event.data.get("response_to_probe_ref")
        if not isinstance(probe_ref, str):
            return None
        if event.data.get("response_to_entity_id") != entity_id:
            return None
        # A causal link to a known personal probe would itself identify the
        # responder. Suppress it whenever identity did not survive perception.
        if not known_actor_ids:
            return None
        if opposition_blocks(
            event.perceptual_barriers,
            entity_id,
            PerceptualAspect.CAUSAL_LINK,
            penetration,
        ):
            return None
        if any(
            opposition_blocks(
                event.perceptual_barriers,
                entity_id,
                PerceptualAspect.CAUSAL_LINK,
                penetration,
                actor_id=actor_id,
            )
            for actor_id in event.actor_ids
        ):
            return None
        return probe_ref

    @staticmethod
    def _veiled_subject_refs(
        event: WorldEvent,
        known_actor_ids: tuple[str, ...],
    ) -> tuple[str, ...]:
        """Mint a safe handle only when perception already implies an unknown actor.

        One opaque handle represents the unresolved agency behind the perceived
        event.  It intentionally encodes neither the objective actor id nor the
        number of hidden participants.  Partially perceived groups do not gain
        extra handles, because doing so would itself reveal hidden information.
        """
        if event.actor_ids and not known_actor_ids:
            return (f"veil:event:{event.event_id}",)
        return ()

    def _reason(
        self,
        event: WorldEvent,
        profile: ObserverProfile,
        owned_target: bool,
        direct_address: bool,
        presence: PresenceSnapshot,
        contextual_salience: float,
        personal_attention: float,
    ) -> str:
        if owned_target:
            return "direct effect on an entity-owned object"
        if direct_address:
            return "direct address"
        if contextual_salience > 0.0:
            observances = ", ".join(presence.active_observances) or "temporal context"
            return f"contextual resonance: {observances}; presence={presence.total:.2f}"
        if personal_attention > 0.0:
            return f"personal attention thread={personal_attention:.2f}; local presence={presence.total:.2f}"
        if presence.focus > 0.0:
            return f"conscious focus; presence={presence.total:.2f}"
        matched = sorted(set(event.tags) & set(profile.domain_weights))
        if matched:
            return f"domain relevance: {', '.join(matched[:4])}; presence={presence.total:.2f}"
        return f"peripheral perception through local presence={presence.total:.2f}"

    def _make_report(
        self,
        *,
        entity_id: str,
        priority: ReportPriority,
        entry: ArchiveEntry,
        game_minute: int,
        source_event_ids: tuple[int, ...],
        known_actor_ids: tuple[str, ...],
        attention_score: float,
        reason: str,
        summary: str,
    ) -> DivineReport:
        self._report_sequence += 1
        return DivineReport(
            report_id=self._report_sequence,
            entity_id=entity_id,
            priority=priority,
            archive_entry_id=entry.archive_id,
            game_minute=game_minute,
            source_event_ids=source_event_ids,
            known_actor_ids=known_actor_ids,
            attention_score=attention_score,
            reason=reason,
            summary=summary,
        )

    def _update_trends(self, event: WorldEvent) -> None:
        rules = {
            "WOOD_HARVESTED": (12, "god_nature", "logging pressure"),
            "FISHED": (25, "god_nature", "fishing pressure"),
            "ITEM_SOLD": (20, "god_trade", "market activity"),
            "NECROMANCY_STUDIED": (8, "god_death", "necromantic interest"),
        }

        if event.event_type == "PRAYER_OFFERED":
            deity_alias = {"nature": "god_nature", "death": "god_death", "trade": "god_trade"}
            recipient = deity_alias.get(str(event.data.get("deity")))
            if recipient:
                self._accumulate_trend(event, 15, recipient, "prayer activity", qualifier=recipient)
            return

        rule = rules.get(event.event_type)
        if rule:
            threshold, recipient, label = rule
            self._accumulate_trend(event, threshold, recipient, label)

    def _accumulate_trend(
        self,
        event: WorldEvent,
        threshold: int,
        recipient: str,
        label: str,
        qualifier: str = "",
    ) -> None:
        day = event.game_minute // (24 * 60) + 1
        key = (day, event.event_type, event.location_id, recipient, qualifier)
        bucket = self._trend_buckets.setdefault(key, [])
        bucket.append(event)
        if len(bucket) % threshold != 0:
            return

        source = tuple(item.event_id for item in bucket[-threshold:])
        region = self.world.regions.get(event.location_id)
        region_name = region.name if region else event.location_id
        summary = f"{threshold} related events indicate {label} in {region_name} during Day {day}."
        entry = self.archive.add_derived(
            game_minute=event.game_minute,
            event_type=f"TREND_{event.event_type}",
            source_event_ids=source,
            location_id=event.location_id,
            tags=("trend", label.replace(" ", "_")),
            summary=summary,
        )
        report = self._make_report(
            entity_id=recipient,
            priority=ReportPriority.DIGEST,
            entry=entry,
            game_minute=event.game_minute,
            source_event_ids=source,
            known_actor_ids=(),
            attention_score=0.50,
            reason=f"aggregated trend: {threshold} × {event.event_type}",
            summary=summary,
        )
        self.inboxes[recipient].enqueue(report)
        self._remember(
            entity_id=recipient,
            entry=entry,
            event_type=entry.event_type,
            source_event_ids=source,
            tags=entry.tags,
            location_id=event.location_id,
            known_actor_ids=(),
            confidence=0.75,
            summary=summary,
        )
