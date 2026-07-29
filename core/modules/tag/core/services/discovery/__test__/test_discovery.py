"""Tag discovery：递归扫描与 meta.key 解析。"""

from __future__ import annotations

from pathlib import Path

import pytest

from core.infra.project_context.core.path_manager import PathManager
from core.modules.tag.core.services.discovery import DiscoveryService


def _minimal_settings(**overrides):
    base = {
        "is_enabled": True,
        "meta": {"key": "nested_tag", "display_name": "nested_tag"},
        "calculation": {
            "update_mode": "incremental",
            "execution": {"mode": "entity_based"},
        },
        "data": {
            "base": {
                "data_key": "stock.kline.daily",
                "params": {"adjust": "qfq"},
            },
            "required": [],
            "min_required_records": 1,
        },
        "tag_definitions": [{"name": "nested_tag"}],
    }
    for key, value in overrides.items():
        if key in ("calculation", "data", "meta") and isinstance(value, dict):
            base[key] = {**base.get(key, {}), **value}
        else:
            base[key] = value
    return base


@pytest.fixture
def tags_tree(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    us = tmp_path / "userspace"
    root = us / "extensions" / "tags"
    root.mkdir(parents=True)
    monkeypatch.setattr(
        PathManager, "get_extensions_root", staticmethod(lambda: us / "extensions")
    )
    monkeypatch.setattr(PathManager, "get_tags_root", staticmethod(lambda: root))
    return root


def _write_tag(
    folder: Path,
    *,
    meta_key: str = "nested_tag",
    is_enabled: bool = True,
) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    settings = _minimal_settings(
        is_enabled=is_enabled,
        meta={"key": meta_key, "display_name": meta_key},
    )
    folder.joinpath("settings.py").write_text(
        f"settings = {settings!r}\n",
        encoding="utf-8",
    )
    folder.joinpath("tag.py").write_text(
        "\n".join(
            [
                "from core.modules.tag.core.engines.per_entity.shared.hooks.tag_hooks import TagHooks",
                "",
                "class NestedTagHooks(TagHooks):",
                "    def calculate_tag(self, ctx):",
                "        return None",
                "",
            ]
        ),
        encoding="utf-8",
    )


class TestDiscoveryService:
    def test_discover_nested_tag(self, tags_tree: Path):
        target = tags_tree / "demo" / "market_cap_tier"
        _write_tag(target, meta_key="market_cap_tier")

        found = DiscoveryService.discover_tags()
        by_id = {t.id(): t for t in found}
        assert "demo/market_cap_tier" in by_id
        info = by_id["demo/market_cap_tier"]
        assert info.key == "market_cap_tier"
        assert info.is_enabled is True
        assert info.settings["calculation"]["update_mode"] == "incremental"
        assert info.hooks_class is not None

    def test_find_by_meta_key_and_path(self, tags_tree: Path):
        _write_tag(tags_tree / "market_cap_tier", meta_key="cap_alias")
        assert DiscoveryService.find_tag("market_cap_tier") is not None
        assert DiscoveryService.find_tag("cap_alias") is not None
        assert DiscoveryService.find_tag("cap_alias").id() == "market_cap_tier"

    def test_skips_disabled(self, tags_tree: Path):
        _write_tag(tags_tree / "disabled_tag", meta_key="disabled_tag", is_enabled=False)
        assert DiscoveryService.find_tag("disabled_tag") is None
        all_tags = DiscoveryService.discover_tags()
        assert any(t.key == "disabled_tag" for t in all_tags)
        assert DiscoveryService.list_enabled_keys() == []

    def test_skips_underscore_dirs(self, tags_tree: Path):
        _write_tag(tags_tree / "_template" / "empty", meta_key="template_tag")
        found = DiscoveryService.discover_tags()
        assert found == []

    def test_duplicate_meta_key_skips_second(self, tags_tree: Path):
        _write_tag(tags_tree / "a", meta_key="dup")
        _write_tag(tags_tree / "b", meta_key="dup")
        found = DiscoveryService.discover_tags()
        assert len([t for t in found if t.key == "dup"]) == 1
