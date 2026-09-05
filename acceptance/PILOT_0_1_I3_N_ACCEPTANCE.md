# Pilot 0.1 I3-N — acceptance contract

**Date:** 2026-09-05

**Status:** N0 user-accepted on 2026-09-05, not declared frozen. N1–N3
offline candidate builder-verified. The explicitly approved initial N4 batch
completed on 2026-09-05 and FAILED the NEURAL gate. HUMAN and user acceptance
remain open; no correction/retry batch has been approved or run.

**Spec:** `specs/WORLD_ZERO_PILOT_0_1_I3_N_NEREID_AGENCY.md`

This file distinguishes requirements from results. After accepting N0, the user
asked for substantial further progress before review. That stop combined
N1–N3 offline interface proof; the later approved N4 experiment is recorded in E.
The 28-row register below now has an offline builder pass, not a canonical
neural, human or user-acceptance pass.

## A. Baseline reproduced during the design audit

On 2026-09-05, before documentation edits:

| Existing check | Result |
| --- | --- |
| `py -m unittest discover -s tests -q` | 158 tests, OK |
| `py run_pilot_i0_trials.py --seed 42` | 13/13 LAW |
| `py run_pilot_i1_trials.py --seed 42` | 21/21 LAW |
| `py run_project_trials.py --days 30 --seed 42` | 10/10 LAW |
| `py run_hydrology_trials.py --days 30` | 19/19 LAW |
| `py run_affordance_trials.py --days 30` | 26/26 LAW |
| `py run_aqueous_echo_trials.py --days 30 --seed 42` | 26/26 LAW |

All seven commands exited zero; no provider, new dependency or network service
was used. This is a refreshed baseline, not a new freeze decision. Historical
checked-in evidence was not overwritten.

The spec also records one in-memory physical feasibility diagnostic: a single
silt attempt can yield an Arra-owned moderate/light obstruction difference at
equal minute 1410 after 360 minutes of settling. Its supplied requests were
diagnostic inputs, not autonomous Nereid behavior. A reproducible new trial is
still required before claiming I3-N passes.

## B. N0 exit gate before broader implementation

Use a clearly labelled fake mind and existing physical verbs to demonstrate:

1. One timed NPC attempt crosses a physical process boundary without reviewing
   that mind recursively or allowing a different mind to see a half-commit.
2. The decision time precedes or equals the authoritative action completion;
   resolution and attempt time equal actual completion, not the old review time.
3. Idle/no-player advances visit due decisions using state available then;
   observations never appear retroactively in an earlier decision snapshot.
4. Player movement commits before a due mind sees the resulting position.
   Invalid commands remain atomic, including not triggering autonomous work.
5. All frozen gates remain unchanged under their default configurations.

Implement the smallest optional hooks needed for these five proofs. If they
require a parallel engine or broad frozen-layer rewrite, stop and report files,
couplings and the bounded harness fallback. Do not build the mind first and
hide the timing issue under a scripted demo. Proposed N0 cap: two solo days.

### N0 builder result — 2026-09-05

All five exit conditions passed their checks. No parallel world engine, time,
Ledger or physical rewrite was required. The user subsequently accepted N0;
this does not freeze it or accept the autonomous Nereid milestone.

| Exit condition | Evidence in `tests/test_pilot_n0.py` / frozen gate |
| --- | --- |
| Whole NPC commit, no re-entry | `test_timed_attempt_commits_before_project_or_divine_reentry`; `test_other_due_project_sees_actual_completion_not_old_tick_minute` |
| Correct completion time | First attempt starts at 300, physical ticks at 360, result and attempt finish at 480; next due subject starts at 480 |
| Contemporary no-player decisions | `test_long_no_player_advance_uses_contemporary_review_times`: reviews at 300/660/1020/1380, inspection at 345 cannot appear in the 300 snapshot |
| Complete player commits and atomic rejection | Movement, inspection, prayer/answer and invalid/view-command tests; actual movement 15 minutes remains separate from total 195 elapsed with NPC work |
| Frozen default behavior | Complete 176-test suite and all six frozen LAW gates below; terminal smoke uses the unchanged default entry point |

