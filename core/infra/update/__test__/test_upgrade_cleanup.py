"""升级收尾清理（通过 setup/updater/helper 加载）。"""
from __future__ import annotations

import importlib.util
import sys
import tempfile
from pathlib import Path
from types import ModuleType

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[4]
_HELPER_PATH = _REPO_ROOT / "setup" / "updater" / "helper.py"


def _load_helper() -> ModuleType:
    name = "ntq_updater_helper_cleanup"
    spec = importlib.util.spec_from_file_location(name, _HELPER_PATH)
    if spec is None or spec.loader is None:
        raise ImportError(_HELPER_PATH)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


helper = _load_helper()


def test_cleanup_removes_staging_and_snapshot():
    helper_module = helper
    with tempfile.TemporaryDirectory() as td:
        repo = Path(td)
        bundle = repo / "userspace" / ".ntq" / "update"
        staging = bundle / "staging" / "current"
        staging.mkdir(parents=True)
        (staging / "marker.txt").write_text("x", encoding="utf-8")
        snap = bundle / "cache" / helper_module.PRE_MIRROR_CORE_TABLE_SCHEMAS_FILE
        snap.parent.mkdir(parents=True, exist_ok=True)
        snap.write_text("{}", encoding="utf-8")

        result = helper_module.cleanup_after_upgrade(
            repo,
            staging_dir=staging,
            pre_mirror_snapshot_path=snap,
        )
        assert not result.skipped
        assert not staging.exists()
        assert not snap.exists()
        assert result.removed_paths


def test_cleanup_skip_env():
    with tempfile.TemporaryDirectory() as td:
        repo = Path(td)
        import os
        from unittest.mock import patch

        with patch.dict(os.environ, {"NTQ_UPDATE_SKIP_CLEANUP": "1"}, clear=False):
            result = helper.cleanup_after_upgrade(repo)
        assert result.skipped is True
