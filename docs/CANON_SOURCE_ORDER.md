# Canon and source order

This file prevents an older handoff from silently overriding newer executable
work.

## When sources disagree

1. The user's latest explicit decision for the current task.
2. Non-negotiable canon laws in AGENTS.md and accepted later decisions.
3. docs/canon/WORLD_ZERO_DIVINE_ONTOLOGY_CANON_V0_1.md for accepted divine
   ontology, with its explicitly provisional and open sections preserved.
4. docs/pilot/WORLD_ZERO_PILOT_0_1_DIRECTION.md for the accepted Ash Valley
   product direction; it does not promote executable status by itself.
5. WORLD_ZERO_CURRENT_STATE.md for checkpoint and migration status.
6. The current checkpoint spec and matching acceptance record.
7. Code plus tests for the behavior that is actually implemented.
8. The cumulative README.md.
9. docs/foundations/WORLD_ZERO_CANON.md and
   WORLD_ZERO_POST_GLOSSARY_HANDOFF.md for enduring concepts.
10. WORLD_ZERO_GLOSSARY.md for terminology.
11. WORLD_ZERO_PLAYER_EXPERIENCE_NORTH_STAR.md for strategic experience goals.
12. WORLD_ZERO_DIFFERENTIATION_IDEA_VAULT.md as non-canonical candidates only.

This is not permission to use passing tests to overrule canon. If code or a test
violates a higher law, report the conflict and propose an explicit migration.
Do not silently choose whichever source makes the task easiest.

## Important historical caveat

The foundation documents were written on 2026-08-07 around D.1.3.3 and the
planned D.1.4 work. Their roadmap labels are historical. The project has since
completed and frozen D.1.4.2, D.2.0, D.2.1, D.2.2, and D.2.3. D.2.3 was
user-local accepted on 2026-08-15 after 139 tests and LAW 10/10, 19/19, 26/26,
26/26.

Pilot 0.1 I0 was builder-verified on 2026-09-04 after 146 tests, 13/13 new LAW
and all four frozen LAW regressions. The user reproduced the local gate and
explicitly accepted and froze I0 on 2026-09-04. The accepted Pilot and Divine
Ontology documents supersede P5-as-the-sole-roadmap assumptions without
changing the frozen D.2.3 baseline.

Pilot 0.1 I1 was builder-verified on 2026-09-04 after 158 tests, 21/21 new LAW,
the frozen I0 gate and all four frozen D.2.x LAW regressions. After guided local
play and a verified four-item UX correction pass, the user explicitly accepted
and froze I1 on 2026-09-05.

Pilot I3-N/N0 was explicitly accepted on 2026-09-05 after 176 tests and all
frozen regressions; the user did not declare a freeze. N1–N3 are a subsequent
builder-verified offline candidate (207 tests, 12/12 E2E), not accepted/frozen
or a canonical neural/HUMAN pass. A lab double never changes that status.

The explicitly approved initial N4 local-model batch completed on 2026-09-05
and failed: 6/68 ordinary decisions valid, 72 total calls, 18/18 exact replays.
The current 220-test offline suite includes 13 new harness tests, not a neural
acceptance. No correction/retry or later acceptance/freeze is implied.

The old documents remain authoritative for enduring principles such as limited
knowledge, causal autonomy, non-player-centered history, and the separation
between objective events and subjective belief. They are not authoritative for
the current version number, test count, next implementation step, or whether a
later checkpoint exists.

## Status vocabulary

- implemented: present in code;
- builder-verified: passes in the construction environment;
- user-local accepted: independently reproduced by the user;
- frozen: protected baseline; new work must remain additive;
- candidate: implemented but still awaiting its declared acceptance boundary;
- idea: exploratory and non-canonical until explicitly accepted.

Never promote one status to another by inference.