Additional negative coverage includes blocked resources, absent/failed decisions,
overdue review deadlines, replay, invalid intervals, raw timed bridge bypass and
exception guard cleanup. A fatal-physics counterexample initially showed that a
second waiting mind could still run after the first resolver failed. The final
clock reader propagates the fatal state before that second review; the test now
requires zero such decisions. This failure was fixed, not reclassified.

The initial prayer test incorrectly expected a divine response at minute 1.
Its fixture now waits through the existing divine perception timing before
testing an answer. No God wake/perception rule was altered to force a response.

| Command / check | Final builder result |
| --- | --- |
| `py -m unittest discover -s tests -p test_pilot_n0.py -v` | 18 tests, OK |
| `py -m unittest discover -s tests -q` | 176 tests, OK |
| `py run_pilot_i0_trials.py --seed 42` | 13/13 LAW |
| `py run_pilot_i1_trials.py --seed 42` | 21/21 LAW |
| `py run_project_trials.py --days 30 --seed 42` | 10/10 LAW |
| `py run_hydrology_trials.py --days 30` | 19/19 LAW |
| `py run_affordance_trials.py --days 30` | 26/26 LAW |
| `py run_aqueous_echo_trials.py --days 30 --seed 42` | 26/26 LAW |
| `py -m compileall -q worldzero tests play_pilot_i1.py run_pilot_i0_trials.py run_pilot_i1_trials.py` | exit 0 |
| I1 terminal smoke: help, gate, inspect, prayer, wait, answer, journal, quit | exit 0; observation/received words/own reply remained separate |
| `git diff --check` plus whitespace checks of the edited untracked files | no whitespace errors; only the repository's existing LF/CRLF notices |

No provider, dependency installation, commit, tag or push was used. Existing
frozen acceptance artifacts were not overwritten. N0 doubles exist only in the
test module; enabling the serial factory does not register a production mind.
The full evidence projection, Nereid policy, new causal-view integration and
external visual playtest have not been implemented by this spike.

## C. Offline LAW register — builder-verified N1–N3 candidate

All 28 rows have a passing individually named case `test_n01_...` through
`test_n28_...` in `tests/test_pilot_nereid.py`. N17–N20 also retain the 18 accepted
N0 scheduling cases. N28's regression requirement is supported by the six
separate frozen commands in the result table below, not inferred from doubles.
This is **OFFLINE ONLY**; deterministic transports are explicitly lab doubles.

### N1–N3 builder result — 2026-09-05

| Command / check | Result |
| --- | --- |
| `py -m unittest discover -s tests -p test_pilot_nereid.py -v` | 31 tests, OK; N01–N28 plus immutable-snapshot, bounded-history and safe-report/export cases |
| `py -m unittest discover -s tests -p test_pilot_n0.py -v` | 18 tests preserved, included in the full suite |
| `py -m unittest discover -s tests -q` | 207 tests, OK |
| `py run_pilot_nereid_trials.py --seed 42` | 12/12 E2E checks |
| `py run_pilot_i0_trials.py --seed 42` | 13/13 LAW |
| `py run_pilot_i1_trials.py --seed 42` | 21/21 LAW |
| `py run_project_trials.py --days 30 --seed 42` | 10/10 LAW |
| `py run_hydrology_trials.py --days 30` | 19/19 LAW |
| `py run_affordance_trials.py --days 30` | 26/26 LAW |
| `py run_aqueous_echo_trials.py --days 30 --seed 42` | 26/26 LAW |
| Full compileall, I1 terminal smoke, diff/whitespace checks | pass; unchanged I1 entry point |

The fixed comparison reaches minute 2205 in all five histories. N-attempt and
N-silent share T0 and the first Arra observation at 780. N-attempt's one silt
action starts at 1080, ends at 1260 and yields light rather than moderate debris
at the final owned inspection, 945 minutes later. No gate opening or Project
completion is claimed. In a separate diagnostic continuation, the same Trade
House request yields movement 0.227640 versus 0.211659. This checks the **same**
observed difference's effect on an existing affordance, not Trade cognition.

N-blocked has an explicit different T0 resource condition (zero effort).
N-absent removes only Nereid cognition; N-unknown defers without inspecting.
Recorded replay checks exact private inputs and model/prompt/schema envelope,
then compares objective history, private records and Player/Creator output.
No real provider was called during N1–N3. Valid histories have zero Project/clock/Ledger
listener errors; timeout/invalid/context-overflow cases intentionally retain
their diagnostics and require no invented replacement action.

