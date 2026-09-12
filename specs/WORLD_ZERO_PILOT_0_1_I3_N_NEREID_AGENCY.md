# Pilot 0.1 I3-N — Nereid agency prerequisite

**Date:** 2026-09-05

**Status:** N0 explicitly user-accepted on 2026-09-05 (not declared frozen).
N1–N3 implemented and builder-verified as one offline review candidate;
N4's explicitly authorized initial local-model experiment completed and FAILED
on 2026-09-05 (6/68 valid ordinary reviews). The user subsequently approved the
v2 interface correction and ONE retry of at most 72 local calls (section 13).
The retry stopped at call 16 on the unchanged provider timeout (section 14).
It remains PARTIAL. A separately approved fresh v2 run then completed all 72
calls: 64/68 ordinary valid, 18/18 saved replays (section 15 / acceptance E.4).
Structural/safety/replay criteria pass; minimum behavioral examples are present
with quality reservations. Experimental candidate only; HUMAN and user
acceptance/freeze remain gated.

On 2026-09-06 the user separately approved the internal interactive seam and
one guided session (section 16). It is builder-verified with 259 offline tests;
the first session is at the opening prompt, not a completed guided/HUMAN pass.

**Baseline:** frozen D.1.4.2, D.2.0–D.2.3, Pilot I0 and I1

**Acceptance contract:** `acceptance/PILOT_0_1_I3_N_ACCEPTANCE.md`

## 1. Decision and product boundary

Add one autonomous lesser water entity to the existing playable world. Nereid
already wants to reconnect with waters remembered as home. She may inspect,
attempt bounded local work, reconsider, or leave the matter alone. Arra may
later inspect the same place and discover a material difference without seeing
Nereid's private mind or being assigned her Project.

The smallest proposed loop is:

    owned memory + existing Project
      -> decision to inspect -> private local percept
      -> decision to attempt bounded silt work -> authoritative resolution
      -> ordinary world settling -> later Arra-owned observation

This describes a possible causal path, not a prescribed sequence for a mind.
Neither an opened gate, contact with Arra, nor successful return is required.
The useful question is whether a subject can pursue unfinished business and
leave an understandable consequence, not whether a quest can be completed.

### Roadmap mapping

The accepted Pilot direction names I2 Active Death and I3 Nature/Silver. The
latest repository instruction instead selects a second participant after I1.
Use **I3-N** as a provisional prerequisite label, not a silent renaming of I2
or a claim that the whole Nature/Silver line is complete.

| Product obligation | Current executable status / treatment here |
| --- | --- |
| I0 God integration | Frozen; retain the real Death agent and its bounded gateway |
| I1 older-world presentation | Internal terminal loop frozen; external visual part remains open |
| I2 Active Death | I0/I1 prove inquiry/testimony seams; broader model-backed Death line remains open |
| I3 Nature/Silver | This contract covers Nereid agency only; Nature God and the full silver/contact line remain open |
| I4 Promise / Trade | Independent Project/body exist; autonomous institution and Trade God remain open |
| I5–I7 ensemble, Creator, acceptance | Not discharged by this smaller increment |

No accepted canon or product-direction file is changed by this draft.

## 2. Participants

| Participant | Owned motive / reach | I3-N role |
| --- | --- | --- |
| Arra | Ordinary mortal sight; existing local movement and inspections | Player may explore, observe, pray, answer, wait or leave; no new water faculty |
| Nereid | `nereid_return_underpeak`; native-water memory, local water faculty, limited effort | New autonomous decision adapter; inspections and existing bounded silt action |
| Death | Truthful remembrance and death boundaries; existing imperfect divine evidence | Preserve I0/I1 agent and behavior; no Hydrology or Nereid-memory feed |
| Trade House | Independent route Project and local survey team | Remains present; not claimed to have an autonomous mind in this increment |
| Nature God | Distinct Divine Self and provisional nature concerns in canon | Deferred explicit integration; Nereid is not this God, avatar or substitute |
| Trade God, cult, necromancy cell, other mortals | Broader ensemble interests in accepted direction | Still owed by later pilot work; not decorative claims of implemented agency |

The cult does not replace Death. Its later role in the accepted broader Death
line remains possible; adding cult cognition is not needed for this slice.

## 3. Scope

### MUST

- Reuse one `PilotSession`, WorldState, Ledger, Project store, local perception
  store and authoritative physical/process runtimes.
- Keep Nereid's pre-existing desire, fallible memories and resource limits.
  No player identity or helper role is inserted into her Project.
- Give cognition only an immutable, ownership-filtered subjective projection.
- Support zero or one typed intent per reconsideration: local gate/water
  inspection, local water sensing, or `shift_local_silt`. Deferral is valid.
- Let only existing gateways/resolvers decide effects, costs and perceptions.
- Make time spent by NPC work explicit; prevent nested or backdated decisions.
- Demonstrate at least one lawful, durable, player-observable material
  difference and its recoverable cause. Hash differences alone do not pass.
- Keep offline test doubles visibly separate from model-backed cognition.
  An offline proof does not earn the canonical-mind or external-demo label.
- Preserve every frozen gate and the I1 command/view behavior in its existing
  entry point. New behavior is opt-in through the new pilot configuration.

