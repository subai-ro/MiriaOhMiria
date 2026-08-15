# WORLD ZERO — AQUEOUS SILVER ECHO v0.1

**Checkpoint:** V0.0-D.2.3  
**Construction boundary:** Silver Thread P4-B  
**Status:** implemented candidate; requires recipient-machine acceptance  
**Depends on:** frozen D.1.4.2 epistemic kernel, D.2.0 PersistentProject,
D.2.1 Hydrology, D.2.2 Physical Affordances + Local Perception

---

# 0. Purpose

P4-B implements one small true law of Hidden Metaphysics:

> Silver in natural water creates a weak transient aqueous echo. The echo
> decays and follows sufficiently connected water. A locally present subject
> with an appropriate water faculty may perceive it imperfectly.

The law creates an opportunity for later cognition. It does not itself create
attention, entity interest, contact, a request, a Project or a quest.

---

# 1. Governing laws

1. Gameplay verbs record physical contacts; hidden metaphysics reads a general
   contact schema rather than a verb name.
2. Item composition is authoritative object data and contains no narrative
   recipient.
3. Silver response depends continuously on contact units and silver fraction.
4. Repetition accumulates physical impulse; no event-count story threshold
   exists.
5. Existing echo decays at every fixed process boundary.
6. Echo transport uses flows from the same-boundary authoritative Hydrology
   tick.
7. An edge below the connected-flow threshold transports no echo.
8. Boundary loss, spill and propagation attenuation are explicit.
9. Hidden objective state is not subjective knowledge.
10. Raw threshold transitions carry a `raw_world_process_state` perceptual
    barrier.
11. Sensing requires exact local presence and an appropriate faculty.
12. A sensed result is coarse and source-ambiguous; exact field values and the
    hidden formula remain server-side.
13. Private percept ownership is enforced.
14. The process never mutates a Project or creates attention/contact/request/
    quest state.
15. Identical material, water and sensing histories are deterministic.

---

# 2. General material-medium contact contract

The event-embedded schema is `material_medium_contact.v1`:

```text
schema
medium_kind
medium_ref
contact_item_id
contact_units
material_fractions{}
```

Example:

```json
{
  "schema": "material_medium_contact.v1",
  "medium_kind": "water",
  "medium_ref": "lake_mirror",
  "contact_item_id": "silver_rod",
  "contact_units": 0.6,
  "material_fractions": {
    "hardwood": 0.075,
    "silver": 0.925
  }
}
```

`MaterialCatalog` owns profiles. `WorldEngine._fish()` records one contact for
the selected tool. Future physical verbs may embed the same schema.

The echo process scans new Ledger events for the schema. It does not branch on:

```text
FISHED
silver_rod
Arra
Nereid
number of fishing actions
```

It responds only to a valid water contact whose composition contains silver.

---

# 3. Objective state

`AqueousEchoState` contains only:

```text
node_amounts{}
band_states{}
```

Its node set must exactly equal the seven focal Hydrology nodes. Amounts are
finite and non-negative. Creator-facing bands use the fixed vocabulary:

```text
silent
faint
clear
strong
```

The state contains no subject, actor, entity, motivation, interpretation,
Project or narrative output slot.

---

# 4. Fixed-clock update

Both processes tick every six hours. `WorldProcessRuntime` orders the current
production IDs so that one boundary is:

```text
silver_thread_hydrology
silver_thread_water_echo
```

The echo process refuses to tick unless the Hydrology process has already
produced a trace for that exact game minute.

For node `n`:

```text
decayed[n] = previous[n] × 0.82

impulse[n] = Σ(
    contact_units
    × silver_fraction
    × 0.052
)

pre_transport[n] = decayed[n] + impulse[n]
```

These prototype constants are fixed simulation parameters, not facts delivered
to any subject.

---

# 5. Flow-dependent transport

Transport consumes the actual edge flows recorded by the same Hydrology tick,
including ordinary lake/junction edges, Gate discharge, backwater, inundation
and Gallery drainage.

For each source node:

```text
path_weight = flow / max(post_tick_storage, 0.05)

export_fraction = min(
    0.58,
    3.0 × Σ(path_weight)
)
```

A path participates only when:

```text
flow >= 0.003
```

