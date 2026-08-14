"""TagPathRules 单元测试。"""

from __future__ import annotations

from pathlib import Path

from core.modules.tag.core.services.discovery.path_rules import TagPathRules


class TestTagPathRules:
    def test_relative_tag_path(self, tmp_path: Path):
        root = tmp_path / "tags"
        folder = root / "demo" / "cap"
        folder.mkdir(parents=True)
        assert TagPathRules.relative_tag_path(folder, root) == "demo/cap"

    def test_machine_readable(self):
        assert TagPathRules.is_machine_readable_path("demo/market_cap_tier") is True
        assert TagPathRules.is_machine_readable_path("demo/市值") is False
        assert TagPathRules.is_machine_readable_path("") is False

    def test_module_id(self):
        assert (
            TagPathRules.tag_module_id("demo/cap", suffix="tag")
            == "_ntq_tag_tag_demo_cap"
        )
