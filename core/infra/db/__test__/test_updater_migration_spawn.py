"""updater ``spawn_database_migration_cli`` 行为（源码在 ``setup/updater/``，不打进 init zip）。"""
from __future__ import annotations

import importlib.util
import os
import sys
import tempfile
from pathlib import Path
from types import ModuleType
from unittest.mock import patch

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[4]
_UPDATER_HELPER = _REPO_ROOT / "setup" / "updater" / "helper.py"


def _load_updater_helper() -> ModuleType:
    name = "ntq_updater_helper"
    spec = importlib.util.spec_from_file_location(name, _UPDATER_HELPER)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load updater helper: {_UPDATER_HELPER}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


helper = _load_updater_helper()


def test_missing_snapshot_raises_by_default():
    with tempfile.TemporaryDirectory() as td:
        repo = Path(td)
        env = os.environ.copy()
        env.pop("NTQ_UPDATE_ALLOW_MISSING_SCHEMA_SNAPSHOT", None)
        with patch.dict(os.environ, env, clear=True):
            with pytest.raises(RuntimeError, match="schema 快照不存在"):
                helper.spawn_database_migration_cli(repo, None)


def test_missing_snapshot_allowed_with_env():
    with tempfile.TemporaryDirectory() as td:
        repo = Path(td)
        with patch.dict(os.environ, {"NTQ_UPDATE_ALLOW_MISSING_SCHEMA_SNAPSHOT": "1"}, clear=False):
            result = helper.spawn_database_migration_cli(repo, None)
        assert result.skipped is True
        assert result.skipped_reason


def test_skip_db_migration_env():
    with patch.dict(os.environ, {"NTQ_UPDATE_SKIP_DB_MIGRATION": "1"}, clear=False):
        result = helper.spawn_database_migration_cli(Path("/tmp/ntq-test-repo"))
    assert result.skipped is True
    assert result.skipped_reason == "NTQ_UPDATE_SKIP_DB_MIGRATION"
