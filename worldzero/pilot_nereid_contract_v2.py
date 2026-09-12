"""Versioned action interface over owned snapshots; no new world rules or mind."""
from copy import deepcopy
import math

from .neural import DEFAULT_LOCAL_MODEL, NeuralContextBudgetError, NeuralModelRequest
from .pilot_nereid import (MAX_OUTPUT_TOKENS, SYSTEM_PROMPT, VERBS, NereidSnapshot,
                           _json, _keys, _object, parse_decision)

CONTRACT_ID = "nereid.actions.v2"
WORK = "shift_local_silt"
SYSTEM_PROMPT_V2 = SYSTEM_PROMPT + """
ACTION INTERFACE v2 (technical rules, not evidence about physical success):
action=null is a valid deferral. Otherwise choose one verb and exact target
from action_catalog. Catalog membership does not guarantee physical success.
inspect_gate, inspect_water_state and sense_local_water have exactly these
fields: verb, target, evidence_refs. Do not include effort for those actions;
their existing observation time still passes. shift_local_silt additionally
requires effort: a finite fraction strictly greater than 0 and at most 1.
This fraction is NOT your resource stock or capability score. Never copy a
resource amount such as 4 into effort. Resources and outcomes are server-checked.
For action.evidence_refs use ONLY that catalog entry's eligible_percept_refs:
they are your delivered local observations of that exact target. Work requires
at least one; inspection/sensing may use an empty list. Do not put memories or
own-intent refs in action.evidence_refs. Your top-level evidence_refs and each
hypothesis.evidence_refs may cite any delivered memory, percept or own-intent
ref from citable_evidence_refs, never omitted refs. Attempt memory is not proof
of an outcome. A later observation is required to learn a physical effect.
strategy and each hypothesis claim must be nonblank and at most 400 characters.
Use at most 5 hypotheses, at most 32 unique refs per list, and an integer review
delay from 360 to 1440 minutes. No extra fields. There is no required sequence
of actions and no preferred ending; inquiry, work and deferral remain choices.
"""


def action_catalog(data):
    """Derive allowed handles/refs only from the delivered subjective payload."""
    entries = []
    body, gate = data["self"], data["known_gate"]
    for verb in VERBS:
        if verb == "sense_local_water":
            if "water_sense" not in body["faculties"]:
                continue
        elif body["capability_levels"].get(verb, 0) <= 0:
            continue
        if verb in ("inspect_gate", WORK):
            targets = [gate["target"]] if gate["site"] in body["present_site_ids"] else []
        else:
            targets = body["present_site_ids"]
        for target in targets:
            refs = [p["ref"] for p in data["percepts"] if p["target_ref"] == target]
            # The existing work contract needs a delivered local percept.
            # This is not a hidden resource/physics feasibility calculation.
            if verb == WORK and not refs:
                continue
            entry = {"verb": verb, "target": target, "eligible_percept_refs": refs,
                     "minimum_evidence_refs": 1 if verb == WORK else 0}
            if verb == WORK:
                entry["effort_fraction"] = {"exclusive_minimum": 0, "maximum": 1}
            entries.append(entry)
    return entries


def _ref_schema(refs, *, required=False):
    return {"type": "array", "items": {"type": "string", **({"enum": list(refs)} if refs else {})},
            "minItems": 1 if required else 0, "maxItems": min(32, len(refs)), "uniqueItems": True}


def decision_schema_v2(data):
    refs = _ref_schema(data["citable_evidence_refs"])
    short = {"type": "string", "minLength": 1, "maxLength": 400, "pattern": r"\S"}
    actions = [{"type": "null"}]
    for entry in data["action_catalog"]:
        work = entry["verb"] == WORK
        fields = {"verb": {"type": "string", "enum": [entry["verb"]]},
                  "target": {"type": "string", "enum": [entry["target"]]},
                  "evidence_refs": _ref_schema(entry["eligible_percept_refs"], required=work)}
        if work:
            fields["effort"] = {"type": "number", "exclusiveMinimum": 0, "maximum": 1}
        actions.append(_object(fields))
    return _object({"strategy": short, "evidence_refs": refs,
                    "review_after_minutes": {"type": "integer", "minimum": 360, "maximum": 1440},
                    "hypotheses": {"anyOf": [{"type": "null"}, {"type": "array", "maxItems": 5,
                        "items": _object({"claim": short, "evidence_refs": refs})}]},
                    "action": {"anyOf": actions}})


def prepare_request_v2(snapshot, *, context_tokens=8192):
    data = snapshot.payload
    for intent in data["own_intents"]:
        if intent["verb"] != WORK:
            intent.pop("effort", None)  # Omit the legacy sentinel from model-facing memory too.
    while True:
        data["action_contract"] = CONTRACT_ID
        data["citable_evidence_refs"] = sorted(
            item["ref"] for key in ("memories", "percepts", "own_intents") for item in data[key])
        data["action_catalog"] = action_catalog(data)
        schema = decision_schema_v2(data)
        chars = len(SYSTEM_PROMPT_V2) + len(_json(data)) + len(_json(schema)) + 512
        if math.ceil(chars / 3.5) + MAX_OUTPUT_TOKENS + 256 <= context_tokens:
            request = NeuralModelRequest(DEFAULT_LOCAL_MODEL, SYSTEM_PROMPT_V2, data, schema, None, MAX_OUTPUT_TOKENS)
            return request, NereidSnapshot(_json(data))
        key = next((key for key in ("own_intents", "percepts") if data[key]), None)
        if key is None:
            raise NeuralContextBudgetError("mandatory Nereid v2 private context exceeds reserved budget")
        omitted = data[key].pop(0)
        data["omitted_evidence_refs_not_citable"] = (data["omitted_evidence_refs_not_citable"] + [omitted["ref"]])[-18:]
        data["omissions"][key] += 1


def parse_decision_v2(output, snapshot):
    # Strictly validate the new shape first. This is not a repair of an invalid
    # model response; an effort field on an inspection is rejected, even zero.
    _keys(output, {"strategy", "evidence_refs", "review_after_minutes", "hypotheses", "action"})
    action = output["action"]
    if action is not None:
        work = isinstance(action, dict) and action.get("verb") == WORK
        _keys(action, {"verb", "target", "evidence_refs"} | ({"effort"} if work else set()))
    internal = deepcopy(output)
    if action is not None and action["verb"] != WORK:
        # Existing ProjectIntent/resolver encoding remains unchanged for replay.
        # Zero is an internal sentinel, never a model choice or a world cost.
        internal["action"]["effort"] = 0
    return parse_decision(internal, snapshot)
