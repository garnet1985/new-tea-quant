"""Shared setup-pipeline session: ``.ntq/setup-runtime.json``.

CLI ``install.py`` and the UI wizard read/write this file. ``isReady`` is the
source of truth for “installation finished”.
"""
from __future__ import annotations

import json
import time
from typing import Any, Dict, List, Optional

from core.infra.setup.core.env import NewTeaQuantSetup
from core.infra.setup.core.meta_loader import load_setup_step_meta
from core.infra.setup.core.pipeline_state import sync_definition_into_state

STATE_FILE = NewTeaQuantSetup.repo_root / ".ntq" / "setup-runtime.json"

STATUS_NOT_STARTED = "not_started"
STATUS_WAITING_INPUT = "waiting_input"
STATUS_RUNNING = "running"
STATUS_SUCCESS = "success"
STATUS_FAILED = "failed"


def _definition() -> List[Dict[str, Any]]:
    return load_setup_step_meta(ui_only=True)


def new_state(definition: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    steps = definition if definition is not None else _definition()
    return {
        "sessionId": f"setup_{int(time.time())}",
        "version": 1,
        "isReady": False,
        "installSource": "",
        "stepStates": [
            {"stepId": step["id"], "status": STATUS_NOT_STARTED, "errorMessage": ""}
            for step in steps
        ],
        "inputsByStep": {},
        "noticesByStep": {},
        "stepSeconds": {},
        "skippedSteps": [],
    }


def save_state(state: Dict[str, Any]) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(
        json.dumps(state, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def load_state(definition: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    steps = definition if definition is not None else _definition()
    if not STATE_FILE.is_file():
        return new_state(steps)
    try:
        state = json.loads(STATE_FILE.read_text(encoding="utf-8"))
        if not isinstance(state, dict):
            return new_state(steps)
    except (OSError, json.JSONDecodeError):
        return new_state(steps)
    state, mutated = sync_definition_into_state(steps, state)
    if mutated:
        save_state(state)
    return state


def is_ready() -> bool:
    if not STATE_FILE.is_file():
        return False
    try:
        payload = json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    return bool(isinstance(payload, dict) and payload.get("isReady"))


def set_step_status(
    state: Dict[str, Any],
    step_id: str,
    status: str,
    error_message: str = "",
) -> None:
    for item in state.get("stepStates") or []:
        if item.get("stepId") == step_id:
            item["status"] = status
            item["errorMessage"] = error_message
            return
    state.setdefault("stepStates", []).append(
        {"stepId": step_id, "status": status, "errorMessage": error_message},
    )


def record_inputs(state: Dict[str, Any], step_id: str, inputs: Dict[str, Any]) -> None:
    state.setdefault("inputsByStep", {})[step_id] = dict(inputs)


def refresh_ready(state: Dict[str, Any], definition: Optional[List[Dict[str, Any]]] = None) -> None:
    steps = definition if definition is not None else _definition()
    by_id = {
        item.get("stepId"): str(item.get("status") or STATUS_NOT_STARTED)
        for item in (state.get("stepStates") or [])
    }
    state["isReady"] = bool(steps) and all(
        by_id.get(step.get("id")) == STATUS_SUCCESS for step in steps
    )


def record_step(
    step_id: str,
    status: str,
    *,
    error: str = "",
    inputs: Optional[Dict[str, Any]] = None,
    source: str = "cli",
) -> Dict[str, Any]:
    definition = _definition()
    state = load_state(definition)
    state["installSource"] = source
    set_step_status(state, step_id, status, error)
    if inputs is not None:
        record_inputs(state, step_id, inputs)
    refresh_ready(state, definition)
    state["version"] = int(state.get("version", 1)) + 1
    save_state(state)
    return state


def mark_pipeline_complete(
    *,
    source: str,
    inputs_by_step: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    definition = _definition()
    state = load_state(definition)
    if inputs_by_step:
        merged = dict(state.get("inputsByStep") or {})
        merged.update(inputs_by_step)
        state["inputsByStep"] = merged
    skipped = list(state.get("skippedSteps") or [])
    for step in definition:
        step_id = str(step.get("id") or "")
        if not step_id:
            continue
        if step.get("cliSkip"):
            set_step_status(state, step_id, STATUS_SUCCESS)
            state.setdefault("inputsByStep", {}).setdefault(step_id, {"skip": True})
            if step_id not in skipped:
                skipped.append(step_id)
        else:
            set_step_status(state, step_id, STATUS_SUCCESS)
    state["skippedSteps"] = skipped
    state["installSource"] = source
    state["isReady"] = True
    state["version"] = int(state.get("version", 1)) + 1
    save_state(state)
    return state


def mark_pipeline_failed(
    step_id: str,
    error: str,
    *,
    source: str = "cli",
) -> Dict[str, Any]:
    definition = _definition()
    state = load_state(definition)
    set_step_status(state, step_id, STATUS_FAILED, error)
    state["installSource"] = source
    state["isReady"] = False
    state["version"] = int(state.get("version", 1)) + 1
    save_state(state)
    return state