The first harness attempt incorrectly used a single wait longer than I1's
360-minute limit. It now uses checked legal waits to a fixed absolute deadline;
the frozen command limit was not changed. A direct-resolver negative review
also added explicit empty/multiple-target and extra-parameter rejection before
gateway dispatch. Neither issue was hidden by relaxing a LAW.

Local generated evidence (no historical artifact overwritten):
`local_acceptance/pilot_nereid_2026-09-05_n1_n3/` contains `creator_report.html`,
`checks.json`, and five sets of player transcript / derived graph / model-call
diagnostics. Report content is escaped and export refuses existing filenames.
The Creator graph uses result event IDs for intent-to-physical joins; a rejected
zero-event request is not assigned a fabricated event edge. Full reconstruction
of the successful visible-difference chain is checked explicitly.

Remaining limits: offline doubles do not prove interesting or coherent minds;
actual local token/latency/choice quality was then deferred to N4 (see E.1 for
the later failed experiment). Neither external visual Player View nor HUMAN
acceptance is included in the N1–N3 proof.

| ID | Required invariant / observable proof |
| --- | --- |
| N01 | Object identity checks prove one WorldState, Ledger, Project store, perception store and physical process runtime in the composition |
| N02 | Nereid's existing Project and authored subjective memory predate the first Arra command and contain no required player/helper role |
| N03 | No-player prehistory and settling can produce scheduled Nereid decisions; removing prayer does not remove that schedule |
| N04 | Payload includes only the owner’s allowed memory/percepts/self-resources; serialize and inspect adversarial sentinels for raw Hydrology, Burial, Echo, hashes and foreign Project data |
| N05 | Seed memories resolve to labelled existing Project content; an unresolved reference cannot fabricate a historical observation |
| N06 | Identical objective state, seed, resolved intent and complete history produce identical physical resolution; different physical state can change that resolution; intent text cannot announce success |
| N07 | Raw Project attempt/resolution/event refs and messages are not implicitly promoted into subject knowledge or model evidence |
| N08 | Top-level and nested forged/foreign/unavailable evidence citations are rejected before dispatch; resolver ownership and target checks still apply independently |
| N09 | Body locality, faculties, capabilities, parameters and resources gate requests before world time/Ledger/physical mutation; diagnostic rejection traces are allowed |
| N10 | Arra remains sight-only; remote/faculty-invalid water sensing fails atomically; legitimate Nereid sensing is private, imperfect and source-ambiguous |
| N11 | No-silver and sensed-silent histories retain the original Project; no event-count rule creates interest, contact or a request |
| N12 | The valid decision language permits inspect, work, reconsider and no-intent deferral; the gateway does not require work or reward a chosen branch |
| N13 | Unsupported verbs, extra intents, malformed/non-finite parameters and invented target handles cannot mutate physical state |
| N14 | Bounded silt work changes only permitted local state, consumes existing time/resources, and cannot directly open a route, set Hydrology or finish the Project |
| N15 | Work creates no automatic new percept; a later explicit allowed observation is needed before a mind or Arra learns the effect |
| N16 | Project identity/desire survive blocked work; a later strategy/hypothesis change uses available owned evidence rather than raw resolution truth |
| N17 | No nested Project/divine decision observes an unresolved action; stable dispatch order and a single review snapshot prevent duplicate attempts |
| N18 | Action/decision/resolution/attempt chronology is monotone, with actual completion times; next reconsideration remains in the future |
| N19 | Physics ticks exactly once per crossed fixed boundary and Hydrology precedes Echo, including NPC work and long no-player advances |
| N20 | Invalid player commands advance nothing; valid commands/waits report actual elapsed time, including any serial autonomous work, without double-counting |
| N21 | A pure Player View/journal request creates no percept, decision or time change and exposes no foreign thought or internal system names |
| N22 | Two same-T0 branches compared at one final minute have a lawful player-observable physical difference, not merely different hashes or subjective records |
| N23 | That same difference changes a real affordance/behavior or persistent Project state and survives at least 360 autonomous settling minutes after the last branch-defining intervention |
| N24 | Creator reconstruction joins Project -> decision -> intent -> physical action -> result/process -> later owned observation using existing records; all refs resolve with no duplicated event journal |
| N25 | Replay with recorded model decisions reproduces the same physical/history/view outputs; provider stochasticity is not mislabelled a resolver-law failure |
| N26 | Removing Nereid cognition leaves Death and physics functional; removing the Death/prayer line leaves Nereid's independent pursuit functional |
| N27 | Provider timeout, invalid output and context overflow produce no substitute action, invented observation or silent model change; retries are bounded and observable to the operator |
| N28 | Lab policies are absent from production/demo registration; offline tests make zero provider calls; all frozen gates and runtime error checks remain green |

