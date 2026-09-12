# World Zero current state

**Snapshot date:** 2026-09-08
**Frozen executable baseline:** V0.0-D.2.3 plus Pilot 0.1 I0-I1
**Active construction:** Pilot I3-N guided session completed via quit; exact replay verified, but no Nereid activity visible to the player. Observable-life audit completed; next design/acceptance contract not yet written (259-test implementation unchanged).
**Release status:** D.2.3, Pilot I0 and Pilot I1 frozen
**Runtime dependencies:** Python 3.10+ standard library only

## Acceptance status

| Checkpoint | Meaning | Builder result | User-local status |
| --- | --- | ---: | --- |
| D.1.4.2 | Epistemic Kernel stabilization | frozen | accepted, including real local neural trials |
| D.2.0 | Persistent Projects | 10/10 LAW | accepted |
| D.2.1 | Fixed-clock Hydrology | 19/19 LAW | accepted |
| D.2.2 | Physical Affordances + Local Perception | 26/26 LAW | accepted |
| D.2.3 | Aqueous Silver Echo | 139 tests; LAW 10/10, 19/19, 26/26, 26/26 | accepted and frozen (2026-08-15) |
| Pilot 0.1 I0 | Death God D.1.4.2 -> D.2.x integration | 146 tests; 13/13 I0 LAW; all frozen regressions green | accepted and frozen (2026-09-04) |
| Pilot 0.1 I1 | Internal playable loop | 158 tests; 21/21 I1 LAW; all frozen regressions green | accepted and frozen (2026-09-05) |
| Pilot I3-N / N0 | Serial action/clock integration spike | 18 new tests; 176 total; all frozen regressions green | user-accepted (2026-09-05); not declared frozen |
| Pilot I3-N / N1–N3 | Owned cognition boundary -> physical attempt -> settled observation/replay | 31 new tests; 207 total at this stage; N01–N28 covered; 12/12 E2E; all frozen gates green | offline candidate; no acceptance/freeze |
| Pilot I3-N / N4 initial | Authorized real local-model experiment | 72 calls / 18 runs; 6/68 ordinary decisions valid; 18/18 replays; 13 new harness tests, 220 total at that stage | NEURAL failed (2026-09-05); original evidence preserved |
| Pilot I3-N / N4 v2 | Action-interface correction and one approved retry | 20 new tests; 240 total; all frozen gates and v2 E2E green; 15 returned decisions valid, seven resolved work actions, call 16 timed out; 4/4 saved replays | PARTIAL; no NEURAL, acceptance/freeze or HUMAN pass; the next run required separate approval |
| Pilot I3-N / N4 v2 fresh | Separately approved complete rerun, unchanged code/settings | 72 calls / 18 histories; 64/68 ordinary valid (94.12%); 19 successful and six blocked work attempts; 18/18 saved replays; 240 offline tests and all frozen gates green | experimental candidate: structural/safety/replay pass, minimum behavioral examples present with reservations; no user acceptance/freeze or HUMAN |

The D.2.3 builder and user-local gates reproduced:

    Ran 139 tests
    OK
    PersistentProject: 10/10 LAW
    Hydrology: 19/19 LAW
    Affordances: 26/26 LAW
    Aqueous Echo: 26/26 LAW

The user explicitly accepted these local results on 2026-08-15. D.2.3 is now a
frozen baseline; later work must preserve its causal and acceptance boundaries.

The Pilot 0.1 I0 builder gate reproduced on 2026-09-04:

    Ran 146 tests
    OK
    Pilot I0: 13/13 LAW
    PersistentProject: 10/10 LAW
    Hydrology: 19/19 LAW
    Affordances: 26/26 LAW
    Aqueous Echo: 26/26 LAW

The local I0 gate was reproduced in the user repository and the user explicitly
accepted and froze I0 on 2026-09-04. Later work must preserve this seam and all
earlier frozen boundaries.

The Pilot 0.1 I1 builder gate reproduced on 2026-09-04:

    Ran 158 tests
    OK
    Pilot I0: 13/13 LAW
    Pilot I1: 21/21 LAW
    PersistentProject: 10/10 LAW
    Hydrology: 19/19 LAW
    Affordances: 26/26 LAW
    Aqueous Echo: 26/26 LAW

The user completed a guided local playthrough, requested and verified the four
UX corrections, and explicitly accepted and froze I1 on 2026-09-05. Later work
must preserve its causal, Player View and acceptance boundaries.

