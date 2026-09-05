# WORLD ZERO PILOT 0.1 — I0 DEATH GOD INTEGRATION

**Pilot:** World Zero Pilot 0.1 — Ash Valley  
**Increment:** I0 integration spike  
**Status:** user-local accepted and frozen  
**Built:** 2026-09-04  
**Acceptance date:** 2026-09-04  
**Depends on:** frozen D.1.4.2 Epistemic Kernel and frozen D.2.0–D.2.3

---

## 0. Purpose

I0 answers one narrow risk before the playable pilot grows:

> Can the real D.1.4.2 God of Death participate in the D.2.x physical world
> through lawful subjective evidence and an existing bounded divine action,
> without receiving the Hydrology, Burial or Aqueous Echo answer key?

The accepted result is yes. I0 is not yet the playable Pilot 0.1 and does not
promote or alter any earlier frozen checkpoint.

## 1. Authored T0

The spike uses a deliberately authored initial situation:

- Arra starts in the Underpeak region at the visible upper-reach bank;
- the frozen Nereid and Trade House Projects already exist;
- the God of Death has an independent Project concerned with truthful memory,
  attribution and the boundary of the dead;
- the bank is objectively ordinary at the surface at T0;
- the hidden burial shelf and Hydrology state remain server-side;
- no outcome, contact, divine response or ending is preselected.

Authored setup is allowed. Scripted resolution is not.

## 2. Participants in the I0 composition

| Participant | Pre-player motive/state | Lawful input in I0 | Available action |
| --- | --- | --- | --- |
| Arra | present at the visible bank with a silver rod in inventory | ordinary local sight and actions | inspect the bank, pray, speak |
| Nereid | persistent desire to regain native water connectivity | existing Project state; no new cognition in I0 | unchanged D.2.x affordances |
| Trade House | persistent desire to establish a viable route | existing Project state; no new cognition in I0 | unchanged D.2.x affordances |
| God of Death | preserve truthful remembrance and attribution around death boundaries | only Herald-delivered `DivineKnowledge` | one existing `SEND_PROBE` inquiry |

The Last Gate cult is not an active pilot participant in I0. The frozen world
may still contain its pre-existing temple and regional metric; neither replaces
the God of Death or drives this spike.

## 3. Additive integration map

```text
authored T0
    -> existing WorldState
    -> existing Hydrology + Aqueous Echo in WorldProcessRuntime

ordinary Arra bank inspection
    -> existing PhysicalAffordanceBridge
    -> existing LocalPerceptionStore
    -> private SubjectivePercept owned by Arra
    -/-> Herald knowledge for Death

Arra prayer to Death
    -> existing WorldEngine
    -> one objective Ledger event
    -> existing HeraldSystem / Epistemic Kernel
    -> bounded DivineKnowledge, if perception is not opposed
    -> existing DivineAgent with pilot Death policy
    -> existing DivineActionGateway
    -> existing SEND_PROBE resolution

Arra response
    -> existing WorldEngine speech action
    -> Ledger causal parent = probe manifestation
    -> existing HeraldSystem
    -> fallible mortal claim in DivineKnowledge
```

No new Ledger, world engine, subjective evidence store, physical truth or
divine resolver is introduced.

## 4. Time architecture

`PilotClock` is an orchestration facade, not another clock. It owns no minute
counter. Its `game_minute` property delegates to `WorldState.game_minute`.

One call performs:

```text
WorldState.advance(minutes)
    -> existing WorldProcessRuntime fixed-boundary ticks
    -> existing ProjectRuntime review at resulting authoritative minute
    -> existing DivineRuntime wake check at resulting authoritative minute
```

D.2.2 and D.2.3 bridges now accept an optional `advance_time` callback. Their
default remains `world.advance`, preserving frozen behavior. Only
`PilotSession` supplies `PilotClock.advance`.

Authoritative physics exceptions still propagate. A divine cognition failure
is recorded by the facade and cannot roll back or corrupt already resolved
world time.

### Integration finding

The spike found one concrete seam mismatch. Physical action durations in
`worldzero/affordances.py` and Echo sensing durations in
`worldzero/processes/aqueous_echo.py` advanced `WorldState` directly, while
`run_world.py` scheduled `ProjectRuntime` and `DivineRuntime` only as
`Simulation` tick listeners. Physics therefore advanced correctly, but a long
physical action alone could not wake Projects or Gods.