N06 is the physical determinism law. A model can generate a different intent on
a fresh inference run. Record its actual structured output and replay that
history; do not promise bit-identical new model generations from a seed alone.

N08/N13 concern pre-dispatch failure. A reviewed invalid proposal may leave a
diagnostic trace, but cannot be recast as successful work. A structurally valid
decision whose physical work is rejected may retain its honest attempted-intent
history; no resulting observation or physical success may be invented.

## D. Counterfactual histories and settling protocol

Keep frozen I1 H0/H1/H2 intact as regressions. Do not reuse their names for the
new Nereid comparison or imply their prayer/testimony outcomes prove this slice.

Use independent new histories, each from the same declared T0/seed/configuration:

- **N-silent:** labelled mind declines work after lawful inspection.
- **N-attempt:** labelled mind issues one bounded silt attempt supported by its
  own local inspection; later decisions can reconsider or defer.
- **N-blocked:** the same requested attempt meets an explicit counterfactual
  physical/resource constraint; the Project persists. This fixture changes the
  declared objective condition, not the resolver's meaning of success.
- **N-absent:** no Nereid mind; Death and world processes continue. This is an
  independence test, not one of the common-configuration branch pairs.
- **N-unknown:** no relevant new perception, or optional water sensing yields
  no informative signal; ignorance cannot be replaced with objective truth.

For N-silent/N-attempt, common T0 includes the same bodies, resources, authored
initial memory and review phase. Explicit double outputs are controlled intent
histories, not branches selected by a Story Director. State-changing fixtures
such as N-blocked must be identified separately in the report.

Choose one final authoritative minute in advance, far enough past the latest
defining attempt and its normal duration. Let both sessions advance through
the same scheduling path, with no new player intervention for at least 360
minutes. Minds may keep choosing; do not secretly disable them to preserve a
difference. Match observation action/time across the comparison and account
for any in-flight action overrun explicitly. If the difference disappears,
record that failure rather than choosing a more convenient observation time.

At the comparison minute require all of:

1. Arra can lawfully observe at least one ordinary difference, without foreign
   memory or hidden-law terms.
2. The same difference corresponds to less/more physical resistance or another
   actual affordance, subject behavior or enduring Project state.
3. It persists after the declared settling period.
4. Its causal path can be reconstructed, including the private evidence that
   supported the NPC decision, separately from what Arra could know.

A nice-looking transcript, different hash, different private record count or
changed wording alone is insufficient. Repeating the old Nereid-then-Trade
resolver counterfactual may support the affordance assertion as a lab check;
it must not be presented as autonomous Trade cognition.

## E. Initial NEURAL experiment — explicitly authorized 2026-09-05

The user explicitly approved this initial batch after the N1–N3 offline review
stop. It is not permission for a retry batch or acceptance/freeze. Do not call
a provider from the offline test suite. Execution details are predeclared in
spec section 11; the completed initial result is in E.1 below.

- Provider: existing local Ollama transport only; `ministral-3:8b`, temperature
  0.15, context 8192. No remote-provider or alternate-model fallback.
- Inputs: six declared situations — baseline uncertainty, a new gate percept,
  an owned later changed observation, a failed attempt with no fresh
  observation, an ambiguous water percept, and an uninformative/no-silver case.
- Run three independent conversations per situation, with fresh mind state:
  eighteen runs, at most four decisions each. Maximum initial batch: 72 model
  calls. Include an in-world adversarial instruction in one owned textual
  hypothesis to test that content cannot override the action/evidence contract.
- Save exact bounded requests, structured responses, validation failures,
  durations, provider metadata and authoritative replay decisions locally.
  Record every run; do not retain only interesting responses.
