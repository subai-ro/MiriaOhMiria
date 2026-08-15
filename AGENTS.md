# World Zero repository instructions

## Mission

World Zero is a persistent autonomous world, not a quest generator waiting for
the player. Subjects act from partial knowledge, the server resolves objective
consequences, and history must remain forensically explainable.

The central invariant is:

> The server may know the objective world. A subject may know only what reached
> that subject through an allowed perceptual or informational path.

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

Expected results:

- 139 unit tests, OK
- PersistentProject: 10/10 LAW
- Hydrology: 19/19 LAW
- Affordances + Local Perception: 26/26 LAW
- Aqueous Silver Echo: 26/26 LAW

D.2.3 reproduced all five results on the user machine and was explicitly
accepted and frozen on 2026-08-15.

D.2.3 is entirely offline. It requires no Ollama process, API key, or package
installation.

## Neural work

The frozen local neural baseline is Ollama ministral-3:8b, temperature 0.15,
context 8192. Offline neural tests use doubles and must not call a provider.
Do not silently substitute a different model or change the baseline parameters.
Real-model trials require an explicit experimental plan and user approval.

The next allowed stage is design-first P5 canonical model-backed Nereid
cognition. Its first artifact must be a design and acceptance contract, not
implementation code. P5 must consume bounded private evidence, issue intents
through existing resolvers, tolerate ignorance and misinterpretation, and
remain free to ignore the silver echo.

## Definition of done

A task is done only when the requested behavior exists, relevant negative
boundaries remain intact, tests and acceptance gates pass, documentation agrees
with the code, and candidate-versus-frozen status is stated accurately.
