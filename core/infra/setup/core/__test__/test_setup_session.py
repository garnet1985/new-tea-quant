from __future__ import annotations

import json
from pathlib import Path

from core.infra.setup.core import setup_session
from core.infra.setup.core.meta_loader import load_setup_step_meta


def test_cli_complete_marks_wizard_ready(tmp_path: Path, monkeypatch) -> None:
    state_file = tmp_path / "setup-runtime.json"
    monkeypatch.setattr(setup_session, "STATE_FILE", state_file)

    setup_session.mark_pipeline_complete(source="cli")
    state = json.loads(state_file.read_text(encoding="utf-8"))
    assert state["isReady"] is True
    assert state["installSource"] == "cli"
    assert setup_session.is_ready() is True

    definition = load_setup_step_meta(ui_only=True)
    by_id = {item["stepId"]: item for item in state["stepStates"]}
    for step in definition:
        assert by_id[step["id"]]["status"] == "success"
    assert state["inputsByStep"]["resolve_ml_deps"]["skip"] is True


def test_ui_and_cli_share_same_state_file(tmp_path: Path, monkeypatch) -> None:
    state_file = tmp_path / "setup-runtime.json"
    monkeypatch.setattr(setup_session, "STATE_FILE", state_file)
    setup_session.mark_pipeline_complete(source="cli")
    loaded = setup_session.load_state()
    assert loaded["isReady"] is True
    assert loaded["installSource"] == "cli"