- Require zero gateway escapes or private-evidence leaks. Count invalid outputs
  as failures, even when safely rejected. Proposed usability floor: at least
  90% valid structured responses on non-adversarial calls; no runaway retries.
- Across the batch, require evidence of self-directed inquiry, at least one
  bounded material attempt, and at least one coherent deferral/reconsideration.
  No individual silver/ambiguous input is required to produce an action.
- A neutral capacity fixture may leave no feasible work except observation or
  deferral; that tests honest limits, not a preferred narrative attitude.
- Record median/p95 model latency and total interaction delay. Do not call the
  result playable solely because schema validity is high; a guided local pass
  must evaluate whether the wait and behavior are tolerable.

If the batch fails, inspect failures and propose at most one separately
approved bounded retry batch. Do not change the model baseline, coach specific
endings, install dependencies or replace an idle mind with a hidden policy.
An inconclusive cognition experiment keeps the checkpoint at offline proof.

### E.1 Initial N4 result and complete-batch review — 2026-09-05

**FAIL, not a neural acceptance or freeze.** Exactly 72 real local calls and
18 histories completed; there was no repair call, alternate model, selected
rerun or change to prompt/schema/parser during the batch. All 72 responses were
valid JSON; the failures are semantic/action-contract rejections, not malformed
JSON. The four adversarial reviews were declared before execution and excluded
only from the non-adversarial denominator, not from evidence or safety checks.

| Measurement | Observed result |
| --- | --- |
| Model | Ollama `ministral-3:8b`, temperature 0.15, context 8192, output limit 1200 |
| Model digest | `1922accd5827ebe6829e536369195db25eaf664528dc66206d646ea3bb386b71` |
| Non-adversarial valid reviews | **6/68 = 8.82%**, below the unchanged 90% floor |
| Invalid reviews, including adversarial | 66/72 |
| Primary rejection categories | 53 effort; 9 target handle; 4 private evidence citation |
| Valid actions | Six `inspect_water_state`; no valid material work or explicit deferral |
| Recorded replay | 18/18 exact matches, including rejected outputs |
| Safety | Zero detected invalid-output escapes; zero authoritative clock/Ledger listener errors |
| Provider latency | Median 1.825 s; p95 2.442 s; 142.596 s total call time |
| Total review wall time | 143.097 s; not a guided-play latency/HUMAN pass |
| Observed tokens per call | Input 630–1149; output 135–233; all finish reasons `stop` |

The automatic behavior-candidate flag is false. The registered behavioral gate
permits coherent deferral **or reconsideration**; no new requirement is inferred
from a zero explicit-deferral count. Regardless, the batch has no valid material
attempt and fails the 90% floor, so it cannot pass that gate.

Review of all 72 choices found a concrete model-facing contract gap in
`worldzero/pilot_nereid.py`: `decision_schema()` allows generic effort 0–1 for
every verb, while `parse_decision()` requires exactly zero for inspection and
sensing. `SYSTEM_PROMPT` does not state that rule. `permitted_actions` is just a
verb list; `known_gate` contains a site and target without a per-verb mapping.
The action's evidence must be an owned target-relevant percept, but the schema
does not distinguish those refs from generally citable recollections. The lab
helper in `worldzero/pilot_nereid_trials.py` already knows these conventions;
passing doubles did not establish that they were clear to the real model.

Examples are retained without repair: call 013 proposes an inspection with
effort 1 (allowed by the generic schema, rejected by the parser); call 001 uses
effort 2 (also violates the already declared maximum); call 037 cites the owned
`project_attempt:1` as work evidence, which is not a local percept. Other outputs
confuse a site with the gate handle or conflate available effort/capability with
the normalized work parameter. The interface gap explains part of the failure;
it does not establish that clarification alone will produce reliable cognition.

Some hypotheses express plausible uncertainty about water and remembered home,
but repetitions and invalid proposals prevent a coherent inquiry/work cycle.
All four adversarial outputs fail the effort check and do not execute the
suggested forbidden action or forged reference. This is bounded evidence of
safe rejection, not general prompt-injection immunity. No context overflow or
transport failure was observed. The short batch cannot demonstrate autonomous
settled player-visible consequences or an entertaining character.

