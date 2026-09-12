"""Internal session checks; every provider here is an OFFLINE LAB double."""
from copy import deepcopy
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import play_pilot_nereid as cli
from worldzero.affordances import GATE_TARGET
from worldzero.neural import NeuralModelResponse, NeuralProviderError
from worldzero.pilot_nereid_playtest import NereidPlaytest, replay_session, MODEL_DIGEST
from worldzero.pilot_nereid_neural import state_evidence, _write_json
from worldzero.pilot_playable import create_pilot_i1_loop, render_player_view


class LabSessionTransport:
    """Test-only action/quiet/error stimulus, not a playable cognition policy."""
    def __init__(self, mode="work"):
        self.mode, self.calls = mode, 0

    def complete(self, request):
        self.calls += 1
        if self.mode == "unavailable":
            raise NeuralProviderError("LAB_PRIVATE_FAILURE")
        output = {"strategy": "LAB_PRIVATE_SECRET <script>bad</script>", "evidence_refs": [],
                  "review_after_minutes": 720, "hypotheses": None, "action": None}
        if self.mode == "invalid":
            output["strategy"] = "x" * 401
        elif self.mode == "work":
            data = request.input_payload
            gates = [p for p in data["percepts"] if p["target_ref"] == GATE_TARGET]
            if not gates:
                output["action"] = {"verb": "inspect_gate", "target": GATE_TARGET, "evidence_refs": []}
            elif not any(i["verb"] == "shift_local_silt" for i in data["own_intents"]):
                output["action"] = {"verb": "shift_local_silt", "target": GATE_TARGET,
                                    "effort": 1, "evidence_refs": [gates[-1]["ref"]]}
        return NeuralModelResponse(output, finish_reason="stop")


class PlaytestTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.guard = patch("worldzero.neural.urlopen", side_effect=AssertionError("offline network"))
        self.guard.start()
        self.addCleanup(self.guard.stop)

    def make(self, mode="work", name="run", **kwargs):
        return NereidPlaytest(self.root/name, provider=LabSessionTransport(mode), **kwargs)

    def finish(self, play):
        self.assertTrue(play.finish()["matches"])
        return json.loads((play.budget.root/"session_result.json").read_text(encoding="utf-8"))

    def test_start_uses_same_v2_composition_and_autonomous_prehistory(self):
        play = self.make()
        self.assertEqual(0, play.budget.used)
        play.start()
        self.assertEqual(720, play.loop.session.world.game_minute)
        self.assertEqual(1, play.budget.used)
        self.assertEqual(2, play.loop.nereid_mind.contract_version)
        self.assertIs(play.loop.navigation.session, play.loop.session)
        self.assertTrue(play.loop.session.clock.serial_actions)
        self.assertEqual([], play.loop.player_view().as_dict()["observations"])
        with self.assertRaises(RuntimeError): play.start()

    def test_player_never_sees_private_decisions_or_report_during_play(self):
        play = self.make()
        play.start()
        self.assertNotIn("LAB_PRIVATE", render_player_view(play.loop.player_view()))
        self.assertFalse((play.budget.root/"creator_report.html").exists())
        self.finish(play)
        report = (play.budget.root/"creator_report.html").read_text(encoding="utf-8")
        self.assertIn("LAB_PRIVATE", report)
        self.assertNotIn("<script>bad</script>", report)
        with self.assertRaises(RuntimeError): play.execute("wait")
        with self.assertRaises(RuntimeError): play.finish()

    def test_invalid_locality_and_read_commands_change_no_world_or_calls(self):
        play = self.make()
        play.start()
        before, count = state_evidence(play.loop), play.budget.used
        for command in ("inspect gate", "look gallery", "go gallery", "wait 9999", "water_sense"):
            self.assertFalse(play.execute(command).ok)
        for command in ("help", "journal", "look"):
            self.assertTrue(play.execute(command).ok)
        self.assertEqual(before, state_evidence(play.loop))
        self.assertEqual(count, play.budget.used)
        self.finish(play)

    def test_work_quiet_counterfactual_is_settled_and_player_owned(self):
        plays = [self.make(mode, mode) for mode in ("work", "quiet")]
        for play in plays:
            play.start()
            play.execute("go gate")
            play.execute("inspect")
            first = play.loop.player_view().observations
            while play.loop.session.world.game_minute < 2160:
                play.execute(f"wait {min(360,2160-play.loop.session.world.game_minute)}")
            self.assertEqual(first, play.loop.player_view().observations)
            play.execute("inspect")
            self.assertEqual(2205, play.loop.session.world.game_minute)
            self.finish(play)
        self.assertEqual(plays[0].loop.player_view().observations[0], plays[1].loop.player_view().observations[0])
        self.assertIn("light", plays[0].loop.player_view().observations[-1])
        self.assertIn("moderate", plays[1].loop.player_view().observations[-1])
        self.assertEqual(0, plays[0].loop.session.hydrology.state.gate.sluice_position)

    def test_provider_stop_is_immediate_recorded_and_replayable(self):
        play = self.make("unavailable")
        play.start()
        self.assertTrue(play.closed)
        self.assertEqual(360, play.loop.session.world.game_minute)
        self.assertEqual(1, play.budget.used)
        self.assertIn("NeuralProviderError", play.loop.nereid_mind.invocations[0].error)
        self.assertEqual(0, len(play.loop.session.project_trace.intents))
        self.finish(play)

    def test_budget_stops_without_replacement_policy_or_extra_provider_call(self):
        play = self.make("quiet", call_limit=1)
        play.start()
        self.assertTrue(play.closed)
        self.assertEqual(1, play.budget.used)
        self.assertEqual(1, len(play.loop.nereid_mind.invocations))
        before = state_evidence(play.loop)
        with self.assertRaises(RuntimeError): play.execute("wait 360")
        self.assertEqual(before, state_evidence(play.loop))
        self.finish(play)

    def test_invalid_output_preserves_cooldown_and_does_not_create_intent(self):
        play = self.make("invalid", call_limit=3)
        play.start()
        self.assertEqual(2, play.budget.used)  # reviews 360 and 720; no immediate repair
        self.assertFalse(play.closed)
        play.execute("wait 360")
        self.assertTrue(play.closed)
        self.assertEqual(3, len(play.loop.session.project_runtime.errors))
        self.assertEqual(0, len(play.loop.session.project_trace.intents))
        self.finish(play)

    def test_existing_directory_and_invalid_limits_rejected(self):
        play = self.make()
        with self.assertRaises(FileExistsError): self.make()
        for limit in (0, 25, True, 1.5):
            with self.assertRaises(ValueError): self.make(name="bad", call_limit=limit)
        with self.assertRaises(ValueError): NereidPlaytest(self.root/"none", provider=None)
        self.assertFalse((self.root/"bad").exists())

    def test_command_reservation_failure_stops_before_time_or_provider(self):
        play = self.make()
        def failing(path, value):
            if str(path).endswith(".request.json"):
                raise OSError("LAB storage full")
            return _write_json(path, value)
        with patch("worldzero.pilot_nereid_playtest._write_json", side_effect=failing): play.start()
        self.assertTrue(play.closed)
        self.assertEqual(0, play.budget.used)
        self.assertEqual(0, play.loop.session.world.game_minute)

    def test_checkpoint_storage_failure_prevents_further_actions(self):
        play = self.make()
        play.start()
        with patch("worldzero.pilot_nereid_playtest._write_json", side_effect=OSError("LAB disk")):
            with self.assertRaises(OSError): play.execute("look")
        self.assertTrue(play.closed)
        with self.assertRaises(RuntimeError): play.execute("wait")

    def test_replay_detects_player_input_and_state_tampering(self):
        play = self.make()
        play.start()
        play.execute("go gate")
        saved = self.finish(play)
        changed = deepcopy(saved)
        changed["operations"][1]["command"] = "go gallery"
        self.assertFalse(replay_session(changed))
        changed = deepcopy(saved)
        changed["final_state"]["minute"] += 1
        self.assertFalse(replay_session(changed))

    def test_frozen_i1_has_no_model_or_serial_mode(self):
        loop = create_pilot_i1_loop()
        self.assertFalse(loop.session.clock.serial_actions)
        self.assertFalse(hasattr(loop,"nereid_mind"))

    def test_command_count_limit_does_not_spend_time_or_calls(self):
        play = self.make()
        play.start()
        with patch("worldzero.pilot_nereid_playtest.COMMAND_LIMIT", 1):
            play.execute("look")
            before = state_evidence(play.loop)
            self.assertIsNone(play.execute("wait"))
        self.assertTrue(play.closed)
        self.assertEqual(before, state_evidence(play.loop))

    def test_cli_requires_approval_and_new_local_output_before_provider(self):
        for argv in (["play", "--output-dir", str(self.root/"x")],
                     ["play", "--approved-local-playtest", "--output-dir", str(self.root/"x")]):
            with patch("sys.argv", argv), patch.object(cli,"local_model_preflight") as preflight, patch("sys.stderr",io.StringIO()):
                with self.assertRaises(SystemExit): cli.main()
                preflight.assert_not_called()

    def test_cli_quit_and_eof_save_replay_and_hide_private_output(self):
        for index, inputs in enumerate((["go gate","inspect","quit"], [EOFError()])):
            directory = self.root/"local_acceptance"/f"cli{index}"
            argv = ["play","--approved-local-playtest","--output-dir",str(directory)]
            out = io.StringIO()
            with patch("sys.argv",argv), patch.object(cli,"__file__",str(self.root/"entry.py")), \
                 patch.object(cli,"local_model_preflight",return_value={"digest":MODEL_DIGEST}), \
                 patch.object(cli,"OllamaChatTransport",return_value=LabSessionTransport()), \
                 patch("builtins.input",side_effect=inputs), patch("sys.stdout",out):
                self.assertEqual(0, cli.main())
            self.assertNotIn("LAB_PRIVATE",out.getvalue())
            self.assertTrue(json.loads((directory/"replay.json").read_text())["matches"])

    def test_cli_changed_or_unavailable_model_never_starts_session(self):
        argv = ["play", "--approved-local-playtest", "--output-dir", str(self.root/"local_acceptance"/"bad")]
        for failure in (False, True):
            with patch("sys.argv",argv), patch.object(cli,"__file__",str(self.root/"entry.py")), \
                 patch.object(cli,"local_model_preflight", return_value={"digest":"different"},
                              side_effect=OSError("offline") if failure else None), \
                 patch.object(cli,"OllamaChatTransport") as provider, patch("sys.stderr",io.StringIO()):
                with self.assertRaises(SystemExit): cli.main()
                provider.assert_not_called()

    def test_cli_provider_failure_does_not_print_private_error(self):
        directory = self.root/"local_acceptance"/"failure"
        argv = ["play", "--approved-local-playtest", "--output-dir", str(directory)]
        out = io.StringIO()
        with patch("sys.argv",argv), patch.object(cli,"__file__",str(self.root/"entry.py")), \
             patch.object(cli,"local_model_preflight",return_value={"digest":MODEL_DIGEST}), \
             patch.object(cli,"OllamaChatTransport",return_value=LabSessionTransport("unavailable")), \
             patch("builtins.input") as user_input, patch("sys.stdout",out):
            self.assertEqual(1,cli.main())
            user_input.assert_not_called()
        self.assertNotIn("LAB_PRIVATE_FAILURE",out.getvalue())

    def test_authoritative_failure_closes_session_without_more_calls(self):
        play = self.make()
        play.start()
        with patch.object(play.loop.session.world,"advance",side_effect=RuntimeError("LAB physics")):
            play.execute("wait 360")
        self.assertTrue(play.closed)
        self.assertEqual(1,play.budget.used)
        self.assertTrue(play.loop.session.clock.errors)
        with self.assertRaises(RuntimeError): play.execute("wait")

    def test_keyboard_interrupt_closes_cli_and_retains_evidence(self):
        directory = self.root/"local_acceptance"/"interrupted"
        argv = ["play", "--approved-local-playtest", "--output-dir", str(directory)]
        with patch("sys.argv",argv), patch.object(cli,"__file__",str(self.root/"entry.py")), \
             patch.object(cli,"local_model_preflight",return_value={"digest":MODEL_DIGEST}), \
             patch.object(cli,"OllamaChatTransport",return_value=LabSessionTransport()), \
             patch("builtins.input",side_effect=KeyboardInterrupt()), patch("sys.stdout",io.StringIO()):
            self.assertEqual(1,cli.main())
        self.assertTrue(json.loads((directory/"replay.json").read_text())["matches"])
