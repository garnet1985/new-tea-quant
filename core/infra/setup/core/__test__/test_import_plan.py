"""设置页导入选包计划。"""

from __future__ import annotations

from pathlib import Path

import pytest

from core.infra.membership import Membership
from core.infra.project_context import ProjectContext
from core.infra.project_context.core.path_manager import PathManager
from core.infra.setup.core.import_plan import build_import_plan, resolve_import_pack_kind

pytestmark = pytest.mark.force_run


@pytest.fixture
def userspace(tmp_path: Path, monkeypatch):
    us = tmp_path / "userspace"
    (us / "system" / "membership").mkdir(parents=True)
    monkeypatch.setattr(PathManager, "_userspace_cache", us)
    ProjectContext.cache.clear_userspace_cache()
    monkeypatch.setattr(PathManager, "_userspace_cache", us)
    monkeypatch.setattr(
        PathManager,
        "get_membership_token_file",
        staticmethod(lambda: us / "system" / "membership" / "membership_token.txt"),
    )
    return us


def test_plan_defaults_to_demo_without_token(userspace: Path) -> None:
    Membership.clear()
    assert resolve_import_pack_kind() == "demo"
    plan = build_import_plan()
    assert plan["packKind"] == "demo"
    assert plan["membershipConfigured"] is False
    assert plan["usesJobPipeline"] is False
    assert plan["warning"]
    assert "300" in plan["packLabel"]
    assert plan["confirmActionLabel"] == "仍导入演示包"


def test_plan_uses_member_when_token_present(userspace: Path) -> None:
    token = "ntq_" + "ab" * 24
    assert Membership.save(token) is None
    plan = build_import_plan()
    assert plan["packKind"] == "member"
    assert plan["membershipConfigured"] is True
    assert plan["usesJobPipeline"] is True
    assert plan["warning"] is None
    assert "全 A" in plan["packLabel"]
    assert plan["confirmActionLabel"] == "开始导入"