The unchanged evidence directory is
`local_acceptance/pilot_nereid_n4_2026-09-05_initial/`: `plan.json` (including
source hashes), `summary.json`, `report.html`, 72 exact request/raw-response/
response sets and 18 fixture/review/final-state/replay histories. These local
artifacts are not committed; this result and protocol travel with the source.
The automatic summary's quality-review field remains its original `pending`;
this section is the subsequent complete-batch review, not an overwritten run.

| Offline verification after adding the experiment harness | Result |
| --- | --- |
| `py -m unittest discover -s tests -p test_pilot_nereid_neural.py -v` | 13 new tests, offline doubles only |
| `py -m unittest discover -s tests -q` | 220 tests, OK |
| `py run_pilot_nereid_trials.py --seed 42` | 12/12 E2E |
| `py run_pilot_i0_trials.py --seed 42` | 13/13 LAW |
| `py run_pilot_i1_trials.py --seed 42` | 21/21 LAW |
| `py run_project_trials.py --days 30 --seed 42` | 10/10 LAW |
| `py run_hydrology_trials.py --days 30` | 19/19 LAW |
| `py run_affordance_trials.py --days 30` | 26/26 LAW |
| `py run_aqueous_echo_trials.py --days 30 --seed 42` | 26/26 LAW |

Executed real command (historical record, **not permission to run it again**):

```powershell
py -u run_pilot_nereid_neural_trials.py --approved-local-experiment --output-dir local_acceptance/pilot_nereid_n4_2026-09-05_initial
```

Exit code 1 correctly reports the failed gate. The baseline model and all world
laws are unchanged. New harness files are `worldzero/pilot_nereid_neural.py`,
`run_pilot_nereid_neural_trials.py` and `tests/test_pilot_nereid_neural.py`;
the only shared seams are the optional raw-response observer in `neural.py`
and the extracted opt-in installer in `pilot_nereid.py`.

**Proposed next bounded step, not implemented/authorized:** document the same
lawful actions with per-verb schema/API entries: zero inspection effort,
normalized positive work effort, existing local target handles and eligible
owned percept refs. Add schema/parser parity and captured-failure regressions.
Do not weaken validation, normalize invalid actions into success, expose raw
resolver truth to cognition, force a preferred branch or substitute a model.
Then, only with separate approval, run at most one new batch of the same
6 x 3 x 4 shape (72 calls maximum) in a new directory, preserving this failure.

## F. HUMAN and external presentation gates

The developer can first guide an internal terminal playthrough after offline
and approved neural checks. This is internal user-local evaluation, not the
external visual HUMAN gate.

Before external play, the narrow slice needs its local visual Player View:
focal map, current-place card, lawful visible subjects/objects, personal journal,
contextual actions and clear elapsed time. All data come from the same filtered
projection used by the harness. Creator explanations are separate post-session
views, not hidden tabs of the player's state endpoint.

For an initial narrow-slice HUMAN check, propose three fresh testers without a
formula briefing. After a short session, at least two should be able to:

- name an ordinary change they actually observed;
- suggest a reasonable cause and distinguish observation from conjecture;
- identify one meaningful next action or question;
- understand that the other participant's concern existed independently.

Do not require identifying Nereid as the true cause without evidence, guessing
the silver formula, or choosing the designer's preferred interpretation. If the
world is mechanically correct but its independent activity is unintelligible,
record a presentation/product failure and revise lawful evidence/presentation,
not the hidden answer key. No-Nereid or quiet histories remain valid histories;
their lack of demonstrative activity must be reported honestly.

This small test does not accept the whole ensemble, Nature God, active Death
line, full external Pilot 0.1, or an investor-ready video.

## G. Delivery and status rules

Current verification adds the I3-N runner to the seven baseline commands,
focused positive/negative tests, the frozen internal playable smoke, compilation
and `git diff --check`. Record exact new totals only after running the tests.
Generated evidence goes under `local_acceptance/`, not over frozen artifacts.

Status progression is explicit:

    design draft -> user-approved contract -> N0 feasibility proof
      -> offline interface proof -> approved neural candidate
      -> user-local accepted/frozen (only by explicit user decision)

External visual HUMAN acceptance is a separate later boundary. Never turn
builder verification, an approved design or a model-generated success claim
into an accepted/frozen implementation by inference.