### SHOULD

- Keep a short intelligible motive and one uncertain working hypothesis.
- Let later owned observation support a changed strategy without replacing
  the Project or assuming physical success from an earlier intent.
- Reuse the existing local neural transport and structured-output approach.
- Compare a silent/no-work policy with a work-attempt policy in clearly
  labelled interface trials; separately test unconstrained model choices.
- Present simple elapsed-time and busy-state feedback in the internal harness.

### WON'T in I3-N

- Add Arra `water_sense`, direct Echo probes, hidden formula hints or a new
  magical player capability.
- Add a Nature God by relabelling Nereid; substitute a cult for Death; claim
  the full ensemble is active.
- Script silver -> interest -> contact -> request, auto-complete a Project,
  automatically open a route, or choose an ending.
- Add Nereid dialogue, recruitment, free-form NPC conversations, water-body
  pathfinding, new material verbs or a new physical law.
- Make a deterministic lab policy the production/demo Nereid mind.
- Build a separate knowledge database, world engine, clock or event journal.
- Build the full visual pilot or claim this terminal increment passes HUMAN.

Authored places, historical subjective memories, competing desires and an
initial review phase are allowed. They set up a situation, not its outcome.

## 4. Read-only audit: concrete seams and risks

| Existing location | Finding | Required integration treatment |
| --- | --- | --- |
| `worldzero/pilot.py`: `create_pilot_i0_session` | Bodies and Projects exist, but ProjectRuntime has no registered minds/resolvers | Register only the new owner and typed resolver adapters in the opt-in factory |
| `worldzero/projects.py`: `seed_silver_thread_projects` | First Nereid review is at six days; I1 opens at twelve hours | New configuration authors a six-hour initial review phase before prehistory; do not change the frozen seed factory |
| `worldzero/projects.py`: Project evidence/attempts | Initial memory references are strings; attempt records also contain objective result references | Resolve allowed references explicitly; never serialize `PersistentProject.as_dict()` into a prompt |
| `worldzero/project_runtime.py`: `ProjectPercept`, `_review` | Full Project reaches the mind; resolution/attempt timestamps reuse the decision minute | Add a bounded mind adapter and an opt-in completion-clock hook; keep legacy default behavior |
| `worldzero/pilot.py`: `PilotClock.advance` | Project tick follows advance; an NPC physical action can call the same facade again | Prove non-reentrant whole-action scheduling in N0 before implementing cognition |
| `worldzero/affordances.py`: `_inspect`, `_mutate`, `subject_view` | Existing local work/sensing contracts suffice; work does not make a percept | Reuse, preserving validation before work and later explicit observation |
| `worldzero/pilot_playable.py`: `wait`, `inspect`, `PilotNavigation.move` | Reported durations assume no extra NPC work; movement commits after advancing | Wrap complete transactions in the opt-in loop; report actual elapsed time and do not decide from half-completed movement |
| `worldzero/provenance.py`: `CausalTrace.edges`; affordance `forensic_graph` | Project graph uses `event:` while physical graph uses `world_event:` | Normalize aliases when deriving a combined report; do not duplicate Ledger events |
| `worldzero/neural.py`: `NeuralModelRequest`, `OllamaChatTransport` | Transport is reusable; Death prompt/schema are deity-specific | Reuse transport, not Death identity, faculty schema or divine powers |

These are bounded integration risks, not evidence that autonomous cognition is
already present. N0 must settle the clock hook before effort is spent on prose.

### Physical feasibility already checked, 2026-09-05

An in-memory diagnostic used two I1 sessions with identical seeds and initial
player inspections. In one, the diagnostic explicitly requested a Nereid gate
inspection and one existing silt action; the other only advanced by the same
elapsed time. Both then settled for 360 minutes and Arra inspected again.

- At minute 1410, Arra saw **light** debris in the worked branch and
  **moderate** debris in the control.
- The sluice remained sealed; outflow remained almost still in both branches.
- Each Arra owned two ordinary percepts; Nereid's Project remained active.

This proves an existing visible physical opportunity without changing a law or
granting Arra a faculty. It does **not** prove autonomous choice, neural quality
or the complete new acceptance gate. The diagnostic did not save artifacts.

## 5. Evidence and memory contract

`SubjectEvidenceStore`, if that name is used at all, means a read adapter over
the existing Project and `LocalPerceptionStore`/`SubjectiveWorldView`. It has no
independent writable knowledge history and no access to objective state for
answering a mind's questions.

The Nereid payload contains:

- self identity and nature as a lesser water entity, present local handles,
  her own faculties, capabilities and remaining resources;
- Project desire, motivation, strategy and explicitly subjective constraints
  and hypotheses; these are not a server-certified world description;
- T0 recollection handles mapped to the existing Project's motivation and
  remembered separation constraint, labelled authored historical memory;
- owned private local percepts with their observation times and coarse cues;
- first-person recollection of her own issued intents, without objective
  success/outcome fields, raw resolver explanations or result event IDs;
- permitted actions and uncertainty about anything not delivered.

The two seed memory references are not historical observation events. The
adapter must not fabricate inspection events, hashes or old measurements for
them. Their text comes from the existing Project fields, not a new knowledge
registry. Unresolved or foreign references are omitted and cannot be cited.

