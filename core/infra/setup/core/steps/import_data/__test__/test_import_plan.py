"""设置页导入选包计划。"""

from __future__ import annotations

from pathlib import Path

import pytest

from core.infra.membership import Membership
from core.infra.project_context import ProjectContext
from core.infra.setup.core.steps.import_data.import_plan import (
    build_import_plan,
    resolve_import_pack_kind,
)

pytestmark = pytest.mark.force_run


@pytest.fixture
def userspace(tmp_path: Path, monkeypatch):
    us = tmp_path / "userspace"
    token_dir = us / "system" / "membership"
    token_dir.mkdir(parents=True)
    token_file = token_dir / "membership_token.txt"
    monkeypatch.setenv("NTQ_USERSPACE_ROOT", str(us))
    ProjectContext.cache.clear_userspace_cache()
    monkeypatch.setattr(
        ProjectContext.path,
        "get_membership_token_file",
        staticmethod(lambda: token_file),
    )
    yield us
    ProjectContext.cache.clear_userspace_cache()


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
