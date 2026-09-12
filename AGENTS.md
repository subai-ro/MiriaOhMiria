# World Zero repository instructions

## Mission

World Zero is a persistent autonomous world, not a quest generator waiting for
the player. Subjects act from partial knowledge, the server resolves objective
consequences, and history must remain forensically explainable.

The central invariant is:

> The server may know the objective world. A subject may know only what reached
> that subject through an allowed perceptual or informational path.

## Repository recovery requirement

Explicit user requirement (2026-09-06): the repository must be sufficient to
recover all project work needed to continue. Chat history and assistant memory
must never be the only record of a decision, result, constraint or next step.

At each meaningful stop, synchronize current state, spec/acceptance and the
active handoff with completed work, user feedback, exact acceptance boundaries,
unfinished work and the next operation. Preserve the actual current plan in
repository documents; a pointer to a chat or an ignored local file is not enough.
Include exact commands, results, version/source identity and evidence locations.
If reproduction depends on raw evidence, retain it in the repository or an
explicitly documented durable archive with integrity hashes and retrieval steps.
Do not call recovery complete for a fresh clone while required material exists
only in ignored local_acceptance files, local chat storage or uncommitted work.
Distinguish local documentation from committed and pushed state. This rule does
not independently authorize committing, pushing or publishing private captures.

## Read before editing

For every non-trivial task, read these files in order:

1. WORLD_ZERO_CURRENT_STATE.md
2. the current section at the top of README.md
3. docs/CANON_SOURCE_ORDER.md
4. the relevant file in specs/
5. the matching acceptance record in acceptance/
6. the implementation and tests you intend to change

Read docs/foundations/ when a task touches canon, terminology, player
experience, or long-range design. The foundation handoffs predate D.2.x and do
not describe the current executable version.

## Checkpoint status

- D.1.4.2 Epistemic Kernel: frozen after real local-model acceptance.
- D.2.0 PersistentProject: frozen and user-local accepted.
- D.2.1 Hydrology: frozen and user-local accepted.
- D.2.2 Physical Affordances + Local Perception: frozen and user-local accepted.
- D.2.3 Aqueous Silver Echo: frozen and user-local accepted on 2026-08-15
  after 139 tests and LAW 10/10, 19/19, 26/26, 26/26.
- Pilot 0.1 I0 Death God integration seam: frozen and user-local accepted on
  2026-09-04 after 146 tests, I0 LAW 13/13, and all earlier frozen regressions.
- Pilot 0.1 I1 internal playable loop: frozen and user-local accepted on
  2026-09-05 after guided play, 158 tests, I1 LAW 21/21, frozen I0 LAW 13/13,
  and all earlier frozen regressions.
- Pilot I3-N/N0 scheduling spike: user-accepted on 2026-09-05 with 18 new
  tests, 176 total and all frozen gates green. Not declared frozen.
  N1–N3 are now an offline candidate: 31 new tests, 207 total, 12/12 E2E and
  all frozen gates green at that review. The user subsequently authorized N4's
  initial local batch; all 72 calls / 18 runs completed and NEURAL FAILED:
  6/68 ordinary decisions valid, 18/18 exact replays. The harness adds 13 tests
  (220 total at that stage). The user subsequently approved the v2 action
  interface correction and ONE retry of at most 72 local calls, unchanged model
  parameters. The correction adds 20 tests (240 at that stage). The retry stopped at
  call 16 on the unchanged 180-second provider timeout: 15 returned decisions
  valid, seven resolved silt-work actions, four recorded histories replayed.
  That experiment remains PARTIAL. The user then explicitly authorized one
  fresh v2 batch: 72 calls / 18 histories completed, 64/68 ordinary decisions
  valid (94.12%), four overlong-text rejects, 18/18 exact disk replays.
  Structural/safety/replay criteria pass and minimum inquiry/work/reconsideration
  examples are present, with quality reservations (spec 15 / acceptance E.4).
  This is an experimental candidate, not user acceptance/freeze or HUMAN.
  That result alone authorized no follow-up. On 2026-09-06 the user explicitly
  approved a separate internal playable entry and ONE joint session (spec 16 /
  acceptance F.1): max 24 calls including prehistory, unchanged v2/settings,
  command/call evidence and post-session Creator report/replay. It adds 19
  offline tests (259 current), all frozen gates green. The guided session ended
  via quit at 17:16: 12 recorded commands, one prehistory model call, exact
  replay. The user saw no Nereid activity; next review was due at 18:00.
  The subsequent observable-life read-only audit is complete, implementation
  not started. See acceptance F.2 and docs/handoffs/WORLD_ZERO_RECOVERY_2026_09_06.md.
  No acceptance/freeze, HUMAN, cognition correction or additional N4 batch.

