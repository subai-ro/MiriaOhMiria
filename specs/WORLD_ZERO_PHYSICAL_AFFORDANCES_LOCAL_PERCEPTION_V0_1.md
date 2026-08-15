# WORLD ZERO — PHYSICAL AFFORDANCES + LOCAL PERCEPTION v0.1

**Checkpoint:** V0.0-D.2.2  
**Construction boundary:** Silver Thread P4  
**Status:** implemented and acceptance-tested  
**Depends on:** frozen D.1.4.2 epistemic kernel, D.2.0 PersistentProject, D.2.1 Hydrology

---

# 0. Purpose

P3 proved that a shared physical world can change without a player and can
authoritatively reject a Project attempt. It did not yet provide a safe way for
a causal subject to inspect or change that world.

P4 implements the missing loop:

```text
local perception
→ subject chooses a bounded request
→ authoritative resolver
→ shared physical state
→ later local perception
```

This is not yet canonical cognition. It is the production interface that a
future neural Nereid, institution, mortal or other entity can use without
receiving direct access to objective server state.

---

# 1. Governing laws

1. A mind may receive only a `SubjectiveWorldView`, never `HydrologyState`.
2. A subject must be locally present at an action or observation site.
3. Cited percepts are private evidence and cannot be borrowed across subjects.
4. A resolver checks capability and resources before changing time or state.
5. Accepted physical work consumes ordinary world time.
6. Hydrology, not action prose, determines downstream water consequences.
7. Physical change does not automatically create knowledge.
8. A later observation contains qualitative cues, not the server answer key.
9. Objective events and private percepts remain distinct records.
10. Exact forensic data is available to Creator View but not to the subject.
11. An affordance never completes a quest or Project by story convention.
12. A lesser entity's local influence is bounded by the same resolver contract.

---

# 2. Server-side subject body

`LocalSubjectState` describes available local agency rather than cognition:

```text
subject_id
subject_kind
present_site_ids[]
faculties[]
capability_levels{}
resources{}
```

It answers questions such as:

- where can this subject currently perceive or touch the world?
- what kind of body, tool or local influence does it possess?
- how skilled is it at a particular physical verb?
- what effort or material stock is locally available?

It does not contain:

- beliefs;
- Projects;
- desired outcomes;
- hidden world facts;
- a decision policy.

Registering a body therefore does not wake a mind or cause an action.

Seed-time P4 registers conservative local agency for:

- `nereid_01`: northern water presence and upstream Gate forebay access,
  water sense, remembered-water faculty and bounded silt influence;
- `trade_house_01`: an upstream engineering field team able to inspect and work
  on the Gate but not magically occupy the sealed Gallery or hidden bank.

---

# 3. Subject-facing view

`SubjectiveWorldView` contains only:

```text
subject_id
game_minute
present_site_ids[]
faculties[]
capability_levels{}
resources{}
private SubjectivePercepts[]
```

Each `SubjectivePercept` contains:

```text
percept_ref
time
observer
observation type
known target
local site
qualitative cues
summary
certainty class
```

The subject-facing object does not contain:

```text
sluice_position
debris_load
structure_integrity
effective_opening
gate_discharge
aquatic_route_viable
burial_shelf
hydrology_tick
state_hash
```

Exact self-owned resources and capabilities are allowed: knowing one's own
available labour or material is not omniscience about the world.

---

# 4. Local observation vocabulary

## `inspect_gate`

Possible coarse cues include:

- visible sluice: `sealed / slightly_raised / partly_open / wide_open`;
- visible debris: `clear / light / moderate / heavy`;
- mechanism: `fragile / worn / weathered / sound`;
- outflow: `almost_still / weak / steady / strong / violent`.

## `inspect_water_state`

Possible cues include:

- visible level band;
- felt current band;
- a remembered-signature comparison only when the observer actually has that
  faculty.

The signature cue is still subjective recognition. It is not the node's hidden
tag table.

## `survey_gallery`

Possible cues include:

- visible rubble band;
- visible wetness band;
- route impression.

The impression may be wrong at boundaries and never supplies the hydraulic
formula.

## `inspect_bank`

Possible cues include:

- visible stability/scour;
- ordinary surface signs;
- unidentified fragments only if material is physically visible.

The observation never exposes the hidden object ID `underpeak_burial_shelf`.

---

# 5. Observation is not objective truth delivery

An inspection is an objective action, so the Ledger records that it occurred:

```text
LOCAL_INSPECTION_PERFORMED
```

The Ledger event stores the observer, known target, place, time and inspection
method. It deliberately does not store the private cue payload.

The private perception store separately records what that subject perceived.

Creator-only `ObservationProvenance` records:

```text
percept_ref
inspection_event_id
source_state_hash
source_hydrology_tick_ref
objective_source_event_ids[]
```

The separation prevents three invalid equivalences:

```text
the server knows X
≠ someone observed X
≠ an observer interpreted X correctly
```

---

# 6. Physical action vocabulary

## Gate

### `adjust_sluice(delta)`

Normal movement is limited by:

- requested direction and distance;
- actor skill and effort;
- visible or hidden debris resistance;
- structure condition;
- remaining mechanical travel.

