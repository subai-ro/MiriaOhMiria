from __future__ import annotations

from .project_runtime import IntentResolution, ProjectIntent
from .projects import AttemptOutcome, PersistentProject
from .processes.hydrology import HydrologyProcess


class AquaticPassageResolver:
    """Project adapter over one authoritative hydrology affordance.

    The resolver returns whether the attempted route is physically usable. It
    deliberately does not expose node levels, gate coefficients, burial state,
    or the rest of HydrologyState to the Project owner.
    """

    rule_id = "hydrology.aquatic_passage.v1"

    def __init__(self, hydrology: HydrologyProcess) -> None:
        self.hydrology = hydrology

    def resolve(
        self,
        *,
        project: PersistentProject,
        intent: ProjectIntent,
        game_minute: int,
    ) -> IntentResolution:
        if intent.target_refs != ("water:underpeak_deep_river",):
            return IntentResolution(
                ok=False,
                outcome=AttemptOutcome.BLOCKED,
                message="aquatic passage resolver requires the known target water",
            )

        viable = self.hydrology.state.aquatic_route_viable
        event = self.hydrology.ledger.append(
            game_minute=game_minute,
            event_type="AQUATIC_PASSAGE_ATTEMPTED",
            actor_ids=(project.owner_id,),
            target_ids=("underpeak_deep_river",),
            location_id="northwood",
            tags=("project_attempt", "movement", "water"),
            witness_ids=(),
            publicity=0.0,
            secrecy=1.0,
            data={
                "project_ref": project.ref,
                "route_viable": viable,
            },
        )
        return IntentResolution(
            ok=viable,
            outcome=AttemptOutcome.SUCCEEDED if viable else AttemptOutcome.BLOCKED,
            message=(
                "the attempted water route carried the traveller into the target waters"
                if viable
                else "the attempted water route did not provide continuous passage"
            ),
            result_event_ids=(event.event_id,),
        )
