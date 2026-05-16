from __future__ import annotations

import json
from pathlib import Path

import pytest

from setup import install_runtime as ir


def _write_ready_state(path: Path, *, req: Path) -> None:
    req_hash = ir.sha256_file(req)
    payload: dict = {
        "coreVersion": ir.system_meta.version,
        "cliRuntime": {"lastStatus": "success", "lastFailedStepId": ""},
        "uiRuntime": {"lastStatus": "success", "lastFailedStepId": ""},
        "cli": {"requirementsHash": req_hash},
        "python": {"uiRequirementsHash": ir.sha256_file(ir.UI_BFF_REQUIREMENTS)},
        "node": {"fedLockHash": ir.sha256_file(ir.UI_FED_LOCKFILE)},
    }
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_needs_install_common_when_state_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    state_dir = tmp_path / ".ntq"
    state_dir.mkdir()
    monkeypatch.setattr(ir, "STATE_FILE", state_dir / "install-state.json")
    monkeypatch.setattr(ir, "userspace_ready", lambda: True)
    assert ir.needs_install("cli") is True
    assert ir.needs_install("ui") is True


def test_needs_install_cli_false_when_ready(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "requirements.txt").write_text("pandas\n", encoding="utf-8")
    state_dir = repo / ".ntq"
    state_dir.mkdir()
    state_file = state_dir / "install-state.json"
    _write_ready_state(state_file, req=repo / "requirements.txt")

    monkeypatch.setattr(ir, "STATE_FILE", state_file)
    monkeypatch.setattr(ir, "REQUIREMENTS", repo / "requirements.txt")
    monkeypatch.setattr(ir, "userspace_ready", lambda: True)
    assert ir.needs_install("cli") is False


def test_needs_install_ui_false_when_ready_production_build(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    fed_build = repo / "fed_build"
    fed_build.mkdir()
    (fed_build / "index.html").write_text("<html></html>", encoding="utf-8")
    (fed_build / "asset-manifest.json").write_text("{}", encoding="utf-8")

    state_dir = repo / ".ntq"
    state_dir.mkdir()
    state_file = state_dir / "install-state.json"
    bff_req = repo / "bff-req.txt"
    bff_req.write_text("flask\n", encoding="utf-8")

    monkeypatch.delenv("NTQ_UI_DEV", raising=False)
    monkeypatch.setattr(ir, "STATE_FILE", state_file)
    monkeypatch.setattr(ir, "UI_BFF_REQUIREMENTS", bff_req)
    monkeypatch.setattr(ir, "UI_FED_BUILD_DIR", fed_build)
    monkeypatch.setattr(ir, "UI_FED_BUILD_INDEX", fed_build / "index.html")
    monkeypatch.setattr(ir, "userspace_ready", lambda: True)

    fp = ir.fed_build_fingerprint()
    state_file.write_text(
        json.dumps(
            {
                "coreVersion": ir.system_meta.version,
                "python": {"uiRequirementsHash": ir.sha256_file(bff_req)},
                "uiRuntime": {"lastStatus": "success", "lastFailedStepId": ""},
                "fedBuild": {"buildFingerprint": fp},
            }
        ),
        encoding="utf-8",
    )
    assert ir.needs_install("ui") is False
