"""演示包目录：userspace 缺失时须给出明确错误。"""

from __future__ import annotations

from pathlib import Path

import pytest

from core.infra.project_context import ProjectContext
from core.infra.setup.core.steps.import_data.data_packages import require_package_dir

pytestmark = pytest.mark.force_run


def test_require_package_dir_missing_userspace(tmp_path: Path, monkeypatch) -> None:
    missing_us = tmp_path / "no-userspace-yet"
    monkeypatch.setenv("NTQ_USERSPACE_ROOT", str(missing_us))
    ProjectContext.cache.clear_userspace_cache()
    try:
        with pytest.raises(RuntimeError, match="需要先有 userspace 文件夹"):
            require_package_dir()
    finally:
        ProjectContext.cache.clear_userspace_cache()


def test_require_package_dir_creates_package_folder(tmp_path: Path, monkeypatch) -> None:
    us = tmp_path / "userspace"
    us.mkdir()
    monkeypatch.setenv("NTQ_USERSPACE_ROOT", str(us))
    ProjectContext.cache.clear_userspace_cache()
    try:
        out = require_package_dir()
        assert out == us / ".ntq" / "packages" / "demo"
        assert out.is_dir()

        member = require_package_dir("member")
        assert member == us / ".ntq" / "packages" / "member"
        assert member.is_dir()
    finally:
        ProjectContext.cache.clear_userspace_cache()
