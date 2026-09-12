# Miria cloud transfer checkpoint — 2026-09-12

## Purpose

Preserve the recoverable local state on GitHub without mixing unfinished
Nereid work into the stable `main` branch or discarding local-only artifacts.

## Source and remote

- Local checkout: `C:\Creation\world_zero_cod`
- Local branch at audit: `main`
- Local HEAD at audit: `9579bd15ef793e197ef722719e4297ace2c8d1db`
- GitHub remote: `https://github.com/subai-ro/MiriaOhMiria.git`
- Live remote `main` before transfer:
  `851ed83accbbae7ac9439edbe1beaf1e281d4982`
- Stable transfer: `main` was fast-forwarded to local HEAD `9579bd1`.
- WIP destination: `cloud/miria-local-checkpoint-2026-09-12`, based on
  `9579bd1`. This branch is a recovery checkpoint, not acceptance, freeze,
  release, or evidence that the complete offline suite is green.

Remote access and the live `main` ref were verified with Git. Repository
visibility (public/private) was not independently established in this audit.

## WIP content selected for the cloud checkpoint

The checkpoint contains the modified Nereid implementation, runner,
specification, acceptance/current-state records and canon instructions, plus
the previously untracked v2 contract, playtest composition, tests, playable
entry point and two recovery handoffs. A path-only credential-pattern scan of
the selected files returned no matches. `git diff --check` passed.

The regular working tree and index were intentionally left untouched while the
checkpoint commit was assembled through a temporary index.

## Local-only exclusions

The following remain in the local checkout and were neither deleted nor sent
to the cloud checkpoint:

- `build/pyinstaller-gui/**` — generated PyInstaller build products.
- `dist/**` — ignored packaged output.
- `local_acceptance/**` — ignored local evidence and model/session captures.
- `tests/_tmp_edit.py`, `worldzero/_edit_pilot_playable.py`, and
  `worldzero/_tmp_edit.py` — scratch edit helpers.

The ignored evidence is still a recovery dependency. A fresh clone can recover
the selected code and project records, but not the raw local acceptance corpus
until a separately approved private archive or repository-safe evidence package
is created and verified.

## Verification performed during transfer

On the current working state:

- `python -m unittest discover -s tests -p test_pilot_nereid_contract_v2.py -q`
  passed: 20 tests.
- `python -m unittest discover -s tests -p test_pilot_nereid_playtest.py -q`
  passed: 19 tests.
- `python -m unittest discover -s tests -q` ran 264 tests and reported the four
  failures listed below.

An isolated archive of both the pre-transfer remote commit `851ed83` and local
HEAD `9579bd1` ran 225 tests with the same four failures. The two GUI commits
therefore did not introduce these failures, but the repository must not be
described as fully green:

1. `test_pilot_i1.PilotI1PlayableLoopTests.test_false_alarm_changes_death_behavior_without_becoming_truth`
2. `test_pilot_i1.PilotI1PlayableLoopTests.test_h0_h1_h2_have_visible_durable_and_causal_differences`
3. `test_pilot_i1.PilotI1PlayableLoopTests.test_player_view_uses_owned_observations_and_visible_manifestations_only`
4. `test_pilot_n0.PilotN0SchedulingTests.test_prayer_and_answer_are_complete_before_due_review`

`python play_pilot_i1_gui.py --help` passed from the isolated `9579bd1`
archive. No interactive GUI smoke or new provider/model run was performed.

## Continuation

- Use `main` at `9579bd1` for the stable GUI checkpoint.
- Use `cloud/miria-local-checkpoint-2026-09-12` to inspect or continue the
  recovered Nereid WIP.
- Before merging the WIP, reconcile the four baseline failures and the stale
  test-count/status wording in active documents, then run the required offline
  and frozen gates.
- Preserve all local-only evidence and scratch files until their archival or
  deliberate disposal is separately decided.