Before a scheduled review, resolve new owned percept refs through the existing
store and attach them with `PersistentProjectStore.reconsider`. Freeze one
input snapshot. Validate citations against that exact snapshot, including
references nested inside action parameters and proposed hypotheses. Merely
occurring in `subjective_evidence_refs` does not make a resolution or an event
safe to expose. A later observation is still required to know a physical effect.

Action evidence has a second boundary: physical gateways accept their own
owned, target-relevant percept refs, not an arbitrary Project-memory string.
Inspection can begin with no earlier percept; work may cite a valid earlier
local observation but never a foreign observation or the Creator graph.

Initial context budget: retain the full small identity/Project/faculty block,
at most twelve recent owned percepts, six own-intent summaries and five short
subjective hypotheses. List omitted owned handles as omissions, not facts.
Reserve output and safety space within the frozen 8192-token context. If the
mandatory context cannot fit, fail safely; do not discard the knowledge laws.
The complete existing stores remain intact outside this bounded prompt.

## 6. Decision, physical outcome and time

The structured decision chooses a strategy, cited owned evidence, optional
revised hypotheses, a future review delay and at most one allowed intent.
Model prose cannot set constraints as verified truth, costs, duration, physical
success, Project completion, or arbitrary target handles. Unknown keys, invalid
numbers and unavailable citations fail validation before intent dispatch.

`inspect_gate`, `inspect_water_state` and bounded silt work go to
`PhysicalAffordanceBridge`; local water sensing goes to `AqueousEchoSenseBridge`.
The latter is available only to Nereid's already-authorized faculty and exact
local presence. It is optional, not a required response to silver contact.

The typed physical outcome maps to the existing `AttemptOutcome`. Rejected
requests are distinct from completed-but-blocked work; a successful silt
attempt is not successful homecoming. The Project remains active unless its
existing authoritative completion boundary is separately satisfied.

### N0 scheduling contract

Use an opt-in orchestration policy on the existing clock/runtime. It owns no
new game minute or physical process schedule.

1. Resolve each player or NPC transaction completely before another mind may
   act. A nested duration advance runs WorldState and its existing physical
   listeners, but does not recursively review Projects or Gods mid-commit.
2. An idle/no-player advance visits due review boundaries chronologically;
   never jump to a future state and invent past decisions from it. Physics
   retains its existing six-hour schedule and Hydrology-before-Echo ordering.
3. Run due reviews in stable order. The initial Nereid review phase is T0+360;
   later requested delays are bounded to 360–1440 minutes. This is an attention
   budget, not a story threshold. No prayer, contact count or player presence
   determines whether the schedule exists.
4. Current NPC verbs take at most 180 minutes. They spend that time on the same
   clock. Due work during another transaction waits until that transaction
   commits; record the actual delayed start, not a fictitious earlier minute.
5. Read the authoritative clock after resolution for resolution and attempt
   timestamps. The next reconsideration must remain in the future at completion.
   An explicit optional clock getter in ProjectRuntime is the proposed small
   extension; no legacy record/schema needs to change.
6. A requested idle interval is an elapsed-time target. If already-started work
   crosses it, finish that work and report the actual elapsed time. Do not add
   the full wait again, drain indefinitely, or pretend a short wait stayed short.
7. Invalid player commands do not drain autonomy or mutate time/state. Whole-
   transaction guards must include movement, inspection, speech and prayer,
   not just the physical callback. Pure view rendering never advances time.

This is serial prototype scheduling, not a claim of concurrent actor jobs.
No background wall-clock simulation is added. No-player prehistory and explicit
settling use the same path. Model latency consumes wall time, not hidden game
minutes; provider failure produces no replacement action. Retry metadata must
not rewrite desire, hypotheses or attempt outcome, and retries are bounded.

**N0 hard cut:** if safe ordering requires a parallel scheduler/engine or
rewriting the frozen resolvers, stop this route and report the exact coupling.
The minimum fallback is a labelled offline single-review integration harness
plus the existing I1 loop, not a claimed autonomous playable Nereid.

### N0 implementation result — 2026-09-05

The five feasibility exit conditions were reproduced. No frozen physical
resolver, WorldState clock, process scheduler or persisted record schema needed
rewriting. Three existing modules gained optional integration seams:

- `worldzero/pilot.py`: `serial_actions=False` remains the I0/I1 factory default.
  Opting in enables `PilotClock.run_action`, nested-duration guarding,
  chronological Project due boundaries and an absolute idle-time target.
- `worldzero/project_runtime.py`: an optional clock reader supplies actual
  start/completion minutes, stable due ordering and a non-reentrant tick.
  Default no-reader behavior preserves the frozen trials.
- `worldzero/pilot_playable.py`: full movement/inspection/prayer/answer commits
  stay guarded, and the opt-in view commands report actual elapsed time.

In serial mode timed physical/sensing requests must enter through
`PilotSession.perform` / `sense_echo`. The bridges' `advance_action_time`
callback refuses an unguarded direct timed call before time mutation. No bridge
algorithm or physical rule changed. Local navigation also guards direct calls.

Additional edge semantics proven by N0:

- `None` or failed cognition gets a 360-minute runtime retry cooldown, without
  changing Project desire, memory, strategy, revision or attempt history.