Do not call any future candidate frozen, accepted, or released until the user
explicitly accepts the required local gates.

## Non-negotiable laws

- No subject is omniscient or omnipotent, including Gods.
- Objective Ledger, process state, hashes, formulas, hidden actors, and
  Creator-only provenance are not automatically subjective knowledge.
- Cognition receives a SubjectiveWorldView or an equally bounded percept, never
  the server answer key.
- Perception, attention, interest, contact, request, Project, and quest are
  distinct causal steps. Never collapse them into one narrative trigger.
- Do not hard-code story chains such as FISHED becoming NEREID_INTEREST.
- Persistent Projects and fixed-clock world processes continue without the
  player and do not require a player role.
- A mind may author a decision or intent. An authoritative resolver decides the
  physical or institutional outcome.
- Locality, faculty, capability, resources, and private-evidence ownership are
  checked before time or state mutation.
- A physical consequence does not manufacture a new observation. A later
  allowed observation may create one private percept.
- Hidden metaphysics is objective world law, not prose emitted for a chosen
  character.
- Deterministic histories must remain deterministic. Sources, sinks, loss,
  state transitions, and causal parentage stay explicit.
- No global story director may force significance, interest, contact, or a
  player-centered future.
- Do not weaken a LAW, delete a counterfactual, or relabel a failure merely to
  make a checkpoint pass.

## Change discipline

1. Inspect Git status and preserve unrelated user work.
2. State the checkpoint and causal boundary being changed.
3. Prefer the smallest additive seam over rewriting a frozen layer.
4. Add positive, negative, ownership/locality, and counterfactual tests where
   relevant.
5. Keep model policies in tests clearly labelled as doubles unless they are
   canonical cognition.
6. Run the smallest relevant tests, then the complete offline suite.
7. Run every frozen acceptance gate affected by the change.
8. Update the current spec, acceptance record, README, and
   WORLD_ZERO_CURRENT_STATE.md when behavior or checkpoint status changes.
9. Report changed files, commands, exact results, remaining risks, and status.

Do not install dependencies, rewrite public schemas, delete evidence, commit,
tag, push, or use network services unless the user asks or the task clearly
requires it. Never use destructive Git recovery to discard user changes.

Generated local acceptance output belongs in local_acceptance/ and must not
overwrite the checked-in builder evidence in acceptance/.

## D.2.3 verification

On Windows PowerShell:

    powershell -ExecutionPolicy Bypass -File .\verify_d23.ps1

Equivalent individual commands:

    py -m unittest discover -s tests -q
    py run_project_trials.py --days 30 --seed 42
    py run_hydrology_trials.py --days 30
    py run_affordance_trials.py --days 30
    py run_aqueous_echo_trials.py --days 30 --seed 42

Expected current offline results with frozen I1, accepted N0 and the N4 harness:

- 259 unit tests, OK
- PersistentProject: 10/10 LAW
- Hydrology: 19/19 LAW
- Affordances + Local Perception: 26/26 LAW
- Aqueous Silver Echo: 26/26 LAW

D.2.3 reproduced all five results on the user machine and was explicitly
accepted and frozen on 2026-08-15, when the complete suite contained 139 tests.
The additional seven I0 tests account for its frozen total of 146. Frozen I1
adds twelve tests, producing its frozen total of 158. N0 added eighteen
scheduling tests (176 at acceptance). N1–N3 added 31 (207 at their review).
The initial N4 harness added 13 (220); v2 added 20 (240); internal play adds 19 (259).

D.2.3 is entirely offline. It requires no Ollama process, API key, or package
installation.

## Pilot 0.1 I0 verification

On Windows PowerShell:

    py -m unittest discover -s tests -q
    py run_pilot_i0_trials.py --seed 42

Expected results:

