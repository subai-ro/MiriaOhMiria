# World Zero current state

**Snapshot date:** 2026-08-15  
**Executable checkpoint:** V0.0-D.2.3, Aqueous Silver Echo  
**Release status:** implemented candidate; user-local D.2.3 acceptance pending  
**Runtime dependencies for D.2.3:** Python 3.10+ standard library only

## Acceptance status

| Checkpoint | Meaning | Builder result | User-local status |
| --- | --- | ---: | --- |
| D.1.4.2 | Epistemic Kernel stabilization | frozen | accepted, including real local neural trials |
| D.2.0 | Persistent Projects | 10/10 LAW | accepted |
| D.2.1 | Fixed-clock Hydrology | 19/19 LAW | accepted |
| D.2.2 | Physical Affordances + Local Perception | 26/26 LAW | accepted |
| D.2.3 | Aqueous Silver Echo | 139 tests and 26/26 LAW; all regressions green | pending |

The D.2.3 builder gate reproduced:

    Ran 139 tests
    OK
    PersistentProject: 10/10 LAW
    Hydrology: 19/19 LAW
    Affordances: 26/26 LAW
    Aqueous Echo: 26/26 LAW

Run verify_d23.ps1 on the recipient machine. Do not update the last column or
freeze D.2.3 until the user confirms all five gates.

## Implemented causal stack

| Layer | Main implementation | Responsibility |
| --- | --- | --- |
| Objective world | worldzero/models.py, engine.py, ledger.py | world state, actions, immutable event history |
| Epistemics | perception.py, presence.py, heralds.py, archive.py | bounded observation, reports, knowledge and Creator history |
| Divine cognition research | divine.py, neural.py, beliefs.py, mysteries.py, impressions.py, attention.py | model-backed God contract behind strict gateways |
| Persistent goals | projects.py, project_runtime.py, provenance.py | desires that survive failure and produce decision-intent-resolution traces |
| World clock | worldzero/processes/runtime.py | deterministic fixed-clock process scheduling |
| Hydrology | worldzero/processes/hydrology.py, hydrology_projects.py | authoritative water state and physical passage resolution |
| Local action/perception | affordances.py | private local inspection and bounded world-facing action |
| Materials | materials.py, engine.py | general item composition and material-medium contact records |
| Hidden metaphysics | worldzero/processes/aqueous_echo.py | silver-water impulse, decay, flow transport, guarded state and local sensing |

## D.2.3 contract

D.2.3 implements one small objective law:

> Silver touching natural water creates a weak transient echo. The echo decays,
> follows sufficiently connected water, and can be sensed only locally by a
> subject with the appropriate faculty.

The input is the general material_medium_contact.v1 record. The process does
not branch on the FISHED verb, actor identity, Nereid, or a count of fishing
actions. Equal physical histories produce equal echo histories.

Hydrology runs first at each six-hour boundary. The echo process then consumes
that same-boundary flow trace, applies continuous decay and contact impulses,
transports a bounded amount, and records explicit boundary and attenuation
losses. Objective band changes are guarded forensic events, not perceptions.

A separate local sensing bridge checks exact presence and faculty. A valid
inspection creates one private qualitative percept. It withholds exact amounts,
formula constants, source location, contact actor, item identity, hashes, and
Creator-only provenance.

The deliberately broken chain remains:

    FISHED
      is not NEREID_INTEREST
      is not CONTACT
      is not REQUEST
      is not QUEST

## Important non-claims

D.2.3 does not implement canonical Nereid cognition, automatic entity interest,
body movement through the water graph, player-facing explanation of the hidden
law, autonomous cult interpretation, or a story director.

The P4 policies named LabNereidMind and similar classes are acceptance doubles,
not canonical character behavior.

The interactive banner in worldzero/interactive.py still contains an older
D.2.0 label. Treat it as cosmetic technical debt, not current checkpoint truth.

## Immediate next action

1. Run the complete D.2.3 gate on the user's machine.
2. If every gate passes, record the user-local acceptance without altering
   behavior.
3. Only then design P5: canonical model-backed Nereid cognition.

P5 must receive only SubjectiveWorldView and owned private percepts. It must not
receive HydrologyState, AqueousEchoState, formulas, exact field values, hidden
contact provenance, or objective route truth. It may ignore, remember,
misinterpret, investigate, or act. Any action must become an intent resolved by
the existing authoritative systems.

## Navigation

- README.md: cumulative executable history and usage
- AGENTS.md: durable instructions for Codex
- START_HERE_CODEX.md: Windows transfer and first-run procedure
- CODEX_FIRST_PROMPTS.md: safe prompts for onboarding and continuation
- docs/CANON_SOURCE_ORDER.md: conflict resolution between documents
- specs/: current physical contracts
- acceptance/: checked-in builder evidence
- docs/foundations/: original conceptual handoffs and glossary
- docs/handoffs/WORLD_ZERO_CODEX_MIGRATION_HANDOFF.md: detailed migration handoff