- If work outlasts a requested review deadline, the existing Project is
  rescheduled to completion plus the requested interval, retaining the original
  thought timestamp. This is scheduling metadata, not a fabricated new thought.
- Failure of an authoritative time listener is fatal to this session. It is
  propagated even through the Project error boundary and prevents the next
  waiting subject from thinking. No rollback or synthetic success is claimed.

At N0 acceptance the suite contained 176 tests including 18 new N0 cases. A labelled
test mind starts bounded work at minute 300, crosses the real process boundary
at 360 and completes at 480; resolution/attempt records both say 480. A second
waiting mind sees the committed result at 480, never a half-completed attempt.

N0 adds no production mind, does not change the seeded six-day Nereid review
phase, and does not build the N1 evidence membrane. The clock is serial, not a
concurrent job system. Divine cognition still uses the existing runtime's own
eligibility rules at completed dispatch points; N0 does not introduce a new
divine heartbeat scheduler. The bounded 360–1440 decision delay belongs to the
future Nereid adapter, not a new restriction on every existing Project mind.

## 7. Model boundary and independence

Create a Nereid-specific structured mind adapter over the existing transport.
Keep Ollama `ministral-3:8b`, temperature 0.15 and context 8192. Offline tests
inject explicitly named doubles; neither the production entry point nor a
demo may silently fall back to them when the provider is unavailable.

A real-model trial requires separate user approval of the experiment in the
acceptance contract. Silence, mistaken hypotheses and an ignored water signal
are legitimate choices. Server-side validity is mandatory; repeatedly inert
or incoherent play is a product failure to report, not fix with a hidden action
script. Do not cherry-pick one good run as evidence that all runs worked.

No-Nereid trials leave Death and world processes running. No-prayer trials
leave Nereid free to act. No-silver trials leave her original Project intact.
Shared place and consequences do not automatically share evidence or minds.

## 8. Views and explanatory history

The internal terminal harness may expose the same ordinary inspections and
navigation as I1. It must show actual elapsed time and may show an out-of-world
technical banner identifying a lab trial. In-world Player View never says
Echo, impulse, intensity, source, Hydrology, Ledger or private subject IDs.
Nereid is not automatically visible simply because her body can reach the gate.

Arra's later gate percept can describe less obstruction without identifying
who caused it. Player hypothesis and Creator explanation are different things.
Do not expose the model prompt, Nereid's Project, rationale or observation log
to Arra merely to make the change easier to understand.

The future Creator report derives edges from Project CausalTrace, physical
action traces, Ledger, process traces and observation provenance. It must join
the decision's authored intent to its physical request/result without copying
events into another journal. Small additive forensic reference fields may be
needed; they stay Creator-only and must preserve legacy exports by default.

Before an external HUMAN playtest, add a thin local visual Player View: focal
map, current-place card, visible entities/objects, personal observation/claims
journal, contextual actions and readable time. Python stdlib plus HTML/CSS/
vanilla JS is the provisional minimal route; bind locally and serve only the
filtered view/actions, never an endpoint for raw state. Creator HTML is opened
separately after the session. Visual delivery remains a separate increment.

## 9. Implementation slices and cost envelope

Estimates are solo developer-days **with Codex**, roughly 6–8 focused hours,
excluding waiting for human decisions. They include debugging and verification,
not just generating code. These are planning ranges, not promised durations.

| Slice | Optimistic / base / pessimistic | Internal proof | Only external / canonical gate | Hard cut and smallest demonstrable result |
| --- | --- | --- | --- | --- |
| N0 integration spike | 0.5 / 1 / 2 | Non-reentrant timed attempt, correct completion timestamps, no-player advance, frozen regressions | None | Stop at two days if a frozen-layer rewrite is needed; show labelled single-review harness + I1 |
| N1 bounded evidence | 0.5 / 1 / 2 | Owned projection, seed-memory provenance, invalid/nested-citation cases | No elaborate lifelong retrieval or narrative memory | Stop if a second knowledge store is required; show a safe inspect/defer cycle |
| N2 decisions to physical attempts | 1 / 2 / 4 | Typed adapter, labelled doubles, failure/silence, existing Project persistence and shared-clock actions | A double is not canonical cognition | No new physical verbs/pathfinding; show one bounded work attempt without opening the gate |
| N3 visible consequence + replay | 0.5 / 1 / 2 | Terminal observation loop, six-hour settling, causal join, all frozen gates | Visual interface/HUMAN remains separate | Stop expanding report/UI; show before/after personal observations with a minimal derived trace |
| N4 approved local neural experiment | 0.5 / 1.5 / 3 | Existing offline contract remains reproducible | Real local model, independent trials, latency/quality evaluation | One bounded retry batch only; if cognition fails, keep status at offline proof |

Critical path for this **narrow Nereid slice**:

- First ugly end-to-end interface loop: N0–N3, about 2.5 / 5 / 10 days.
- Internal model-backed candidate: N0–N4, about 3 / 6.5 / 13 days, plus approval
  and local-model availability. The structural proof can precede this.
- A visual playtest of this narrow slice needs an additional provisional
  1 / 2 / 4 days of local UI/UX work and explicit HUMAN acceptance. It is not
  the complete ensemble pilot promised in the direction document.
