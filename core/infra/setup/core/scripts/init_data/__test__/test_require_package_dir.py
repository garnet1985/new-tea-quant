"""演示包目录：userspace 缺失时须给出明确错误。"""

from __future__ import annotations

from pathlib import Path

import pytest

from core.infra.project_context import ProjectContext
from core.infra.project_context.core.path_manager import PathManager
from core.infra.setup.core.scripts.init_data.config import require_package_dir

pytestmark = pytest.mark.force_run


def test_require_package_dir_missing_userspace(tmp_path: Path, monkeypatch) -> None:
    fake_root = tmp_path / "repo"
    fake_root.mkdir()
    missing_us = tmp_path / "no-userspace-yet"
    monkeypatch.setattr(PathManager, "_root_cache", fake_root)
    monkeypatch.setattr(PathManager, "_userspace_cache", missing_us)
    ProjectContext.cache.clear_userspace_cache()
    monkeypatch.setattr(PathManager, "_userspace_cache", missing_us)
    with pytest.raises(RuntimeError, match="需要先有 userspace 文件夹"):
        require_package_dir()


def test_require_package_dir_creates_package_folder(tmp_path: Path, monkeypatch) -> None:
    fake_root = tmp_path / "repo"
    us = tmp_path / "userspace"
    us.mkdir()
    monkeypatch.setattr(PathManager, "_root_cache", fake_root)
    ProjectContext.cache.clear_userspace_cache()
    monkeypatch.setattr(PathManager, "_userspace_cache", us)
    out = require_package_dir()
    assert out == us / ".ntq" / "packages" / "install_demo"
    assert out.is_dir()
