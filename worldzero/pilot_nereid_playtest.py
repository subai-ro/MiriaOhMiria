"""Bounded internal session: composition and evidence, never a character policy."""
from dataclasses import asdict
from html import escape
from pathlib import Path
from hashlib import sha256
import json
import tempfile

from .pilot_playable import create_pilot_i1_loop
from .pilot_nereid import NEREID, NereidEvidenceProjection, install_nereid_cognition
from .pilot_nereid_neural import (AuditedTransport, EvidenceBudget, RecordedN4Transport,
                                  _write_json, state_evidence)

CALL_LIMIT = 24
COMMAND_LIMIT = 128
MODEL_DIGEST = "1922accd5827ebe6829e536369195db25eaf664528dc66206d646ea3bb386b71"


class _SessionStop(BaseException):
    """Termination must bypass recoverable Project cognition errors."""


class _GuardedReview:
    def __init__(self, mind, projection, budget):
        self.mind, self.projection, self.budget = mind, projection, budget

    def decide(self, percept):
        if self.budget.fatal or self.budget.used >= self.budget.limit:
            raise _SessionStop(self.budget.fatal or "call_limit")
        try:
            return self.mind.decide(self.projection.snapshot(percept.project.project_id))
        except Exception:
            # The unchanged mind already recorded the failure. Do not let the
            # tolerant runtime convert a provider/storage stop into more time.
            if self.budget.fatal:
                raise _SessionStop(self.budget.fatal)
            raise


