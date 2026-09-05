# WORLD ZERO — PILOT 0.1 DIRECTION AND CODEX HANDOFF

**Decision date:** 2026-08-17  
**Working title:** `World Zero Pilot 0.1 — Ash Valley`  
**Status:** accepted product direction; architecture and implementation plan
still require user approval  
**Primary companion document:**
`docs/canon/WORLD_ZERO_DIVINE_ONTOLOGY_CANON_V0_1.md`

---

## 0. Purpose

World Zero already contains strong research proofs: bounded divine epistemics,
Persistent Projects, fixed-clock Hydrology, local physical affordances and one
objective hidden-metaphysics law. It does not yet contain an investor-facing
playable proof of the complete product thesis.

This handoff redirects development from another isolated subsystem or a
Nereid-only demonstration toward a compact ensemble pilot in which several
autonomous subjects create intersecting history.

---

# I. Baseline and source authority

## 1. Verify the actual local repository

Expected user-local baseline is D.2.3 accepted and frozen, with:

- 139 unit tests;
- D.2.0 10/10 LAW;
- D.2.1 19/19 LAW;
- D.2.2 26/26 LAW;
- D.2.3 26/26 LAW.

The transferred scratch snapshot may still call D.2.3 a candidate. Codex must
trust and inspect the user's actual Git repository, current-state documents,
acceptance record and tag. It must report any discrepancy and must not promote
or demote a checkpoint merely because this handoff exists.

All new work remains additive over frozen D.1.4.2 and D.2.0–D.2.3 laws.

## 2. Roadmap supersession

Older files say the immediate next construction boundary is P5 canonical
Nereid cognition or call the whole pilot `The Silver Thread`.

That direction is superseded **as the sole product roadmap**.

Canonical Nereid cognition remains valuable, but it becomes one bounded thread
inside a broader pilot. Do not implement the earlier `World Zero Pilot 0.1 —
The Silver Thread` plan unchanged.

The following earlier assumptions are specifically rejected for the external
pilot:

- no active Gods;
- Nereid as the central load-bearing participant;
- terminal-only Player View as the investor surface;
- granting Arra `water_sense` merely to expose the Echo mechanic;
- one hydrology-centred storyline presented as proof of the whole game.

---

# II. Product thesis

## 3. What the pilot must prove

The pilot must make this visible without a lecture:

> A small action enters a world whose Gods, lesser entities, institutions,
> physical processes and mortals already have histories and desires. Each knows
> only part of reality. Their independent decisions produce delayed,
> persistent, forensically explainable consequences that nobody centrally
> authored.

The player is neither the centre of history nor irrelevant. The player can
discover, misinterpret, conceal, communicate and alter causes already in
motion.

## 4. Small geography, broad causality

A compact region is acceptable. A single storyline is not.

The pilot should use one dense region containing Ash Valley, its death-sites,
northern waters, a trade route and the edge of Underpeak. Geographic expansion
is secondary to independent actors, different player fantasies and
cross-system consequences.

---

# III. Three independent causal threads

## 5. Thread A — Aqueous Silver Echo / Silver Thread

**Primary proof:** hidden metaphysics, Hydrology, physical affordances and a
lesser entity with an old desire.

Participants:

- Nereid;
- God of Nature;
- local waters and the Underpeak system;
- mortals or institutions who may alter the physical route.

The Nereid's return Project exists before the player. Silver-water contact is
an objective law and possible source of evidence, not an interest or quest
trigger. Nereid may ignore, misunderstand or never encounter it.

## 6. Thread B — The Unremembered Dead

**Primary proof:** active divine subjectivity, superior but non-omniscient
memory, deception, necromancy and divergence between God and religion.

Participants:

- God of Death;
- a local death cult or temple;
- a bounded Necromantic Order cell;
- an old burial or death-site;
- mortals carrying testimony and partial evidence.

God of Death can remember ancient events extraordinarily well while still
lacking current physical facts or being deceived about present actors. The
cult does not read the God's mind and may sincerely or opportunistically offer
a false interpretation.

This thread must remain meaningful if Nereid is removed entirely.

## 7. Thread C — The Price of a Promise

**Primary proof:** autonomous divine personality outside death/nature,
contracts, institutions, social choices and material economic consequences.

Participants:

- God of Trade and Contracts;
- Trade House;
- at least two mortal or institutional parties to a live obligation;
- the route, goods, labour or resources affected by the agreement.

The conflict should distinguish the letter, purpose and living consequences of
an agreement. The Trade God has a personal Project concerning freedom and
promise; it is not a divine contract parser or automatic debt collector.

