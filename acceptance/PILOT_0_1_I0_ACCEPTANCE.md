# World Zero Pilot 0.1 I0 acceptance record

**Increment:** I0 — Death God integration spike  
**Built:** 2026-09-04  
**User-local acceptance:** 2026-09-04  
**Status:** user-local accepted and frozen

## Builder verification

| Gate | Result |
| --- | --- |
| Complete offline unit suite | 146 tests, OK |
| Pilot 0.1 I0 integration | 13/13 LAW |
| Frozen D.2.0 PersistentProject regression | 10/10 LAW |
| Frozen D.2.1 Hydrology regression | 19/19 LAW |
| Frozen D.2.2 Physical Affordances + Local Perception regression | 26/26 LAW |
| Frozen D.2.3 Aqueous Silver Echo regression | 26/26 LAW |

## New proof boundary

The I0 gate proves that:

- `PilotSession` is a composition root over the existing world runtimes;
- `PilotClock` delegates to the authoritative `WorldState` clock;
- the existing fixed-clock physics, Project runtime and Divine runtime can be
  advanced from one pilot orchestration seam;
- one Ledger and the existing private perception store remain authoritative;
- Arra has ordinary sight and explicitly lacks `water_sense`;
- Arra's bank observation contains ordinary local cues only;
- a real D.1.4.2 `god_death` agent can receive a bounded prayer percept through
  `HeraldSystem` and issue one existing `SEND_PROBE` intent;
- the probe is causally justified by the prayer, not by private bank evidence
  or objective Hydrology/Burial state;
- the God can miss the prayer behind a metaphysical event veil;
- a false mortal response stays subjective testimony and does not overwrite
  objective truth;
- prayer, probe and response retain recoverable Ledger parentage;
- identical state, seed, intent and history reproduce identical resolution.

## Reproduction commands

```powershell
py -m unittest discover -s tests -q
py run_pilot_i0_trials.py --seed 42
py run_project_trials.py --days 30 --seed 42
py run_hydrology_trials.py --days 30
py run_affordance_trials.py --days 30
py run_aqueous_echo_trials.py --days 30 --seed 42
```

Expected summaries:

```text
Ran 146 tests
OK

LAWS: 13/13
LAWS: 10/10
LAWS: 19/19
LAWS: 26/26
LAWS: 26/26
```

I0 is entirely offline. No Ollama process, API key, network service or package
installation is required.

## Freeze decision

The local repository reproduced 146 tests with `OK` and the 13/13 I0 LAW gate.
All four earlier frozen regressions were also green in the same construction
run. The user explicitly accepted and froze I0 on 2026-09-04.

This decision freezes the I0 integration seam only. It does not claim that the
complete Pilot 0.1, a playable loop, external Player View or any later
increment exists.
