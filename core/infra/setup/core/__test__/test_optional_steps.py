from __future__ import annotations

from core.infra.setup.core.cli_runtime import _ordered_cli_steps
from core.infra.setup.core.meta_loader import load_setup_step_meta
from core.infra.setup.core.pipeline_state import sync_definition_into_state, wants_skip_input


def test_wants_skip_input_truthy() -> None:
    assert wants_skip_input({"skip": True}) is True
    assert wants_skip_input({"skip": "yes"}) is True
    assert wants_skip_input({"skip": "1"}) is True
    assert wants_skip_input({"skip": False}) is False
    assert wants_skip_input({"skip": "false"}) is False
    assert wants_skip_input({}) is False
    assert wants_skip_input(None) is False


def test_sync_ready_session_marks_optional_step_success() -> None:
    definition = [
        {"id": "db_connection", "optional": False},
        {"id": "import_data", "optional": True},
        {"id": "resolve_ml_deps", "optional": True},
    ]
    state = {
        "isReady": True,
        "stepStates": [
            {"stepId": "db_connection", "status": "success", "errorMessage": ""},
            {"stepId": "import_data", "status": "success", "errorMessage": ""},
        ],
    }
    next_state, mutated = sync_definition_into_state(definition, state)
    assert mutated is True
    assert next_state["isReady"] is True
    ml = next(item for item in next_state["stepStates"] if item["stepId"] == "resolve_ml_deps")
    assert ml["status"] == "success"


def test_sync_unready_session_adds_optional_as_not_started() -> None:
    definition = [
        {"id": "import_data", "optional": True},
        {"id": "resolve_ml_deps", "optional": True},
    ]
    state = {
        "isReady": False,
        "stepStates": [
            {"stepId": "import_data", "status": "waiting_input", "errorMessage": ""},
        ],
    }
    next_state, mutated = sync_definition_into_state(definition, state)
    assert mutated is True
    assert next_state["isReady"] is False
    ml = next(item for item in next_state["stepStates"] if item["stepId"] == "resolve_ml_deps")
    assert ml["status"] == "not_started"


def test_meta_optional_ml_and_import_pause() -> None:
    steps = load_setup_step_meta(ui_only=True)
    by_id = {step["id"]: step for step in steps}
    assert "import_data" in by_id
    assert "resolve_ml_deps" in by_id
    assert by_id["import_data"].get("requiresUserInput") is True
    assert by_id["import_data"].get("optional") is True
    assert by_id["resolve_ml_deps"].get("requiresUserInput") is True
    assert by_id["resolve_ml_deps"].get("optional") is True
    assert by_id["resolve_ml_deps"].get("cliSkip") is True
    assert by_id["resolve_deps"].get("progressWeight") == 50
    weights = sum(int(step.get("progressWeight") or 0) for step in steps)
    assert weights == 100


def test_cli_steps_skip_ml_but_keep_import() -> None:
    steps = _ordered_cli_steps()
    assert "import_data" in steps
    assert "resolve_ml_deps" not in steps