This thread must remain meaningful without Nereid, Hydrology and necromancy.

## 8. Optional intersection, not forced convergence

Shared world processes may connect the threads:

- water threatens a burial;
- a route changes the value or feasibility of a contract;
- a deceased party leaves a disputed obligation;
- a cult depends on Trade House funding;
- a Nereid offers information or access in exchange for help;
- Gods make conflicting claims over one consequence.

No global director may order these intersections or require all three threads
to reach a designed finale.

---

# IV. Starting autonomous subjects

## 9. Required first-class subjects

The target pilot ensemble is:

| Subject | Independent pre-player Project |
| --- | --- |
| God of Death | Preserve or investigate a death-site and violations of the life/death boundary |
| God of Nature | Determine the fate of the isolated Underpeak ecology and its seal |
| God of Trade/Contracts | Resolve or escape a consequential promise without reducing itself to its domain pressure |
| Nereid | Return to Underpeak waters |
| Trade House | Establish or restore a route for institutional reasons |
| Death cult | Protect the dead and preserve its interpretation/authority |
| Necromantic Order cell | Test or advance a bounded method involving memory of the dead |

The architecture must treat all three Gods as first-class divine subjects even
if implementation is staged. At least Death and Nature must be active divine
actors in the integrated pilot. Codex must propose an honest staged boundary
for Trade rather than silently replacing the Trade God with the Trade House.

Acceptance doubles must not appear in the production/demo registry.

## 10. Mortals

Use a small cast of persistent named mortals, approximately 6–10 for the pilot,
shared across locations and institutions. They need bounded memory,
relationships, roles and autonomous routines sufficient for the three threads;
they do not need general AGI or a full population simulator.

Arra remains a test/player fixture, not immutable final protagonist lore. Arra
has no assigned world-saving Project and no innate `water_sense` unless the
user later authorizes a specific diegetic source for that faculty.

---

# V. Player experience

## 11. Core player verbs

The pilot should support a small reusable vocabulary:

- move and wait;
- inspect a local physical or social situation;
- interact with ordinary objects and materials;
- perform bounded physical work through authoritative resolvers;
- converse and receive claims;
- tell the truth, lie, omit or selectively route information;
- make, refuse, fulfil or break a bounded promise;
- accept, reject or renegotiate a request;
- leave a situation and allow it to continue without the player.

These are verbs, not quest stages.

## 12. Player View

The external pilot requires a minimal **visual** Player View. A terminal may
remain an internal diagnostic and acceptance harness but is not the final
investor or external-playtest surface.

The visual design can be modest, but must show:

- location and navigable local space;
- visible subjects and objects;
- dialogue or claims with clear provenance;
- owned observations and promises;
- passage of time;
- persistent visible consequences.

Player View must not receive `WorldState`, raw Ledger, Hydrology/Echo values,
foreign private evidence, divine confidence values, hidden IDs or Creator
provenance.

Do not add a universal quest list merely to explain the demo.

## 13. Creator / Investor View

A separate post-session or demonstrator-only view should reconstruct:

- objective events;
- each subject's private percepts and memories;
- beliefs and cited evidence;
- decisions and typed intents;
- authoritative resolutions;
- Project revisions;
- world-process transitions;
- cross-thread causal edges;
- the exact divergence caused by player or non-player actions.

This is evidence that the history was generated causally, not the interface
through which the player experiences the world.

---

# VI. Required negative boundaries

## 14. Do not regress the existing architecture

The pilot must not:

- create a global Story Director;
- turn `FISHED` into Nereid interest;
- turn a percept into automatic attention, contact, request or quest;
- expose objective world state to a God because the event concerns its domain;
- let neural prose declare a physical, contractual or metaphysical result;
- duplicate the authoritative Ledger, clock, evidence ownership or physical
  resolver systems;
- weaken ordinary locality/resource checks to support divine remote action;
- make a cult a proxy view into a God's beliefs;
- treat worship as generic mana;
- reduce divine memory to the prototype's short recollection window;
- centre all meaningful histories on Arra;
- script named endings into input manifests or tests;
- call a checkpoint accepted or frozen without its declared acceptance gate.

## 15. Power and targeting

The future divine-action seam must reflect the new canon:

- knowledge improves deliberate targeting but is not a universal permission
  gate;
- Gods may use identity, place, trace, class or objective condition selectors;
- sufficient effective power may overcome distance or contested jurisdiction;
- objective targeting must not reveal the selected target automatically;
- authoritative resolvers own results and consequences.

Do not retrofit these rules by weakening `PhysicalAffordanceBridge`. Propose a
separate additive divine/metaphysical resolution boundary.