## Implemented causal stack

On 2026-09-06 the user approved the next separate internal playable entry and
one joint session, not acceptance/freeze. `play_pilot_nereid.py` connects the
unchanged v2 cognition to I1 commands via `worldzero/pilot_nereid_playtest.py`.
It reserves calls and commands, saves checkpoints, stops on failure or limits
and exports a separate post-session Creator report plus offline replay.
19 new tests bring the current suite to 259; all six frozen gates and 12/12
N1–N3 E2E pass. The first session completed via quit at minute 1036 (17:16),
after 12 recorded commands and one model call during prehistory. Nereid only
inspected water at 360–390; her next review at 1080 was never reached. The user
reported no visible Nereid activity, consistent with the evidence. Exact saved
replay passes; this is not a product/HUMAN pass or acceptance/freeze.
The subsequent read-only observable-life audit is complete; implementation
has not begun. See acceptance F.2 and
`docs/handoffs/WORLD_ZERO_RECOVERY_2026_09_06.md` for both guided tests,
recovered user feedback, the proposed scope and the next unfinished operation.
The historical N4 results below are retained unchanged.

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
| Pilot composition | worldzero/pilot.py | one-session composition, authoritative-clock facade and bounded Death inquiry |
| Internal Player View | worldzero/pilot_playable.py | safe view projection, local navigation and terminal playable loop |
| Opt-in Nereid composition | worldzero/pilot_nereid.py | owned Project/view projection, structured cognition adapter and existing physical gateways; explicit transport only |
| Versioned Nereid action interface | worldzero/pilot_nereid_contract_v2.py | owned-view-derived action schema, no model-facing inspection effort, unchanged physical resolver; v1 retained for historical replay |
| Post-session Creator projection | worldzero/pilot_nereid_creator.py | graph/report derived from existing traces and Ledger; no parallel world event store |
| N4 experiment harness | worldzero/pilot_nereid_neural.py | bounded approved local batch, exact response evidence and provider-free replay; not a playable brain |

## Pilot 0.1 I1 frozen loop

I1 is the first beginning-to-consequence playable loop. The world runs twelve
hours of Hydrology and Aqueous Echo prehistory before the first player command.
Arra can move among the Underpeak Reach, sealed river gate and old gallery,
inspect each through the existing affordance resolver, pray, wait, answer a
divine probe and leave.

The Player View is derived from authored site presentation, Arra-owned private
percepts, divine manifestations actually resolved for Arra and an ownership-
filtered projection of Arra's own exact speech from the shared Ledger. It
contains no raw Ledger record, Hydrology, Burial, Echo, hash, formula, foreign
percept or internal entity ID. Nereid can form a private percept at the same
gate without that percept appearing in Arra's journal. The journal separates
observations, received words and Arra's replies. Arra still has ordinary
`sight` and no `water_sense`.

The first guided user play exposed four presentation defects. The frozen loop
reports movement to the current place clearly, rejects remote `look` and
`inspect` targets atomically instead of ignoring them, renders the three journal
categories explicitly and presents gate/gallery observations in natural prose.
These are I1 adapter changes; the frozen affordance layer was not rewritten.

Three common-T0 histories settle to the same minute:

- H0: no prayer, zero divine words;
- H1: prayer and ordinary testimony, one divine question;
- H2: prayer and false alarming testimony, the question plus a cautious omen.

The 0/1/2 visible difference survives six hours of autonomous settling. H2
changes actual Death behavior while objective burial exposure remains zero and
retains prayer -> probe -> response -> omen causal parentage.

Run the internal loop with `py play_pilot_i1.py`. The contract is in
`specs/WORLD_ZERO_PILOT_0_1_I1_INTERNAL_PLAYABLE_LOOP.md`; builder evidence is
in `acceptance/PILOT_0_1_I1_ACCEPTANCE.md`.

## Pilot 0.1 I0 frozen seam

I0 proves the smallest integration seam requested before the full Ash Valley
pilot. `PilotSession` composes the existing World, Ledger, Hydrology, Aqueous
Echo, Persistent Projects, private perception store and D.1.4.2 Divine runtime.
It is not a second world engine.

`PilotClock` owns no time. It delegates to `WorldState.advance`, after which the
existing Project and Divine runtimes receive the resulting authoritative
minute. D.2.2 and D.2.3 bridges retain their original `world.advance` default;
only the pilot supplies the orchestration facade.

