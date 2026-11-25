"""Setup pipeline state helpers (skip flags + definition migration)."""

from __future__ import annotations

from typing import Any, Dict, List, Tuple

STATUS_SUCCESS = "success"
STATUS_NOT_STARTED = "not_started"


def wants_skip_input(inputs: Dict[str, Any] | None) -> bool:
    """True when the interactive step was submitted as skip (still counts as success)."""
    raw = (inputs or {}).get("skip")
    if isinstance(raw, bool):
        return raw
    if isinstance(raw, (int, float)) and not isinstance(raw, bool):
        return raw != 0
    return str(raw or "").strip().lower() in ("1", "true", "yes", "skip")


def sync_definition_into_state(
    definition: List[Dict[str, Any]],
    state: Dict[str, Any],
    *,
    success_status: str = STATUS_SUCCESS,
    not_started_status: str = STATUS_NOT_STARTED,
) -> Tuple[Dict[str, Any], bool]:
    """
    Ensure ``state.stepStates`` contains every definition step.

    Already-ready sessions get new *optional* steps marked success so they are
    not pulled back into the wizard. Required new steps reset ``isReady``.
    """
    mutated = False
    step_states = list(state.get("stepStates") or [])
    known = {item.get("stepId") for item in step_states}
    was_ready = bool(state.get("isReady"))

    for step in definition:
        step_id = step.get("id")
        if not step_id or step_id in known:
            continue
        optional = bool(step.get("optional"))
        if was_ready and optional:
            status = success_status
        else:
            status = not_started_status
            if was_ready and not optional:
                state["isReady"] = False
        step_states.append(
            {"stepId": step_id, "status": status, "errorMessage": ""},
        )
        known.add(step_id)
        mutated = True

    state["stepStates"] = step_states

    by_id = {
        item.get("stepId"): str(item.get("status") or not_started_status)
        for item in step_states
    }
    if definition:
        all_success = all(by_id.get(step.get("id")) == success_status for step in definition)
        if bool(state.get("isReady")) != all_success:
            state["isReady"] = all_success
            mutated = True

    return state, mutated
