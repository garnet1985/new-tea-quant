"""静态数据包本地缓存（demo / member / full）。"""

from __future__ import annotations

from pathlib import Path

import pytest

from core.infra.project_context import ProjectContext
from core.infra.project_context.core.path_manager import PathManager
from core.infra.setup.core.steps.import_data import data_packages as dp

pytestmark = pytest.mark.force_run


@pytest.fixture
def userspace(tmp_path: Path, monkeypatch):
    us = tmp_path / "userspace"
    us.mkdir()
    monkeypatch.setattr(PathManager, "_userspace_cache", us)
    ProjectContext.cache.clear_userspace_cache()
    monkeypatch.setattr(PathManager, "_userspace_cache", us)
    return us


def test_require_package_dir_by_kind(userspace: Path) -> None:
    demo = dp.require_package_dir("demo")
    member = dp.require_package_dir("member")
    full = dp.require_package_dir("full")
    assert demo == userspace / ".ntq" / "packages" / "demo"
    assert member == userspace / ".ntq" / "packages" / "member"
    assert full == userspace / ".ntq" / "packages" / "full"
    assert demo.is_dir() and member.is_dir() and full.is_dir()


def test_describe_and_clear_packages(userspace: Path) -> None:
    demo_dir = dp.require_package_dir("demo")
    (demo_dir / dp.package_zip_name("demo")).write_bytes(b"PK\x03\x04x" * 100)
    summary = dp.describe_data_packages()
    assert summary["demoPresent"] is True
    assert summary["packages"]["demo"]["present"] is True
    assert summary["packages"]["member"]["present"] is False

    removed = dp.clear_static_data_packages()
    assert removed >= 1
    assert dp.find_local_package_zip("demo") is None
