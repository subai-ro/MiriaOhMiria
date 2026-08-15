# Canon and source order

This file prevents an older handoff from silently overriding newer executable
work.

## When sources disagree

1. The user's latest explicit decision for the current task.
2. Non-negotiable canon laws in AGENTS.md and accepted later decisions.
3. WORLD_ZERO_CURRENT_STATE.md for checkpoint and migration status.
4. The current checkpoint spec and matching acceptance record.
5. Code plus tests for the behavior that is actually implemented.
6. The cumulative README.md.
7. docs/foundations/WORLD_ZERO_CANON.md and
   WORLD_ZERO_POST_GLOSSARY_HANDOFF.md for enduring concepts.
8. WORLD_ZERO_GLOSSARY.md for terminology.
9. WORLD_ZERO_PLAYER_EXPERIENCE_NORTH_STAR.md for strategic experience goals.
10. WORLD_ZERO_DIFFERENTIATION_IDEA_VAULT.md as non-canonical candidates only.

This is not permission to use passing tests to overrule canon. If code or a test
violates a higher law, report the conflict and propose an explicit migration.
Do not silently choose whichever source makes the task easiest.

## Important historical caveat

The foundation documents were written on 2026-08-07 around D.1.3.3 and the
planned D.1.4 work. Their roadmap labels are historical. The project has since
completed and frozen D.1.4.2, D.2.0, D.2.1, D.2.2, and D.2.3. D.2.3 was
user-local accepted on 2026-08-15 after 139 tests and LAW 10/10, 19/19, 26/26,
26/26.

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
