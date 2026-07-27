#!/usr/bin/env python3
"""Tag discovery：递归扫描与 tag_key。"""

from __future__ import annotations

from pathlib import Path

import pytest


from core.infra.project_context.core.path_manager import PathManager
from core.modules.tag.services.discovery import TagDiscoveryHelper


def _minimal_settings(**overrides):
    base = {
        "is_enabled": True,
        "meta": {"display_name": "nested_tag"},
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
    monkeypatch.setattr(PathManager, "get_extensions_root", staticmethod(lambda: us / "extensions"))
    monkeypatch.setattr(PathManager, "get_tags_root", staticmethod(lambda: root))
    return root


def _write_tag(folder: Path, *, meta_key: str | None = None) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    settings = _minimal_settings()
    if meta_key:
        settings["meta"] = {**(settings.get("meta") or {}), "key": meta_key}
    folder.joinpath("settings.py").write_text(
        f"settings = {settings!r}\n",
        encoding="utf-8",
    )
    folder.joinpath("tag_worker.py").write_text(
        "\n".join(
            [
                "from core.modules.tag.engines.shared.base_worker import BaseTagWorker",
                "from core.modules.tag.models.tag_model import TagModel",
                "from typing import Any, Dict, Optional",
                "class NestedTagWorker(BaseTagWorker):",
                "    def calculate_tag(self, as_of_date, historical_data, tag_definition):",
                "        return None",
                "",
            ]
        ),
        encoding="utf-8",
    )


def test_discover_nested_tag(tags_tree: Path):
    target = tags_tree / "demo" / "market_cap_tier"
    _write_tag(target, meta_key="market_cap_tier")

    found = TagDiscoveryHelper.discover_tags(tags_tree)
    assert "demo/market_cap_tier" in found
    assert found["demo/market_cap_tier"].settings_name == "demo/market_cap_tier"
    assert found["demo/market_cap_tier"].module_key == "market_cap_tier"
    assert found["demo/market_cap_tier"].settings["calculation"]["update_mode"] == "incremental"


def test_resolve_by_tag_key(tags_tree: Path):
    _write_tag(tags_tree / "market_cap_tier", meta_key="cap_alias")
    found = TagDiscoveryHelper.discover_tags(tags_tree)
    assert TagDiscoveryHelper.resolve_tag_key("market_cap_tier", found) == "market_cap_tier"
    assert TagDiscoveryHelper.resolve_tag_key("cap_alias", found) == "market_cap_tier"
