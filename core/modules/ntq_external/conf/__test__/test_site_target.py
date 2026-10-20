"""官网 base_url：membership.json / 默认。"""

from __future__ import annotations

from pathlib import Path

import pytest

from core.infra.project_context.core.path_manager import PathManager
from core.modules.ntq_external.conf import site_target

pytestmark = pytest.mark.force_run


@pytest.fixture
def config_root(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(
        PathManager,
        "get_user_config_root",
        staticmethod(lambda: tmp_path),
    )
    return tmp_path


def test_default_is_production(config_root):
    assert site_target.base_url() == site_target.DEFAULT_BASE_URL
    assert site_target.ai_base_url().endswith("/api/v1/ntq-ai")
    assert site_target.member_profile_url().startswith(site_target.DEFAULT_BASE_URL)


def test_membership_json_base_url_drives_all(config_root: Path):
    (config_root / "membership.json").write_text(
        '{"base_url": "http://localhost:2026"}',
        encoding="utf-8",
    )
    assert site_target.base_url() == "http://127.0.0.1:2026"
    assert site_target.ai_base_url() == "http://127.0.0.1:2026/api/v1/ntq-ai"
    assert site_target.member_profile_url() == (
        "http://127.0.0.1:2026/api/v1/ntq-member/profile"
    )
    assert site_target.register_url() == "http://127.0.0.1:2026/zh-hans/user/register"