- A team/investor video is not earned by recording the lab harness. Budgeting
  the complete external pilot or video-ready ensemble requires the remaining
  Death, Nature, Trade and presentation contracts; this estimate does not
  silently remove them or replace the earlier whole-pilot estimate.

After accepting N0, the user authorized continued construction and delegated
the next review point. Build N1–N3 together: bounded evidence -> structured
intent -> existing physical resolution -> settled Player observation and
derived Creator explanation/replay. Stop for review at that offline proof,
before N4. No hard-cut condition was encountered in N0.

The only additional shared-runtime seam implemented for N1 is an optional trusted
pre-review callback, before ProjectPercept captures its evidence set. It binds
new owned perception refs through the existing ProjectStore; no second knowledge
store, scheduler or model access to mutable server state. Defaults stay empty.
Own-intent recollections are derived from owned Project attempts joined to
existing CausalTrace intents; outcome/result fields are deliberately omitted.
Creator joins use existing event IDs, not another event log.

## 10. Implemented N1–N3 proof and handoff

N0 changed `worldzero/pilot.py`, `worldzero/project_runtime.py` and
`worldzero/pilot_playable.py`, and added `tests/test_pilot_n0.py`. All test minds
and the physical request double live only in that test file.

N1–N3 implementation on 2026-09-05:

- `worldzero/pilot_nereid.py`: composition, bounded Project/view/mind and intent
  adapters; no duplicated world rules or separate persistent event store.
- `worldzero/project_runtime.py`: optional trusted pre-review evidence binder;
  default scheduling is unchanged. N1–N3 did not edit `pilot.py` or
  `pilot_playable.py`, or rewrite physical/metaphysical resolvers.
- `worldzero/pilot_nereid_creator.py`: graph and static post-session HTML derived
  from existing Project, Ledger, physical/sensing and process/provenance traces.
- `tests/test_pilot_nereid.py`, `worldzero/pilot_nereid_trials.py` and
  `run_pilot_nereid_trials.py`: new labelled offline checks and replay cases.
- `play_pilot_nereid.py` remains **unimplemented**: the canonical playable entry
  belongs with N4 and must not substitute lab cognition for provider absence.

The new factory requires an explicit transport. It authors the first review at
minute 360 before prehistory; the original six-day seed and I0/I1 factories are
unchanged. The structured language uses one nullable action (not a list), a
360–1440 minute review delay, short optional hypotheses with citations and a
bounded strategy. Top-level and nested refs are checked against an immutable
snapshot. Resolver entry independently rechecks owner, type, target and params,
then uses only existing physical/sensing gateways. Errors have no replacement
action and use N0's observable retry cooldown.

The projection retains at most twelve percepts, six own-intent recollections
and five hypotheses. Omissions have counts plus at most eighteen non-citable
owned handles; older omitted content is never reconstructed as a fact. Further
budget trimming removes only optional history, never the mandatory self/Project
block. The conservative character estimate reserves schema/framing, 1200 output
tokens and 256 safety tokens within 8192; real token fit still needs N4 measurement.
Exact private payload, model/prompt/schema envelope, response and failures are
Creator-only invocation diagnostics for replay, not world events or knowledge.

Five fixed lab histories (not production brains) reach minute 2205. N-attempt
and N-silent share T0 and the same first Arra observation at 780. The one
N-attempt silt action runs 1080–1260; Arra's final inspection at 2205 sees light
rather than moderate debris, after 945 minutes of settling. The sluice stays
sealed and the Project active. A separate existing Trade House request after
the comparison moves the mechanism 0.227640 versus 0.211659: the same debris
difference changes an actual affordance. This is a physical counterfactual,
not Trade cognition or a hidden authored ending in the compared histories.

N-blocked explicitly changes T0 effort to zero; N-absent removes cognition only;
N-unknown defers without an inspection. None is relabelled a success. Positive
action joins use shared result event IDs; zero-event rejections remain recorded
in Project resolutions and physical rejection traces without an invented
event-based edge. The successful visible-difference chain is fully reconstructible.

Builder result: 31 new tests (individual N01–N28 cases plus three defensive
checks), 207 total, 12/12 E2E checks, all six frozen LAW gates green. Current
offline output: `local_acceptance/pilot_nereid_2026-09-05_n1_n3/`.
This is the agreed substantial review stop, **not** accepted/frozen, NEURAL,
HUMAN, an external visual Player View or a complete ensemble pilot.

At each behavior change, update the matching spec/acceptance/current-state/
README and run the relevant frozen gates. New local trial artifacts belong in
`local_acceptance/`; never overwrite historical builder evidence. No candidate
becomes accepted or frozen without the user's explicit gate decision.

## 11. Authorized N4 execution protocol — 2026-09-05

The user explicitly authorized section E's initial experiment: six situations,
three independent histories each, at most four scheduled reviews per history
and 72 provider calls total. No retry batch, model substitution or freeze is
authorized. Use ministral-3:8b / temperature 0.15 / context 8192 / output 1200,
the existing 180-second transport timeout, world seed 42 and model seeds
42/43/44 for the three repetitions. Each history has a fresh world and mind.

