# D.2.2 acceptance record

**Checkpoint:** `world_zero_v0_0d2_2`  
**Stage:** P4 — Physical Affordances + Local Perception  
**Built:** 2026-08-15  
**Status:** candidate; independent user-local acceptance pending

## Builder-side verification

| Gate | Result |
| --- | --- |
| Complete offline unit suite | 119/119 |
| D.2.0 PersistentProject regression | 10/10 LAW |
| D.2.1 Hydrology regression | 19/19 LAW |
| D.2.2 Physical Affordances + Local Perception | 26/26 LAW |

## Reproduction commands

```powershell
py -m unittest discover -s tests -q
```

```powershell
py run_project_trials.py --days 30 --seed 42 --log-file d22_project_regression.txt
```

```powershell
py run_hydrology_trials.py --days 30 --log-file d22_hydrology_regression.txt
```

```powershell
py run_affordance_trials.py --days 30 --log-file d22_affordance_acceptance.txt
```

Expected terminal summaries:

```text
Ran 119 tests
OK

LAWS: 10/10
LAWS: 19/19
LAWS: 26/26
```

## Freeze rule

Do not mark P4 frozen until the user-local run reproduces all four gates. A
failure is evidence to inspect, not a reason to weaken or reclassify a LAW.
