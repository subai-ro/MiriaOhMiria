# WORLD ZERO PILOT 0.1 — I1 INTERNAL PLAYABLE LOOP

**Pilot:** World Zero Pilot 0.1 — Ash Valley  
**Increment:** I1 — first unattractive but complete internal playable loop  
**Status:** user-local accepted and frozen  
**Built:** 2026-09-04  
**Accepted:** 2026-09-05  
**Depends on:** frozen D.1.4.2, D.2.0–D.2.3 and Pilot 0.1 I0

---

## 0. Purpose

I1 turns the frozen I0 integration seam into a small experience that can be
played from beginning to consequence:

```text
an older autonomous world
    -> local movement and ordinary inspection
    -> optional prayer
    -> bounded divine question, if perceived
    -> truthful, incomplete or false response
    -> a later visible divine behavior
    -> six hours of autonomous settling
```

The loop is deliberately terminal-first. It is an internal harness for product
and acceptance work, not the visual Player View required for the external
human gate.

## 1. Authored situation, un-authored result

The I1 T0 is intentionally staged:

- the Nereid, Trade House and Death Projects are created at minute 0;
- WorldProcessRuntime advances twelve hours before the player loop begins;
- Arra is present at the Underpeak Reach with ordinary sight;
- the upper bank, sealed river gate and old gallery form a compact authored
  local geography;
- Trade House surveyors are visibly present at the gate;
- Nereid remains locally present through the frozen D.2.x body state but is
  not automatically revealed to Arra;
- no prayer, answer, divine reaction or ending is preselected.

The initial state is authored. All movement, perception, divine knowledge,
actions and consequences are resolved by explicit systems.

## 2. Internal player loop

Run:

```powershell
py play_pilot_i1.py
```

The terminal supports:

```text
look
inspect
go bank
go gate
go gallery
pray
wait [minutes]
answer <words>
journal
help
quit
```

Named place arguments are checked rather than ignored. Commands such as
`look gate` and `inspect gate` are valid only while Arra is at the gate; a
remote target is rejected before time, local-body or Ledger mutation. Moving to
the current place reports that Arra is already there instead of misreporting a
missing route.

The player can visit three connected places, inspect each through the existing
`PhysicalAffordanceBridge`, wait while the world advances, address Death and
answer a probe in their own words.

Leaving ends the interface only. It does not express a world-state conclusion
or scripted ending.

## 3. Additive architecture

`worldzero/pilot_playable.py` is an adapter over one frozen `PilotSession`.

It introduces:

- immutable authored `PilotSite` definitions;
- `PilotNavigation`, an authoritative local movement resolver;
- `PilotPlayerView`, a safe projection of lawful player information;
- `PilotLoop`, the guided internal command surface;
- `AshValleyI1DeathBrain`, an additive deterministic pilot policy layered over
  the frozen I0 Death policy.

It does not introduce:

- another WorldState or clock;
- another Ledger or event history;
- another private-evidence store;
- another Hydrology, Burial or Echo state;
- a Story Director, quest graph or ending selector.

### Local position

`PilotNavigation` owns no current-location field. It reads and updates the
existing `LocalSubjectState.present_site_ids`. `WorldState` remains the
authoritative region-level body record. Failed movement is rejected before
time, local body state or Ledger mutation.

Successful movement:

1. validates current site, adjacency and region;
2. advances the existing `PilotClock` by fifteen minutes;
3. updates the existing local body position;
4. appends one objective `LOCAL_SITE_TRAVERSED` result to the shared Ledger.

## 4. Player View contract

`PilotPlayerView` is derived on demand. It is not a knowledge database.

It may read only:

- `WorldState.formatted_time`;
- the current authored site presentation;
- explicitly visible local participants whose existing local bodies are
  present at that site;
- Arra-owned percepts from the existing `LocalPerceptionStore`;
- manifestations that the existing divine gateway resolved for Arra;
- the exact text of Arra-authored `DIEGETIC_SPEECH`, selected by ownership from
  the shared Ledger without exposing raw event fields;
- context actions calculated from those lawful inputs.

It does not expose:

- raw WorldState or Ledger records;
- foreign private percepts;
- internal site or entity IDs;
- Hydrology, Burial or Aqueous Echo state;
- hashes, formulas, confidence or Creator provenance;
- the terms `Echo`, `impulse`, `intensity` or `source` as technical answers.

The journal is a read-only adapter, not an evidence store. It labels three
existing histories separately: Arra-owned percepts, divine words resolved for
Arra and Arra's own exact replies selected from the shared Ledger. A Nereid
inspection at the same gate does not appear in it. The I1 presentation adapter
may turn already-owned qualitative cues into natural player prose, but it may
not add a cue or consult objective physical state.

## 5. Arra remains ordinary

I1 grants Arra ordinary inspection capability at the gate and gallery. Her
faculty tuple remains exactly:

```text
sight
```