The result may be `succeeded`, `partial` or `blocked`.

### `clear_gate_debris(effort)`

Removes a bounded amount of the current obstruction. It does not move the
sluice or set discharge.

### `force_sluice(delta)`

Can obtain greater movement but also damages structural integrity. The damage
persists and can later create leakage even if the sluice is nominally closed.

### `repair_gate(effort, materials)`

Restores bounded structural integrity and consumes both effort and materials.

## Gallery

### `clear_gallery_rubble(effort)`

Changes physical obstruction. The route remains derived from rubble plus water
state; clearing rubble does not declare the Gallery passable.

## Bank

### `reinforce_bank(effort, materials)`

Reduces sediment mobility at the visible reach. The worker does not need to
know what, if anything, is hidden inside the bank.

## Lesser water entity

### `shift_local_silt(effort)`

Moves only a small bounded amount of local Gate debris. It cannot:

- set `q_gate`;
- set `aquatic_route_viable`;
- move the sluice;
- teleport the entity through the Gate;
- reveal hidden state;
- complete a Project.

---

# 7. Locality, capability and evidence checks

For every request the bridge checks, in order:

1. known subject;
2. valid typed target for the requested verb;
3. target site inside current local presence;
4. non-zero capability for the verb;
5. ownership of every cited private percept;
6. relevance of cited evidence to the target;
7. parameter validity;
8. sufficient local effort/materials.

Failure before physical work is atomic:

- no world-time advance;
- no Ledger event claiming an action occurred;
- no resource loss;
- no Hydrology mutation.

The rejected request remains in Creator-facing action trace as a rejected
attempt, but is not rewritten as an objective world event.

---

# 8. Time and physical consequence

Each accepted verb has a deterministic prototype duration. The bridge advances
the same `WorldState` clock used by `WorldProcessRuntime`.

Therefore an eight-hour repair naturally crosses one or more six-hour
Hydrology boundaries. Physics is neither paused nor run in a separate story
clock.

The action event is recorded at completion and becomes the causal action ID for
the mutated Hydrology subsystem. Later process traces and threshold events can
retain that provenance.

No action directly sets:

- Gallery route state;
- aquatic passage viability;
- lake bands;
- burial exposure;
- Underpeak narrative access;
- a Project lifecycle state.

---

# 9. Counterfactual proofs

P4 contains three particularly load-bearing counterfactuals.

## Private evidence isolation

Trade tries to use Nereid's gate percept. The request is rejected without time
or state change.

## Cross-subject affordance creation

Two otherwise identical branches perform the same Trade adjustment. In one,
Nereid previously shifted a bounded amount of silt. The later Trade action
achieves more physical movement because resistance is lower.

Nereid does not control Trade and does not author the result. Her action merely
changed the affordance another subject later encountered.

## Hidden-site protection without hidden-site knowledge

Two branches share the same inspection time, high Gate regime and 30-day
Hydrology history. In one, a crew reinforces an apparently ordinary eroding
bank. In the other it does not.

The reinforced branch keeps the hidden burial covered; the unreinforced branch
exposes it. The crew's percept contains no burial, tomb or remains reference.

This proves that an actor can create a consequential historical difference for
a reason unrelated to the hidden story meaning.

---

# 10. Acceptance gates

P4 acceptance has **26 LAW checks** covering:

- locality;
- qualitative perception;
- private-evidence isolation;
- Ledger/percept separation;
- bounded lesser-entity influence;
- no automatic observation;
- resource atomicity;
- partial mechanical outcomes;
- action → Hydrology provenance;
- two-tick route validation;
- no quest/passage automation;
- cross-subject affordance creation;
- deterministic replay;
- hidden-site counterfactual;
- raw-event perceptual barriers;
- fixed-clock integration;
- complete objective action recording.

The complete offline suite is **119/119** at D.2.2.

---

# 11. Explicit non-goals

P4 does not add:

- canonical neural Nereid cognition;
- autonomous Trade House policy;
- passive witness/report networks;
- hidden silver-water echo;
- Nereid contact with Arra;
- full local movement/pathfinding;
- realistic engineering simulation;
- a separate Gallery drain-integrity model;
- a quest system;
- a story director.

The deterministic lab policies prove the interface only. They must not be
mistaken for the subjects' final minds.

---

# 12. Next boundary

The old Silver Thread draft placed hidden silver-water metaphysics immediately
after Hydrology. P4 inserted the missing safe perception/action prerequisite.

The next construction step is **P4-B: aqueous silver echo**:

```text
ordinary silver-water contact
→ deterministic decaying/propagating field
→ local perceivable phenomenon
→ no automatic interest, contact or quest
```

Only after that law is accepted should **P5 canonical Nereid cognition** be
connected to `SubjectiveWorldView` and the physical request schema.

---

# Final formula

P4 is not:

> the server tells Nereid that the Gate is blocked, and she opens it.

It is:

> **A local subject sees only signs, spends real time and capability on one
> bounded attempt, the world resolves what physically changed, and the subject
> must look again to learn even part of what followed.**
