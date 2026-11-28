"""PackageFetcher 注入：无官网硬依赖。"""

from __future__ import annotations

from pathlib import Path

import pytest

from core.infra.project_context import ProjectContext
from core.infra.setup import Setup
from core.infra.setup.core.shared import package_fetch as pf
from core.infra.setup.core.steps.import_data.data_packages import (
    MEMBER_MANIFEST_NAME,
    member_parts_complete,
)
from core.infra.setup.core.steps.import_data.installer import SetupDataInstaller

pytestmark = pytest.mark.force_run


@pytest.fixture
def userspace(tmp_path: Path, monkeypatch):
    us = tmp_path / "userspace"
    us.mkdir()
    monkeypatch.setenv("NTQ_USERSPACE_ROOT", str(us))
    monkeypatch.delenv(pf.PACKAGE_FETCHER_ENV, raising=False)
    ProjectContext.cache.clear_userspace_cache()
    pf.set_package_fetcher(None)
    yield us
    pf.set_package_fetcher(None)
    ProjectContext.cache.clear_userspace_cache()


def test_member_parts_complete_local(userspace: Path) -> None:
    dest = userspace / ".ntq" / "packages" / "member"
    dest.mkdir(parents=True)
    part = dest / "data_member_3y_part1.zip"
    part.write_bytes(b"x" * 10)
    (dest / MEMBER_MANIFEST_NAME).write_text(
        '{"parts":[{"file":"data_member_3y_part1.zip","size_bytes":10}]}',
        encoding="utf-8",
    )
    assert member_parts_complete(dest) is True


def test_ensure_demo_without_fetcher_errors(userspace: Path) -> None:
    inst = SetupDataInstaller(pack_kind="demo", table_prefix="")
    with pytest.raises(RuntimeError, match="本地没有可用"):
        inst.ensure_demo_package(force_download=False)


def test_ensure_demo_uses_injected_fetcher(userspace: Path) -> None:
    called = {}

    def fake_fetch(kind, dest_dir, *, force=False, on_progress=None):
        called["kind"] = kind
        dest = Path(dest_dir)
        dest.mkdir(parents=True, exist_ok=True)
        path = dest / "data_demo.zip"
        path.write_bytes(b"PK\x03\x04fake")
        if on_progress:
            on_progress(4, 4)
        return path

    Setup.runtime.set_package_fetcher(fake_fetch)
    inst = SetupDataInstaller(pack_kind="demo", table_prefix="")
    out = inst.ensure_demo_package(force_download=True)
    assert called["kind"] == "demo"
    assert out.is_file()