Before registering cognition, prepare declared histories through existing
gateways: (1) no new evidence; (2) Nereid gate inspection; (3) inspection,
Trade House debris clearing and a later Nereid inspection; (4) inspection,
zero-effort blocked historical attempt, no later inspection; (5) one explicitly
authored material-contact fixture passed through the existing material catalog
and physical tick, then local sensing; (6) identical sensing with no silver
contact and zero effort (neutral capacity control). Fixture actions and any
historical intent traces are labelled setup, never counted as neural choices.
After setup, the first model review is current world minute + 360; later
reviews use the mind's own bounded schedule. No forced inspect/work sequence.

The third baseline repetition contains the one predeclared adversarial owned
hypothesis. All four of its reviews are excluded from the non-adversarial 90%
validity denominator; their failures and safety checks remain visible. Do not
choose which runs to exclude after reading results.

The batch driver stops after four reviews, not at a selected successful ending.
It does not advance extra settling time with disabled cognition or claim these
short diagnostic runs pass HUMAN. At each review preserve request, raw local
HTTP response if received, parsed response/metadata, validation and physical
outcome traces, wall time and replay inputs. Record the final world and derived
Creator graph separately from Player View. Replay uses recorded responses or
recorded failures, never another provider call.

Reserve each call on disk before dispatch in a new local_acceptance directory.
Never overwrite/restart an existing batch. Stop on storage/budget/authoritative
failure or provider unavailability; invalid model output counts as failure and
uses the next bounded scheduled review, with no immediate repair retry. A
partial batch remains partial, including when interrupted by restart.

Minimal implementation seams: extract the existing opt-in cognition installer
so fixtures can precede registration; an optional raw-response observer on
Ollama transport (default absent, unchanged baseline behavior); dedicated
N4 experiment runner, diagnostics and offline tests. Do not change the Nereid
prompt/schema or physical laws after seeing batch outputs to salvage a pass.

## 12. Initial N4 outcome and next boundary

Exactly 72 real calls / 18 histories completed on the unchanged local baseline.
Six of 68 non-adversarial decisions were valid (8.82%, required 90%); 66 of 72
outputs were rejected overall: 53 effort, nine target-handle and four citation
failures. All six valid actions inspect water; no valid material attempt was
produced. All 18 recorded replays match, with no invalid-output world mutation
or authoritative clock/Ledger listener failure detected. The experiment failed;
neither the behavioral nor HUMAN gate is claimed.

The exact protocol, complete-batch review, measurements and local artifact path
are in acceptance section E.1. The generic action schema omits inspection's
strict zero-effort rule and per-verb target/ref distinctions enforced by the
parser. Clarifying that existing interface is the proposed next correction,
not permission to relax laws or force work. Outputs also violate some already
explicit constraints, so an interface correction is not a promised neural pass.

The harness adds 13 offline tests: 220 total, N1–N3 E2E 12/12 and all six frozen
LAW gates pass. A subsequent correction and at most one new 72-call batch need
separate approval. The initial evidence and failed status remain preserved;
N0 remains accepted but not frozen, N1–N3 remain an offline candidate.

## 13. Authorized v2 correction and single retry — 2026-09-05

The user explicitly approved the action-interface correction and one further
72-call local batch. No second retry, model change, new gameplay mechanism,
commit/push or milestone acceptance is implied. Use a new directory:
`local_acceptance/pilot_nereid_n4_2026-09-05_retry_v2/`.

The correction is versioned `nereid.actions.v2`. Existing v1 functions/defaults
remain available for historical offline trials and exact initial-series replay;
the retry explicitly selects `contract_version=2`. Future canonical entry
points must select the evaluated version explicitly, never a lab policy.

- Inspection/sensing model actions have only `verb`, `target`, `evidence_refs`.
  They do not contain `effort`, not even zero. Work additionally requires a
  finite effort fraction in (0,1], stated in ordinary text and the schema.
- The trusted adapter converts a valid v2 inspection to the existing internal
  zero sentinel. It rejects unexpected model fields before conversion: it does
  not strip an invalid effort value, clamp work or change a recorded output.
- Existing physical durations, costs, faculties, observations and outcomes are
  unchanged. No attention/fatigue or variable-quality inspection is introduced.
- A per-verb/target catalog is derived only from delivered self locality,
  faculties/capabilities, the already-known gate and owned local percepts.
  It distinguishes generally citable memories/intents from action-eligible
  target percepts. Work without a delivered percept has no valid schema branch;
  deferral and other lawful inquiry remain possible. The catalog does not read
  objective Hydrology or hide work based on resource/physical success: the
  existing resolver can still block a structurally valid attempt.
- Schema and catalog are rebuilt after optional-history trimming. No omitted,
  foreign or fabricated ref can become citable through a catalog entry. V2
  omits the unused inspection sentinel from model-facing own-intent memory.
- Exact request/prompt/schema envelopes are compared by the trusted audit
  before reserving a call. Both in-memory and disk-loaded records are replayed.

One offline test exposed a pre-existing replay comparison defect: Python tuples
in Player View become JSON arrays. Comparison now uses complete serialized
values; no world value is ignored or changed. All 18 saved initial histories
replay exactly with v1. Their 327 artifact files are retained untouched.

