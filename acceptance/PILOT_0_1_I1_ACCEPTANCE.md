# World Zero Pilot 0.1 I1 acceptance record

**Increment:** I1 — internal playable loop  
**Built:** 2026-09-04  
**User-local acceptance:** accepted 2026-09-05  
**Status:** frozen

## Builder verification

| Gate | Result |
| --- | --- |
| Complete offline unit suite | 158 tests, OK |
| Frozen Pilot 0.1 I0 integration | 13/13 LAW |
| Frozen Pilot 0.1 I1 internal playable loop | 21/21 LAW |
| Frozen D.2.0 PersistentProject regression | 10/10 LAW |
| Frozen D.2.1 Hydrology regression | 19/19 LAW |
| Frozen D.2.2 Physical Affordances + Local Perception regression | 26/26 LAW |
| Frozen D.2.3 Aqueous Silver Echo regression | 26/26 LAW |

## New proof boundary

I1 proves that:

- twelve hours of authoritative world processes can run before player input;
- one frozen `PilotSession` can support a beginning-to-consequence playable
  loop;
- the player can move among three authored sites and inspect them through the
  existing local affordance bridge;
- navigation validates adjacency and region before time or state mutation;
- movement to the current place reports that state clearly and remains atomic;
- targeted `look` and `inspect` commands reject remote places instead of
  silently discarding their arguments;
- Player View is projected from Arra-owned percepts and resolved
  manifestations rather than exposing raw world or Ledger state;
- the exact text of Arra's own replies is selected from the shared Ledger by
  ownership, not copied into a parallel journal store;
- the journal separates observations, received words and Arra's replies;
- the I1 presentation adapter renders natural gate and gallery prose from
  already-owned qualitative cues without changing the frozen resolver;
- a foreign Nereid percept at the same site remains private;
- Arra retains ordinary sight and receives no `water_sense`;
- H0, H1 and H2 create visible manifestation histories of 0, 1 and 2 messages;
- H1 has a real answer affordance only after the divine probe reaches Arra;
- a false alarming H2 statement changes Death's later behavior while objective
  burial exposure remains zero;
- branch differences survive six hours of autonomous settling;
- H2 retains prayer -> probe -> response -> omen causal parentage;
- identical state, seed, intent and history reproduce identical Ledger,
  Player View and divine thought history;
- no quest, Story Director or prescribed ending enters the world history.

## Reproduction commands

```powershell
py -m unittest discover -s tests -q
py run_pilot_i0_trials.py --seed 42
py run_pilot_i1_trials.py --seed 42
py run_project_trials.py --days 30 --seed 42
py run_hydrology_trials.py --days 30
py run_affordance_trials.py --days 30
py run_aqueous_echo_trials.py --days 30 --seed 42
```

Expected summaries:

```text
Ran 158 tests
OK

LAWS: 13/13
LAWS: 21/21
LAWS: 10/10
LAWS: 19/19
LAWS: 26/26
LAWS: 26/26
```

Interactive smoke test:

```powershell
py play_pilot_i1.py
```

I1 requires no Ollama process, model, API key, network service or package
installation.

## Acceptance decision

The user completed a guided local playthrough. That play exposed four UX
defects: misleading current-place movement feedback, silently ignored remote
targets, an under-structured journal and awkward observation prose. The
correction pass was then reproduced through the 158-test suite, 21/21 I1 LAW,
13/13 frozen I0 LAW and all four frozen D.2.x gates.

The user explicitly accepted and froze I1 on 2026-09-05. Later increments must
preserve this acceptance boundary and remain additive over the frozen
`PilotSession` and Player View contracts.