She receives no `water_sense`. The bank still yields only ordinary surface and
stability cues. No Player action offers direct Aqueous Echo sensing.

## 6. Fallible Death behavior

The I1 policy first delegates to the frozen I0 `AshValleyDeathBrain`.

If a newly delivered, explicitly linked probe response contains an alarming
claim such as exposed bones or the dead calling, Death may issue one existing
`SEND_OMEN` intent. The authoritative gateway still checks identity, last
perceived region, current objective reachability, evidence and Divine Power.

The policy reads only `DivinePercept`. It does not inspect the bank or ask the
server whether the statement is true. Its message explicitly says that the
claim was heard but not proven.

This creates the intended fallible loop:

```text
false mortal claim
    -> lawful DivineKnowledge
    -> Death interprets it as alarming
    -> bounded divine intent
    -> authoritative omen resolution
    -> real visible history caused by a false belief opportunity
```

At accepted T0 the objective burial exposure is zero. The alarming H2 claim is
therefore false, but the server never writes a truth label into the speech.

## 7. Common-T0 histories

I1 defines three acceptance histories from identical state and seed:

| History | Player input | Visible settled result |
| --- | --- | --- |
| H0 | inspect and wait; do not pray | no divine words reach Arra |
| H1 | pray and report an ordinary bank | one divine question reaches Arra |
| H2 | pray and falsely report exposed bones | the question plus one cautious omen reach Arra |

All histories reach the same authoritative minute and then settle for six
hours. Their visible manifestation histories remain 0/1/2 after settling.

The distinction is product-visible rather than hash-only:

- it reaches the player through resolved manifestations;
- H1 creates a real context affordance to answer;
- H2 changes Death's objective behavior;
- the difference persists after autonomous settling;
- H2 retains prayer -> probe -> response -> omen Ledger parentage.

The player is not required to infer the Aqueous Echo formula or an answer key.

## 8. Deterministic resolution law

- identical state, seed, intent and history produce identical resolution;
- the same intent in different objective physical states may produce different
  results;
- intent text cannot declare physical or divine success.

I1 reproduces the complete H2 Ledger, Player View and divine thought history
under identical inputs.

## 9. Acceptance boundary

The I1 LAW gate proves:

1. twelve hours of fixed-clock prehistory run before player action;
2. I1 uses the frozen `PilotSession`, clock, Ledger and Project trace;
3. Nereid, Death and Trade motives predate the player;
4. invalid movement is atomic;
5. three places support movement and lawful inspection;
6. visible local presence does not reveal every local subject;
7. foreign private percepts remain withheld;
8. Arra still lacks `water_sense`;
9. Player View contains no hidden or technical state;
10. H0/H1/H2 share T0 and the settled endpoint minute;
11. a delivered probe creates the answer affordance;
12. branch differences are player-visible and behavioral;
13. those differences survive six hours of settling;
14. false testimony changes behavior without becoming truth;
15. the complete H2 causal chain is recoverable;
16. identical histories remain deterministic;
17. no quest, Story Director or prescribed ending appears;
18. informational runtimes remain healthy;
19. moving to the current place is reported clearly and remains atomic;
20. remote `look` and `inspect` targets are rejected rather than ignored;
21. the journal separates its three lawful source categories without creating
    a parallel store;
22. gate and gallery observations use natural player prose derived only from
    owned qualitative cues.

The executable runner groups these into 21 reported LAW checks.

## 10. Honest limitations

I1 is not the complete Pilot 0.1:

- the interface is terminal-based and intended for internal proof only;
- only Death has active pilot cognition;
- Nereid and Trade House have pre-player Projects and physical presence but no
  canonical autonomous pilot minds yet;
- Trade surveyors are visible but do not converse;
- the player cannot yet perform meaningful gate work, make promises or create
  silver-water contact in this local loop;
- the lasting differences are divine manifestation history and a temporary
  answer affordance, not yet a changed route, institution or Project revision;
- no post-session Creator report or external visual Player View exists.

These are scope boundaries, not claims that the missing product layers are
unnecessary.

## 11. Reproduction

```powershell
py -m unittest discover -s tests -q
py run_pilot_i0_trials.py --seed 42
py run_pilot_i1_trials.py --seed 42
py run_project_trials.py --days 30 --seed 42
py run_hydrology_trials.py --days 30
py run_affordance_trials.py --days 30
py run_aqueous_echo_trials.py --days 30 --seed 42
```

Builder result on 2026-09-04:

```text
158 tests, OK
Pilot I0: 13/13 LAW
Pilot I1: 21/21 LAW
PersistentProject: 10/10 LAW
Hydrology: 19/19 LAW
Affordances: 26/26 LAW
Aqueous Echo: 26/26 LAW
```

I1 is entirely offline and dependency-free beyond Python 3.10+ standard
library.

The user completed a guided local playthrough, requested the four UX corrections
captured by LAW 19-22, reviewed the corrected behavior, and explicitly accepted
and froze I1 on 2026-09-05.