Exports are distributed by relative path weight. Internal deliveries retain
`0.90` of exported echo; the rest is explicit transmission loss. Boundary
outflow and spill are explicit full losses.

The tick asserts:

```text
final total
= decayed total
 + impulse total
 - boundary losses
 - transmission losses
```

within `1e-10`.

The mechanism is deterministic and intentionally small. It proves physical
connectivity and path dependence; it is not a claim to model real-world
chemistry or folklore.

---

# 6. Threshold events are not perceptions

When a node changes qualitative band, the process may append:

```text
AQUEOUS_ECHO_BAND_CROSSED
```

This is an objective Creator/forensic transition with:

```text
actor_ids = ()
publicity = 0
secrecy = 1
perceptual barrier = raw_world_process_state
```

It does not append a `SubjectivePercept`, wake Nereid, or route a hidden answer
to a God.

---

# 7. Local sensing bridge

`AqueousEchoSenseBridge` shares the D.2.2 `LocalPerceptionStore` and therefore
feeds the already safe `SubjectiveWorldView` seam.

A request is:

```text
subject_id
water_node_id
```

The bridge rejects atomically unless:

- the subject exists;
- the node exists;
- the node is in `present_site_ids`;
- the subject has `water_sense`.

Successful sensing consumes 30 ordinary game minutes, so any crossed fixed
process boundary still runs authoritative Hydrology and Echo first.

The objective action event is:

```text
LOCAL_AQUEOUS_ECHO_SENSING_PERFORMED
```

Its data contains only the observation type and
`percept_payload_withheld_from_ledger=true`.

---

# 8. Subject-facing perception

The private percept contains only:

```text
echo_presence:      silent / faint / clear / strong
water_borne_pattern: indistinct / threaded
movement_cue:       none_discernible / pooled / moving
source_identity:    unknown
summary
certainty
```

It cannot contain:

```text
actor identity
contact item identity
contact event count
silver fraction
contact units
impulse coefficient
exact node amount or concentration
origin node
state hash
Hydrology answer key
Project relevance
```

`ObservationProvenance` remains Creator-only. D.2.3 adds an optional
`source_process_refs[]` seam so the record can cite an aqueous echo tick without
mislabeling it as a Hydrology tick. Existing D.2.2 records remain unchanged when
that optional field is empty.

---

# 9. Forensic braid

The combined graph can show:

```text
world event
    → embedded material contact
    → aqueous echo tick
        ← same-boundary Hydrology tick
    → guarded objective threshold (when crossed)
    → local sensing action
    → objective sensing event
    → private percept
```

Successive echo ticks are linked through input/output state hashes. This is a
post-hoc causal explanation, not a script given to any participant.

---

# 10. Required counterfactuals

P4-B acceptance must include:

- `FISHED` and a differently named event with identical contacts;
- `silver_rod` and a differently named silver item;
- silver versus hands/iron;
- one contact versus repeated contacts;
- contact followed by decay;
- equal contact at Mirror versus Whisper;
- flowing versus exact zero-flow edge;
- closed versus opened Gate under identical contacts;
- objective field evolution with no observation;
- remote/faculty-invalid versus valid local sensing;
- percept owner versus another subject;
- identical complete histories.

---

# 11. Forbidden implementation shortcuts

The following fail this checkpoint even if a demo looks correct:

```text
if event_type == FISHED and silver_rod:
    notify(nereid_01)

if silver_fishing_count >= 3:
    create_quest(...)

echo_state.nereid_interest = ...

subject_view.exact_echo_amount = ...

raw_echo_transition → DivineKnowledge
```

---

# 12. Acceptance commands

```powershell
py -m unittest discover -s tests -q
py run_project_trials.py --days 30 --seed 42
py run_hydrology_trials.py --days 30
py run_affordance_trials.py --days 30
py run_aqueous_echo_trials.py --days 30 --seed 42
```

Expected D.2.3 candidate gate:

```text
139 unit tests
10/10 PersistentProject LAW
19/19 Hydrology LAW
26/26 Physical Affordance LAW
26/26 Aqueous Silver Echo LAW
```

No model server or API key is needed. Canonical neural Nereid cognition belongs
to P5 and is explicitly outside this checkpoint.
