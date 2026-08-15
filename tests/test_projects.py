from __future__ import annotations

import unittest

from worldzero.project_runtime import ProjectDecision, ProjectRuntime
from worldzero.project_trials import run_no_player_prehistory_trial
from worldzero.projects import (
    AttemptOutcome,
    PersistentProjectStore,
    ProjectStatus,
    seed_silver_thread_projects,
)
from worldzero.provenance import CausalEdgeKind, CausalTrace


class PersistentProjectTests(unittest.TestCase):
    def test_silver_thread_projects_exist_without_player_assignment(self) -> None:
        store = seed_silver_thread_projects(0)
        nereid = store.get("nereid_return_underpeak")
        trade = store.get("trade_house_underpeak_route")
        self.assertEqual("nereid_01", nereid.owner_id)
        self.assertEqual("trade_house_01", trade.owner_id)
        self.assertNotIn("player_id", nereid.as_dict())
        self.assertNotIn("player_id", trade.as_dict())

    def test_duplicate_project_id_is_rejected(self) -> None:
        store = seed_silver_thread_projects(0)
        with self.assertRaises(ValueError):
            store.create(
                project_id="nereid_return_underpeak",
                owner_id="someone_else",
                desire="duplicate",
                motivation="duplicate",
                commitment=0.5,
                current_strategy="duplicate",
                created_minute=0,
            )

    def test_failed_attempt_does_not_complete_or_delete_project(self) -> None:
        store = seed_silver_thread_projects(0)
        attempt = store.record_attempt(
            "nereid_return_underpeak",
            game_minute=100,
            strategy="try something",
            decision_ref="decision:1",
            intent_refs=("intent:1",),
            resolution_refs=("resolution:1",),
            outcome=AttemptOutcome.BLOCKED,
            evidence_refs=("resolution:1",),
        )
        project = store.get("nereid_return_underpeak")
        self.assertEqual(AttemptOutcome.BLOCKED, attempt.outcome)
        self.assertEqual(ProjectStatus.ACTIVE, project.status)
        self.assertEqual(1, len(project.attempt_history))
        self.assertIn("resolution:1", project.subjective_evidence_refs)

    def test_completion_requires_authoritative_validator(self) -> None:
        store = seed_silver_thread_projects(0)
        completed, project = store.complete_if(
            "nereid_return_underpeak",
            completion_rule_id="water_path.connected.v1",
            validator=lambda _: False,
        )
        self.assertFalse(completed)
        self.assertEqual(ProjectStatus.ACTIVE, project.status)
        completed, project = store.complete_if(
            "nereid_return_underpeak",
            completion_rule_id="water_path.connected.v1",
            validator=lambda _: True,
        )
        self.assertTrue(completed)
        self.assertEqual(ProjectStatus.COMPLETED, project.status)
        self.assertEqual("water_path.connected.v1", project.completion_rule_id)

    def test_trace_rejects_evidence_the_subject_did_not_have(self) -> None:
        store = seed_silver_thread_projects(0)
        trace = CausalTrace()
        with self.assertRaises(ValueError):
            trace.record_decision(
                project=store.get("nereid_return_underpeak"),
                game_minute=100,
                subjective_evidence_refs=("objective:master_hydrology_graph",),
            )

    def test_trace_preserves_distinct_causal_edge_types(self) -> None:
        store = seed_silver_thread_projects(0)
        project = store.get("nereid_return_underpeak")
        trace = CausalTrace()
        decision = trace.record_decision(
            project=project,
            game_minute=10,
            subjective_evidence_refs=(project.subjective_evidence_refs[0],),
        )
        intent = trace.record_intent(
            decision_ref=decision.ref,
            intent_type="inspect",
            target_refs=("region:underpeak",),
        )
        trace.record_resolution(
            intent_ref=intent.ref,
            game_minute=10,
            resolver_rule_id="test.rule",
            ok=True,
            outcome=AttemptOutcome.SUCCEEDED.value,
            message="resolved",
            result_event_ids=(7,),
        )
        kinds = {edge.kind for edge in trace.edges()}
        self.assertEqual(
            {
                CausalEdgeKind.PROJECT_CONTEXT,
                CausalEdgeKind.DECISION_INPUT,
                CausalEdgeKind.AUTHORED_INTENT,
                CausalEdgeKind.ACTION_RESOLUTION,
                CausalEdgeKind.OBJECTIVE_RESULT,
            },
            kinds,
        )

    def test_no_player_prehistory_acceptance(self) -> None:
        result = run_no_player_prehistory_trial(seed=42, elapsed_days=30)
        self.assertTrue(result.passed, [check for check in result.checks if not check.ok])
        nereid = result.projects.get("nereid_return_underpeak")
        self.assertGreaterEqual(len(nereid.attempt_history), 3)
        self.assertEqual(ProjectStatus.ACTIVE, nereid.status)
        self.assertFalse(result.runtime.errors)

    def test_runtime_rejects_mind_that_cites_unavailable_evidence(self) -> None:
        class BadMind:
            def decide(self, percept):
                return ProjectDecision(
                    strategy="cheat",
                    subjective_evidence_refs=("objective:secret",),
                    next_review_minute=percept.game_minute + 10,
                )

        store = PersistentProjectStore()
        store.create(
            project_id="p",
            owner_id="owner",
            desire="want",
            motivation="because",
            commitment=1.0,
            current_strategy="wait",
            created_minute=0,
            next_review_minute=0,
        )
        runtime = ProjectRuntime(store, CausalTrace())
        runtime.register_mind("owner", BadMind())
        self.assertEqual((), runtime.tick(1))
        self.assertEqual(1, len(runtime.errors))
        self.assertEqual(1, store.get("p").revision)


if __name__ == "__main__":
    unittest.main()