class NereidPlaytest:
    def __init__(self, directory, *, provider, seed=42, call_limit=CALL_LIMIT,
                 provider_metadata=None):
        if provider is None:
            raise ValueError("explicit provider required")
        if type(call_limit) is not int or not 1 <= call_limit <= CALL_LIMIT:
            raise ValueError("session call limit must be in [1,24]")
        self.budget = EvidenceBudget(directory, limit=call_limit)
        self.seed = seed
        self.loop = create_pilot_i1_loop(seed=seed, prehistory_minutes=0, serial_actions=True)
        projection = NereidEvidenceProjection(self.loop.session)
        self.transport = AuditedTransport(provider, self.budget, run_id="interactive",
                                          projection=projection, contract_version=2)
        mind = install_nereid_cognition(self.loop, transport=self.transport, contract_version=2)
        self.loop.session.project_runtime.register_mind(
            NEREID, _GuardedReview(mind, projection, self.budget))
        self.operations = []
        self.started = self.closed = self.finished = False
        self.stop_reason = None
        _write_json(self.budget.root / "plan.json", {
            "kind": "internal guided playtest, not HUMAN or acceptance",
            "seed": seed, "model_seed": 42, "contract_version": 2,
            "prehistory_minutes": 720, "call_limit": call_limit,
            "command_limit": COMMAND_LIMIT, "provider_metadata": provider_metadata,
            "model": "ministral-3:8b", "temperature": .15, "context": 8192,
            "output_limit": 1200, "timeout_seconds": 180,
            "source_sha256": {name: sha256((Path(__file__).parent/name).read_bytes()).hexdigest()
                for name in ("pilot_nereid_playtest.py", "pilot_nereid.py", "pilot_nereid_contract_v2.py",
                             "pilot_nereid_neural.py", "pilot_playable.py", "pilot.py", "neural.py")}})

    def start(self):
        if self.started or self.closed:
            raise RuntimeError("session already started or closed")
        self.started = True
        self._run(None, lambda: self.loop.session.advance(720))
        self.loop.started_minute = self.loop.session.world.game_minute

    def execute(self, command):
        if not self.started or self.closed:
            raise RuntimeError("session is not open")
        if len(self.operations) - 1 >= COMMAND_LIMIT:
            self.closed, self.stop_reason = True, "command_limit"
            return None
        return self._run(command, lambda: self.loop.execute(command))

    def _run(self, command, operation):
        record = {"command": command, "before_minute": self.loop.session.world.game_minute,
                  "result": None, "error": None}
        prefix = self.budget.root / f"operation_{len(self.operations):03d}"
        result = None
        try:
            _write_json(prefix.with_suffix(".request.json"), record)
            result = operation()
            if result is not None:
                record["result"] = asdict(result)
            if self.loop.session.clock.errors or self.loop.session.ledger.listener_errors:
                raise _SessionStop("authoritative runtime error")
            if self.budget.used >= self.budget.limit:
                self.closed, self.stop_reason = True, "call_limit"
        except (_SessionStop, Exception, KeyboardInterrupt) as exc:
            self.closed = True
            self.stop_reason = f"{type(exc).__name__}: {exc}"
            record["error"] = self.stop_reason
        record["after_minute"] = self.loop.session.world.game_minute
        self.operations.append(record)
        try:
            _write_json(prefix.with_suffix(".result.json"), {
                "operation": record, "state": state_evidence(self.loop),
                "invocations": [asdict(i) for i in self.loop.nereid_mind.invocations]})
        except Exception:
            self.closed, self.stop_reason = True, "checkpoint storage failure"
            raise
        return result

    def finish(self, reason="quit", *, verify_replay=True):
        if self.finished:
            raise RuntimeError("session evidence already finalized")
        self.closed = self.finished = True
        result = {"seed": self.seed, "call_limit": self.budget.limit,
                  "stop_reason": self.stop_reason or reason, "operations": self.operations,
                  "calls": self.transport.records, "final_state": state_evidence(self.loop),
                  "invocations": [asdict(i) for i in self.loop.nereid_mind.invocations],
                  "status": "internal session evidence; not acceptance/freeze or HUMAN"}
        _write_json(self.budget.root / "session_result.json", result)
        saved = json.loads((self.budget.root / "session_result.json").read_text(encoding="utf-8"))
        replay = None
        if verify_replay:
            try:
                replay = {"matches": replay_session(saved)}
            except Exception as exc:
                replay = {"matches": False, "error": f"{type(exc).__name__}: {exc}"}
        _write_json(self.budget.root / "replay.json", replay)
        # Escaped, Creator-only report is written after session close, never in Player View.
        with (self.budget.root / "creator_report.html").open("x", encoding="utf-8") as report:
            report.write('<!doctype html><meta charset="utf-8"><title>World Zero internal session</title>'
                         '<style>body{max-width:1000px;margin:40px auto;font:16px/1.5 system-ui;'
                         'padding:20px}pre{white-space:pre-wrap;overflow-wrap:anywhere}</style>'
                         '<h1>Internal session — post-session Creator View</h1>'
                         '<p>Private diagnostics; not player knowledge or HUMAN acceptance.</p>')
            for title, value in (("Replay", replay), ("Player View", saved["final_state"]["player_view"]),
                                 ("Commands and elapsed time", saved["operations"]),
                                 ("Private decisions", saved["invocations"]),
                                 ("Derived causal graph", saved["final_state"]["creator_graph"])):
                report.write(f'<h2>{title}</h2><pre>{escape(json.dumps(value, ensure_ascii=False, indent=2))}</pre>')
        return replay


def replay_session(result):
    """Exact commands and recorded responses; never a real provider or new policy."""
    with tempfile.TemporaryDirectory() as directory:
        provider = RecordedN4Transport(result["calls"])
        replay = NereidPlaytest(Path(directory)/"replay", provider=provider,
                               seed=result["seed"], call_limit=result["call_limit"])
        for index, operation in enumerate(result["operations"]):
            if index == 0:
                if operation["command"] is not None:
                    return False
                replay.start()
            else:
                replay.execute(operation["command"])
        return (provider.index == len(result["calls"])
                and replay.operations == result["operations"]
                and [asdict(i) for i in replay.loop.nereid_mind.invocations] == result["invocations"]
                and json.dumps(state_evidence(replay.loop), sort_keys=True)
                    == json.dumps(result["final_state"], sort_keys=True))