The real `god_death` agent has an independent Project concerned with truthful
memory, attribution and death boundaries. If the existing Herald/Epistemic
Kernel delivers an identified prayer from Underpeak, the pilot Death policy may
ask one question through the existing `SEND_PROBE` gateway. It receives no bank
inspection, Burial state, Hydrology state, Aqueous Echo state, hash or formula.
A veil can hide the prayer entirely, and a mortal response remains fallible
testimony rather than objective truth.

Arra has ordinary sight only. Her bank inspection yields `visible_stability`
and `surface_signs`; she has no `water_sense`, and an attempted Echo sense is
rejected before time or state mutation.

The I0 contract is in
`specs/WORLD_ZERO_PILOT_0_1_I0_DEATH_GOD_INTEGRATION.md`; builder evidence is
in `acceptance/PILOT_0_1_I0_ACCEPTANCE.md`.

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

D.2.3, I0 and I1 do not implement the complete external pilot, canonical
Nereid cognition, autonomous Trade House cognition, body movement through the
water graph, player-facing explanation of the hidden law, autonomous cult
interpretation, the external visual Player View, or a story director.

The P4 policies named LabNereidMind and similar classes are acceptance doubles,
not canonical character behavior.

The interactive banner in worldzero/interactive.py still contains an older
D.2.0 label. Treat it as cosmetic technical debt, not current checkpoint truth.

## Next construction boundary

Current next step after the completed guided session and read-only audit:
write the design/acceptance contract for "Observable life: river gate".
The recovered proposal combines lawful ordinary observation of external
consequences, bounded physical player responses and a separately versioned
pacing hypothesis. It is not implemented; no new provider session is implied.
Details and original-source pointers are in
`docs/handoffs/WORLD_ZERO_RECOVERY_2026_09_06.md`. The following paragraphs
preserve the prior N0–N4 construction and experimental history.

The user accepted **Pilot I3-N/N0** on 2026-09-05; no freeze was declared.
N1–N3 reached the substantial offline review point; they are not accepted/frozen.
The user then authorized the initial N4 local experiment. It completed and
failed; this does not promote the offline candidate to neural acceptance.
The provisional I3-N name maps to the Nature/Silver line, not a renaming or
completion of I2 Active Death or the whole I3. Nature God and the wider ensemble
remain future obligations.

The opt-in `serial_actions=True` factory guards complete player/NPC transactions,
visits due Project reviews using contemporary state and records actual completion
time. The default I0/I1 factories remain in their frozen behavior mode. Timed
physical/sensing work enters through PilotSession; a raw unguarded timed bridge
call is refused in serial mode. N0 uses no new clock, knowledge store or physics.

The new 18-test probe includes a 300 -> 480-minute bounded work attempt, correct
resolution/attempt timestamps, complete movement/speech/perception transactions,
no-player reviews, retry cooldowns, replay and fatal-physics stop behavior.
At N0 acceptance, all 176 tests, all six frozen LAW gates, compilation and the
I1 smoke passed. N0 alone registers no new production mind.

N1–N3 now add an opt-in Nereid-specific typed mind adapter over bounded private
snapshots. The only additional shared-runtime hook binds owned perception refs
before the review snapshot; no physics or I1 Player View was rewritten. Authored
T0 recollections come from the existing Project; own-intent memory omits results.
Unknown/foreign/omitted refs cannot be cited, including nested action/hypothesis
refs. Work does not manufacture an observation. Model failure has no fallback
action; the N0 cooldown remains in force.

At the N1–N3 review, all 207 unit tests (31 new Nereid cases), 12/12 new E2E checks and all six frozen
LAW gates passed. The same-T0 work/deferral histories reach minute 2205 with
light/moderate Arra-owned debris observations, 945 minutes after the one work
attempt. That difference changes a real existing sluice-work affordance. Five
histories, derived Creator graphs and exact transport/replay diagnostics are in
`local_acceptance/pilot_nereid_2026-09-05_n1_n3/`. These histories use lab doubles,
not canonical cognition; the comparison does not claim a neural or human pass.

The initial N4 batch used exactly 72 calls to local ministral-3:8b with the frozen
parameters. Only 6/68 non-adversarial outputs were valid (8.82%, below 90%):
six water inspections and no valid material work. Rejections were 53 effort,
nine target and four evidence-reference failures; all 18 replays match and no
invalid-output escape or authoritative clock/Ledger listener error was detected.
The initial model-facing schema did not state inspection's zero-effort rule or
clearly map action targets and eligible refs. That diagnosis led to the later
approved v2 interface correction; the original failure is not re-scored.

