"""upgrade_entry 交互逻辑。"""
from __future__ import annotations

import importlib.util
import sys
import tempfile
from pathlib import Path
from types import ModuleType
from unittest.mock import patch

import pytest

_REPO = Path(__file__).resolve().parents[4]
_ENTRY = _REPO / "setup" / "updater" / "upgrade_entry.py"


def _load_entry() -> ModuleType:
    updater_dir = _REPO / "setup" / "updater"
    upd = str(updater_dir)
    if upd not in sys.path:
        sys.path.insert(0, upd)
    name = "ntq_upgrade_entry_test"
    spec = importlib.util.spec_from_file_location(name, _ENTRY)
    if spec is None or spec.loader is None:
        raise ImportError(_ENTRY)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def test_already_latest_message():
    entry = _load_entry()
    with tempfile.TemporaryDirectory() as td:
        repo = Path(td)
        (repo / "core").mkdir(parents=True)
        (repo / "core" / "system.json").write_text(
            '{"version": "1.0.0"}', encoding="utf-8"
        )
        with patch.object(entry, "check_remote_has_newer_version", return_value=None):
            code = entry.run_interactive_upgrade(repo)
    assert code == 0


def test_cancel_on_empty_input():
    entry = _load_entry()
    with tempfile.TemporaryDirectory() as td:
        repo = Path(td)
        (repo / "core").mkdir(parents=True)
        (repo / "core" / "system.json").write_text(
            '{"version": "1.0.0"}', encoding="utf-8"
        )
        with patch.object(entry, "check_remote_has_newer_version", return_value="2.0.0"), patch(
            "builtins.input", return_value=""
        ), patch.object(entry, "run_upgrade_pipeline") as mock_run:
            code = entry.run_interactive_upgrade(repo)
    assert code == 0
    mock_run.assert_not_called()