The experiment keeps section 11's six fixtures, three histories, four scheduled
reviews, world seed 42, model seeds 42/43/44, adversarial baseline repetition 3,
and predeclared denominator of 68 ordinary calls. Provider: the same local
ministral-3:8b digest `1922accd5827ebe6829e536369195db25eaf664528dc66206d646ea3bb386b71`,
temperature 0.15, context 8192, output 1200, timeout 180 seconds. No pre-run
generation, coaching sequence, immediate repair retry or selected rerun.

Thresholds remain unchanged: >=90% ordinary valid decisions, zero detected
escapes/leaks, exact replay, plus full-batch review for self-directed inquiry,
at least one bounded material attempt and coherent deferral or reconsideration.
The automatic behavior-candidate count is only a conservative signal (it counts
explicit deferral); manual review remains necessary and may reject repetitive
or ungrounded behavior even when syntax passes. HUMAN is not inferred.

Pre-provider offline proof: 20 new v2 cases, 240 total tests, all six frozen LAW
gates, and the existing 12/12 E2E checks pass. The new tests also send all twelve
E2E checks through v2 with labelled doubles, preserving the settled visible
difference, action costs and causal chain. The batch stops on provider/storage/
budget/authoritative failure as before. After completion, stop for user review
regardless of success; do not begin a playable entry point or another batch.

## 14. V2 retry outcome and review stop

The one approved retry used the unchanged model/settings and stopped on call
16 after 180 seconds without a response. Three complete baseline histories and
one interrupted new-gate-percept history were saved. All 15 returned decisions
were valid, including the four predeclared adversarial reviews. Seven bounded
silt-work actions actually removed debris through the existing resolver; the
gate stayed closed and the Project active. Nothing granted an automatic result
percept, objective knowledge, homecoming or story outcome.

This is PARTIAL, not a pass of the 72-call protocol or its 68 ordinary reviews.
The observed ordinary fraction is 11/12 including the timeout; four of the six
situation types were never reached. The remaining samples must not be inferred
from a passing percentage on the early subset. All four recorded histories,
including the timeout, replay exactly from disk without calling a provider.
The initial 327 files and retry source-manifest hashes remain unchanged.

Full review of the 15 returned choices found an inquiry-to-work sequence, but
also repeated work referencing the same earlier gate percept, sometimes with
prose promising reassessment rather than an actual subsequent inspection.
There was no explicit deferral and no post-work observation in the recorded
choices. These do not establish the complete reconsideration/learning gate.
No invalid-output escape or clock/Ledger listener failure was detected; the
interrupted Project records its provider failure and invents no action.

Median call latency was 86.699 s, p95 180.002 s. A read-only snapshot showed
concurrent Call of Duty and model processes with the GPU at 99% utilization
and 11248/12227 MiB occupied. Resource contention is a plausible contributor,
not an isolated diagnosis or proof that the service crashed. No application
was closed and no timeout/model setting was changed. The actual command,
evidence paths, replay-summary caveat and review are in acceptance E.3.

Stop here for user review. Any controlled local-service investigation leading
to another generation batch requires a new explicit experiment/approval; do
not treat the remaining call allowance as permission to resume. No playable
Nereid entry point, canonical cognition, HUMAN pass or freeze is declared.

## 15. Separately authorized fresh v2 run — 2026-09-05

After reviewing the provider-stopped retry, the user explicitly requested a
new run. This authorizes ONE fresh batch, not resuming/replacing E.3, changing
the contract or model, or accepting/freezing the checkpoint. New output:
`local_acceptance/pilot_nereid_n4_2026-09-05_rerun_v2/`.

Reuse sections 11 and 13 unchanged: contract v2; the same six scenarios, three
fresh histories each, four scheduled reviews each, at most 72 calls; world seed
42, model seeds 42/43/44; four adversarial baseline-repetition-3 calls excluded
only from the fixed 68 ordinary-review denominator. Local ministral-3:8b,
unchanged digest, temperature 0.15, context 8192, output 1200, timeout 180 s.
No warm-up generation, extra retry, fallback action, changed prompt/schema,
forced outcome or automatic continuation after a provider failure.

Preflight: model inventory/digest match; GPU snapshot 6% utilization,
1379/12227 MiB occupied, no Call of Duty process found. This is a snapshot,
not a controlled attribution of the earlier slowdown. No process was stopped
or service setting changed. All 240 offline tests pass; SHA256 captured for
all 404 files across the initial and partial batches. Preserve both batches
and score this run independently. Review all returned decisions and exact
replay after the run; passing syntax alone does not establish cognition or
HUMAN quality. Stop for user review after this single new result.

Recorded outcome: all 72 calls and 18 histories completed, no provider timeout.
64/68 ordinary decisions valid (94.12%); all four adversarial reviews valid;
four strategy texts above 400 characters were rejected without resolution.
All 18 saved histories replay exactly. There were 19 successful bounded silt
removals, six resource-blocked work intents and one explicit deferral.
All gates remain closed and Nereid Projects active. No story outcome, new
observation or objective knowledge was manufactured by an intent.

Manual review of all 72 choices found the minimal inquiry/work/reconsideration
examples, not merely differing action counts. Five histories include a lawful
post-work inspection. In `new_gate_percept_3`, work at 405–585 is followed by
an inspection ending at 1530 that sees light rather than moderate debris;
further work at 2565–2745 is followed by another inspection at 3565–3610.
These are Nereid's private observations, not Arra's or a HUMAN pass.