This was not a disproportionate blocker. The optional callback above resolves
it additively without changing default D.2.x behavior, creating a second clock
or moving authority into `PilotSession`. No fallback or removal of the God was
required.

## 5. Divine epistemic boundary

The I0 Death policy extends `DeathGodPrototypeBrain`. It never receives
`WorldState`, `HydrologyState`, `BurialBankState`, `AqueousEchoState`, Ledger
data or Arra's private local percept.

The only new policy branch requires a newly delivered `PRAYER_OFFERED`
`DivineKnowledge` item that:

- is tagged for Death;
- names an actor through lawful perception;
- carries Underpeak only as the perceived event location.

This justifies a question, not a conclusion. The probe's sole causal evidence
is the prayer event. Its text asks what Arra witnessed and why Arra called. It
does not mention the burial shelf, Hydrology, Echo, exposure or an answer.

The God can fail or be wrong:

- a sufficient event veil makes it miss the prayer entirely;
- stale objective position can still make the gateway reject a targeted act;
- Arra can answer with an incomplete, mistaken or false statement;
- the subjective channel supplies no automatic correction from objective
  state.

## 6. Arra perception boundary

Arra is registered with exactly the ordinary `sight` faculty. She has no
`water_sense` and cannot call the Echo sensing bridge successfully.

Bank inspection yields only:

```text
visible_stability
surface_signs
```

The Player-facing payload contains none of the terms `Echo`, `impulse`,
`intensity` or `source`. A rejected Echo sense attempt is atomic: no time,
state, Ledger or private-percept mutation.

## 7. Deterministic resolution law

The governing law is:

- identical state, seed, intent and history produce identical resolution;
- the same intent in different objective physical states may produce different
  results;
- intent text cannot declare physical success.

I0 proves the first clause for the complete bank-inspection, prayer, probe and
response history. Existing D.2.x counterfactuals continue to prove the second
and third clauses.

## 8. I0 acceptance contract

The I0 LAW gate must prove:

1. `PilotSession` reuses one `WorldState` across all existing runtimes.
2. All objective events use one `EventLedger`.
3. Physical and Echo observation paths share the existing
   `LocalPerceptionStore`.
4. `CausalTrace` wraps the same Ledger rather than becoming a second history.
5. the participant is the real `god_death` agent and existing gateway;
6. the Death Project contains motive but no objective Burial/Hydrology fact;
7. Arra has no `water_sense`;
8. Arra receives only ordinary bank cues;
9. private bank inspection does not become divine knowledge;
10. one perceived prayer can justify exactly one bounded probe;
11. probe evidence and parentage cite only the perceived prayer;
12. the God receives no objective Burial, Hydrology, Echo, hash or formula;
13. event opposition can make the God miss the prayer;
14. mortal response remains testimony rather than verified truth;
15. prayer -> probe -> response is forensically recoverable;
16. identical state, seed, intent and history are deterministic;
17. clock, Project and Ledger informational runtimes remain healthy.

The executable runner groups these into 13 reported LAW checks.

## 9. Non-claims and hard boundary

I0 does not implement:

- a full playable loop or external Player View;
- canonical model-backed Nereid cognition;
- autonomous Trade House cognition;
- a cult, Messenger or divine avatar;
- a general Domain Field runtime;
- an objective divine remote-action system beyond frozen D.1.4.2 actions;
- scripted story beats, endings or a Story Director;
- an explanation of the Aqueous Echo formula to Arra or Death.

The direct prayer event currently carries no mortal-authored prayer text. That
is an intentionally accepted I0 limit: Death learns that Arra addressed it and
where, then asks rather than inferring the reason. Richer prayer expression is
future product work, not permission to leak objective state.

## 10. Reproduction

```powershell
py -m unittest discover -s tests -q
py run_pilot_i0_trials.py --seed 42
py run_project_trials.py --days 30 --seed 42
py run_hydrology_trials.py --days 30
py run_affordance_trials.py --days 30
py run_aqueous_echo_trials.py --days 30 --seed 42
```

Builder result on 2026-09-04:

```text
146 tests, OK
Pilot I0: 13/13 LAW
PersistentProject: 10/10 LAW
Hydrology: 19/19 LAW
Affordances: 26/26 LAW
Aqueous Echo: 26/26 LAW
```

No neural provider, API key, network service or package installation is
required.