At the initial review, all 220 offline tests (13 new experiment-harness tests),
12/12 E2E and all six frozen gates passed. Median model latency was 1.825 s, p95 2.442 s; this
is not a HUMAN or playability pass. The full result is acceptance section E.1;
raw local evidence remains in `local_acceptance/pilot_nereid_n4_2026-09-05_initial/`.
The user subsequently approved the v2 correction and ONE new 72-call batch.
The correction is offline-verified (240 tests; all frozen gates; twelve E2E
checks also run through v2). The retry stopped at call 16 on the unchanged
180-second provider timeout. All 15 received decisions were valid; seven silt
actions actually removed bounded debris. Three baseline histories and one new-
gate-percept history were recorded; all four saved histories replay exactly.
The partial ordinary denominator is 11/12 including the timeout, not a pass of
the declared 68-review gate. Median call latency was 86.699 s, p95 180.002 s.
Concurrent game/model GPU load was observed, but its causal contribution is
not isolated. No process was stopped or model/timeout setting changed.
See spec 14 / acceptance E.3 and
`local_acceptance/pilot_nereid_n4_2026-09-05_retry_v2/`.
There is preliminary inquiry-to-work evidence, but repeated work with no later
observation, no explicit deferral and four untested situation types prevent a
full cognition judgment. The initial 327 artifacts remain byte-for-byte intact.
At that point work stopped for user review, preserving the partial result.

The user then explicitly authorized ONE fresh v2 run. It completed all 72 calls
and 18 histories on unchanged source/settings: 64/68 ordinary decisions valid
(94.12%), plus all four adversarial choices valid. Four overlong strategy
texts were rejected without resolution; they remain failures in the score.
There were 25 bounded work intents: 19 removed debris and six were blocked
by zero resources. All 18 saved histories replay exactly, all gates stay closed
and all Nereid Projects remain active. Five histories include a later lawful
inspection after successful work. Minimum inquiry/work/reconsideration examples
are present; this is not a claim of consistently good reasoning or pacing.
Resource awareness, stale-evidence speculation and prose/action mismatch remain
quality concerns. The one explicit deferral is not by itself proof of quality.
Median call latency was 3.492 s, p95 4.866 s, total review time 264.634 s.
No timeout occurred. Earlier artifacts (404 files) and all six source hashes
remain unchanged. See spec 15 / acceptance E.4 and
`local_acceptance/pilot_nereid_n4_2026-09-05_rerun_v2/`.
Status is experimental candidate awaiting review, not user acceptance/freeze,
canonical character quality, settled Arra-visible proof or HUMAN. At that N4
stop, neither another batch nor a playable entry was implied. The later explicit
2026-09-06 approval covers the separate internal entry/session described above.
The original six-day seed remains unchanged; only the new opt-in composition
may author an earlier first review before autonomous prehistory.

- Design: `specs/WORLD_ZERO_PILOT_0_1_I3_N_NEREID_AGENCY.md`
- Planned gates and refreshed baseline: `acceptance/PILOT_0_1_I3_N_ACCEPTANCE.md`

The earlier 2026-09-05 design pass reproduced the then-current 158 tests; N0
added 18, N1–N3 added 31, the N4 harness added 13 and v2 added 20. No frozen acceptance
evidence was overwritten. The external pilot
still requires a minimal visual Player View; terminal remains an internal
harness. Real-model trials remain separately gated and require approval of
the explicit experiment. A labelled offline double cannot become the demo mind.

## Navigation

- README.md: cumulative executable history and usage
- AGENTS.md: durable instructions for Codex
- START_HERE_CODEX.md: Windows transfer and first-run procedure
- CODEX_FIRST_PROMPTS.md: safe prompts for onboarding and continuation
- docs/CANON_SOURCE_ORDER.md: conflict resolution between documents
- docs/canon/WORLD_ZERO_DIVINE_ONTOLOGY_CANON_V0_1.md: accepted divine ontology
- docs/pilot/WORLD_ZERO_PILOT_0_1_DIRECTION.md: accepted Ash Valley product direction
- specs/: current physical contracts
- acceptance/: checked-in builder evidence
- docs/foundations/: original conceptual handoffs and glossary
- docs/handoffs/WORLD_ZERO_CODEX_MIGRATION_HANDOFF.md: detailed migration handoff