---

# VII. Pilot proof and acceptance direction

## 16. Required counterfactuals

Codex must design exact LAW counts later, but the acceptance architecture must
include at least:

1. **No-player history:** the region continues and multiple Projects advance.
2. **No-Nereid history:** Death and Trade threads remain active and meaningful.
3. **Thread independence:** disabling any one thread does not freeze the other
   two.
4. **Common-T0 counterfactuals:** changing one player input yields a durable,
   causally traceable divergence.
5. **Private-evidence isolation:** one subject cannot read another's percept or
   memory without delivery.
6. **Superior-memory boundary:** durable divine memory does not become Ledger
   access or retroactive knowledge.
7. **Conditional-targeting boundary:** objective selection can affect an
   unknown target without returning an answer key.
8. **Resolver authority:** intention never declares success.
9. **No Director / no quest trigger:** actor decisions remain independent.
10. **Player View safety:** zero hidden-state or foreign-evidence leaks.
11. **Forensic completeness:** every displayed causal explanation resolves to
    real decisions, events and state transitions.
12. **Frozen regressions:** all accepted D.1/D.2 gates remain green.

## 17. Human proof

Before investor use, testers unfamiliar with the architecture should be able
to understand through play that:

- the world existed before them;
- at least two divine or institutional subjects want different things;
- observations and claims are not the same as truth;
- refusing or leaving does not stop history;
- a later consequence plausibly follows from earlier action;
- the experience is not a conventional quest chain with hidden dressing.

Exact human acceptance thresholds belong in a later approved acceptance
contract.

---

# VIII. Development sequence

## 18. Plan before code

The next Codex task is a read-only architecture and product plan. Do not begin
implementation from this handoff alone.

Codex must first:

1. reconcile the actual local checkpoint and Git status;
2. read the new divine ontology canon;
3. audit the current D.1 divine runtime and D.2 physical/project seams;
4. identify which parts of the previous Silver Thread plan are reusable;
5. show where that plan conflicts with the new direction;
6. propose the smallest additive D.1-to-D.2 integration seam;
7. propose a staged visual vertical slice rather than a terminal-only demo;
8. estimate complexity and identify cuts that do not destroy the product
   thesis;
9. propose tests and acceptance gates without weakening frozen LAW.

## 19. Recommended milestone shape

This is guidance, not permission to implement:

- **I0 — Canon and architecture integration:** install the new documents,
  update source order/current direction, define the smallest first-class God
  contract and D.1→D.2 seam.
- **I1 — Visible older world:** minimal visual Player View, bounded movement,
  time passage and autonomous prehistory through one production composition.
- **I2 — Active Death thread:** connect existing Death cognition to owned D.2
  evidence, Projects and authoritative actions without truth leakage.
- **I3 — Nature and Silver thread:** canonical Nature/Nereid cognition over
  local evidence and existing Hydrology/Echo/affordance resolvers.
- **I4 — Promise thread:** Trade God, Trade House and a bounded live contract
  with material consequences.
- **I5 — Cross-thread communication:** claims, lies, omissions, covenants and
  institutional interpretation using one ownership-safe evidence seam.
- **I6 — Counterfactual replay and Creator View:** common-T0 histories and a
  unified forensic explanation.
- **I7 — Pilot acceptance:** offline LAW, separately authorized neural trials,
  internal timed rehearsals and external human comprehension tests.

Every executable increment should end in a player-visible loop. Do not spend
several checkpoints building invisible ontology infrastructure without a
demonstrable experience.

## 20. Scope discipline

Pilot 0.1 is not an MMORPG production build. It does not require:

- networking or concurrency at scale;
- a seamless large world;
- general combat/crafting systems;
- a full economy;
- dozens of Gods;
- arbitrary natural-language action;
- final art;
- universal religion, reputation or dialogue frameworks.

It does require enough visual, interactive and causal coherence that a stranger
can perceive the product thesis without reading design documents.

---

# IX. Definition of the next approved deliverable

The immediate deliverable from Codex is a **plan**, not code or a commit. It
must contain:

1. read-only audit verdict and conflicts;
2. exact Pilot 0.1 boundary;
3. actor/thread matrix;
4. reuse-versus-missing integration matrix;
5. proposed data contracts and authoritative seams;
6. incremental implementation plan with player-visible outcomes;
7. positive, negative and counterfactual gates;
8. visual Player View approach and Creator View approach;
9. size/complexity estimates, risks and cut order;
10. a list of documentation changes to make only after plan approval.

The user should review this plan before selecting “Implement plan.”