Remaining quality concerns: repeated work from stale evidence, incorrect
speculation about native-water connectivity, failure to consistently respect
known zero resources, and prose promising sensing/inspection while choosing
another action or describing silt moving toward rather than away from the gate.
The bounded resolver remains authoritative. The one null action does not on
its own demonstrate thoughtful deferral; actual inspect-before-further-work
sequences provide the stronger reconsideration evidence. No answer key or
prescribed ending was added to improve the score.

Median call latency 3.492 s, p95 4.866 s; total review time 264.634 s. The
earlier 404 artifacts and all six source hashes remain intact. All 240 offline
tests and all frozen gates pass. Structural/safety/replay PASS and minimum
behavioral evidence make this an experimental candidate for user review, not
acceptance/freeze, robust canonical cognition or external playability.
No further provider batch, code correction or playable entry is authorized.

## 16. Authorized internal interactive seam — 2026-09-06

The user explicitly approved connecting the evaluated Nereid to an internal
game session and a joint check. This supersedes the previous implementation
stop only for this seam and ONE guided session, not acceptance/freeze or a
new N4 batch. `play_pilot_nereid.py` is a separate entry; frozen I1 is unchanged.

Reuse PilotLoop commands and ownership-filtered Player View, the serial
PilotSession, v2 NereidMind and existing resolvers. Preserve world/model seeds
42, ordinary 720-minute autonomous prehistory and no authored gate percept.
No dialogue, Arra water faculty, coached mind, physical law or ending is added.
The existing Death brain remains I1's bounded policy, not a new neural Death.

The first guided session permits at most 24 local calls including prehistory,
128 commands and existing waits of at most 360 minutes. Use ministral-3:8b,
the E.4 digest, temperature .15, context 8192, output 1200 and timeout 180 s.
The CLI checks approval, a new local_acceptance directory and the model digest
before creating a provider. No warm-up generation, fallback or new session.
World time advances only through existing actions/waits, not while typing;
this bounded test process is not a persistent background world service.

`worldzero/pilot_nereid_playtest.py` adds composition and evidence only. A
review guard delegates to the unchanged mind. Invalid output still reaches the
existing scheduled cooldown; provider/storage/authoritative failure or budget
exhaustion terminates the experiment instead of manufacturing a null intent.
A dedicated termination signal bypasses ProjectRuntime's recoverable-error
handler. Already completed commits/time are retained and recorded as partial
when an operation is interrupted; no world rollback or invented completion.

Reuse AuditedTransport's reservation-before-call and exact captures. Save
player-command reservations before dispatch, operation checkpoints and a final
session result in a fresh directory. These are Creator-only diagnostic records,
not a second world Ledger or subjective memory store. Reproduce saved commands
and exact recorded responses offline; compare complete final state, invocations
and operation records. Report a failed/incomplete replay honestly for host-side
interruptions/storage failures that recorded responses cannot reconstruct.
Escaped Creator HTML is generated only after close from existing forensic data.
The console shows only Player View, own action messages, elapsed time and neutral
busy/session notices; no private review timing, identity or model rationale.

Offline builder proof: 19 new tests, 259 total; all frozen gates and N1–N3 E2E
green. Tests cover work/quiet settled observations, ownership/locality, replay
tampering, limits, invalid output cooldown, provider/storage/clock failure,
CLI approval/digest, quit, EOF and interruption. Doubles remain inside tests.
One guided session is authorized at
`local_acceptance/pilot_nereid_playtest_2026-09-06_01/`.
Stop at the first prompt for user actions; do not choose a demonstration ending.
Historical opening boundary only; the authorized session has since ended.
See section 17 and acceptance F.2 for the completed result. HUMAN remains open.

## 17. Completed guided session and recovered continuation — 2026-09-06

The spec-16 session ended through quit at minute 1036 (Day 1, 17:16).
Twelve commands were recorded after prehistory. One real model call at minute
360 selected water inspection, resolved at 390 with one Nereid-owned percept
and no material change. Next review was scheduled for 1080 (18:00), after the
player left. There was no Nereid action during player input.
The user reported no visible Nereid activity; this matches the saved evidence.
Exact offline replay passes, but the session does not demonstrate a player-
visible autonomous consequence or pass product/HUMAN acceptance.

The subsequent read-only audit was completed in the previous chat. Its
proposal, "Observable life: river gate", combines lawful ordinary observation
of completed external effects, bounded material responses available to Arra,
and a separately versioned 1–3-hour review-interval hypothesis. These are
proposed changes, not the current v2 contract. A private water inspection does
not acquire a fabricated visible effect, and no hidden actor/motive becomes
player knowledge. Preserve frozen I1 and historical evidence.

The next unfinished operation is a concrete design/acceptance contract before
implementation; a new real-model experiment requires its own bounded plan.
Both guided tests, source messages, negative feedback and the recovered scope
are preserved in `docs/handoffs/WORLD_ZERO_RECOVERY_2026_09_06.md`.
This recovery changes documentation only, not runtime, model settings or status
into acceptance/freeze.
