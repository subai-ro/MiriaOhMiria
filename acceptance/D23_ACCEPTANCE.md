# D.2.3 acceptance record

**Checkpoint:** `world_zero_v0_0d2_3`
**Stage:** P4-B — Aqueous Silver Echo
**Built:** 2026-08-15
**User-local acceptance:** 2026-08-15
**Status:** user-local accepted and frozen

## Builder and user-local verification

| Gate | Result |
| --- | --- |
| Complete offline unit suite | 139 tests, OK |
| D.2.0 PersistentProject regression | 10/10 LAW |
| D.2.1 Hydrology regression | 19/19 LAW |
| D.2.2 Physical Affordances + Local Perception regression | 26/26 LAW |
| D.2.3 Aqueous Silver Echo | 26/26 LAW |

The user-local run reproduced all five gates and the user explicitly accepted
the results on 2026-08-15.

## New proof boundary

The P4-B gate proves:

- `material_medium_contact.v1`, not `FISHED`, is the physical input contract;
- another silver item and another event type obey the same law;
- hands and iron create no silver impulse;
- repeated contact accumulates continuously and later decays;
- transport uses same-boundary Hydrology flows and cannot cross a zero-flow
  edge;
- Mirror/Whisper and closed/open Gate counterfactuals diverge physically;
- objective echo creates no subjective knowledge by itself;
- valid sensing is local, faculty-gated, private and qualitative;
- raw echo transitions remain guarded;
- no attention, contact, request, quest or Project mutation is manufactured;
- the contact → Hydrology → Echo → sensing → private-percept braid is
  forensically recoverable;
- identical histories reproduce identical state, trace, Ledger and percept.

## Reproduction commands

```powershell
py -m unittest discover -s tests -q
```

```powershell
py run_project_trials.py --days 30 --seed 42 --log-file d23_project_regression.txt
```

```powershell
py run_hydrology_trials.py --days 30 --log-file d23_hydrology_regression.txt
```

```powershell
py run_affordance_trials.py --days 30 --log-file d23_affordance_regression.txt
```

```powershell
py run_aqueous_echo_trials.py --days 30 --seed 42 --log-file d23_aqueous_echo_acceptance.txt
```

Expected terminal summaries:

```text
Ran 139 tests
OK

LAWS: 10/10
LAWS: 19/19
LAWS: 26/26
LAWS: 26/26
```

No Ollama server, neural model or API key is required for D.2.3.

## Freeze decision

The pre-freeze rule required the user-local run to reproduce all five gates and
the user to accept the results explicitly. Both conditions were met on
2026-08-15, so P4-B is frozen. Any later failure remains evidence to inspect,
not a reason to weaken or reclassify a LAW.