- 259 unit tests, OK in the current worktree; I0 froze at 146
- Pilot I0: 13/13 LAW

I0 is entirely offline. It requires no Ollama process, API key, network
service, or package installation.

## Pilot 0.1 I1 verification

On Windows PowerShell:

    py -m unittest discover -s tests -q
    py run_pilot_i0_trials.py --seed 42
    py run_pilot_i1_trials.py --seed 42

Expected results:

- 259 unit tests, OK; I1 froze at 158
- frozen Pilot I0: 13/13 LAW
- frozen Pilot I1: 21/21 LAW

The internal playable loop starts with:

    py play_pilot_i1.py

I1 is entirely offline and uses only the Python standard library.

## Pilot I3-N / N0 verification

    py -m unittest discover -s tests -p test_pilot_n0.py -v

Expected: 18 N0 tests, OK; then run the complete 259-test suite and all six
frozen LAW gates above. The N0 result is a feasibility proof, not acceptance of
the full I3-N contract, canonical cognition or the external pilot.

`serial_actions=True` is opt-in on the existing pilot factories. In that mode,
route timed requests through `PilotSession.perform` / `sense_echo`; do not call
timed bridges directly without the whole-action guard. Preserve the default
frozen I1 mode, and keep all N0 scheduling doubles inside tests.

## Pilot I3-N / N1–N3 candidate verification

    py -m unittest discover -s tests -p test_pilot_nereid.py -v
    py run_pilot_nereid_trials.py --seed 42

Expected: 31 tests (one named case per N01–N28 plus three extra boundaries),
12/12 E2E checks; then all 259 tests and the frozen gates. Lab policies belong
only in tests or the explicitly labelled acceptance runner, never a playable
entry-point registry. The opt-in factory requires an explicit transport.
Creator HTML is post-session, not an external visual Player View/HUMAN pass.

## Pilot I3-N / N4 harness verification

    py -m unittest discover -s tests -p test_pilot_nereid_neural.py -v
    py -m unittest discover -s tests -p test_pilot_nereid_contract_v2.py -v

Expected: 13 harness and 20 v2 offline tests; then the full suite/frozen gates.
They use labelled doubles and never need a running provider. The initial real
N4 batch is complete and failed (72 calls; 6/68 ordinary reviews valid). Its
local artifact directory must not be reused or overwritten. Do not repeat the
real runner merely to verify a checkout or transfer. The approved v2 retry has
stopped on its sixteenth call; preserve that partial result too. The separately
approved fresh batch then completed (72 calls, 64/68 ordinary valid, 18/18
replays). Preserve all three series. No new run follows automatically from
the passing structural floor; every further batch needs explicit approval.

## Neural work

Internal session verification: `py -m unittest discover -s tests -p test_pilot_nereid_playtest.py -q`
(19 offline tests), then the complete suite/frozen gates. `play_pilot_nereid.py`
requires explicit local-session approval and a new local_acceptance directory.
Do not restart an ended session, replace the mind or expose private diagnostics
in Player View. The first guided session authorized by spec 16 has ended;
do not restart it. Its completed result and negative player-visibility review
are in acceptance F.2. The next unfinished step is the observable-life
design/acceptance contract described in docs/handoffs/WORLD_ZERO_RECOVERY_2026_09_06.md.
Its status is not accepted/frozen until the user explicitly makes that decision.

The frozen local neural baseline is Ollama ministral-3:8b, temperature 0.15,
context 8192. Offline neural tests use doubles and must not call a provider.
Do not silently substitute a different model or change the baseline parameters.
Real-model trials require an explicit experimental plan and user approval.

The I3-N design and acceptance contract exist under specs/ and acceptance/.
N0 is user-accepted. N1–N3 owned evidence, bounded attempts and settled
observation/replay are builder-verified and awaiting the user's review.
Offline doubles are not canonical cognition or permission to run a provider.
Canonical model-backed cognition
remains separately gated: it must
consume bounded private evidence, issue intents through existing resolvers,
tolerate ignorance and misinterpretation, and remain free to ignore the silver
echo.

## Definition of done

A task is done only when the requested behavior exists, relevant negative
boundaries remain intact, tests and acceptance gates pass, documentation agrees
with the code, and candidate-versus-frozen status is stated accurately.
