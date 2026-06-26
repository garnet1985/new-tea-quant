#!/usr/bin/env python3
import json
from pathlib import Path

import pytest

from core.infra.project_context.config_merge_policies import merge_market_profile_dicts
from core.infra.project_context.discovery_manager import (
    DiscoveryManager,
    OverridableConfigNotFoundError,
)


@pytest.fixture
def discovery_dirs(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    core_root = tmp_path / "core" / "default_config"
    user_root = tmp_path / "userspace" / "config"
    rel = core_root / "markets"
    urel = user_root / "markets"
    rel.mkdir(parents=True)
    urel.mkdir(parents=True)
    monkeypatch.setattr(
        "core.infra.project_context.discovery_manager.PathManager.default_config",
        lambda: core_root,
    )
    monkeypatch.setattr(
        "core.infra.project_context.discovery_manager.PathManager.user_config",
        lambda: user_root,
    )
    return rel, urel


class TestDiscoveryManager:
    def test_discover_configs_union(self, discovery_dirs):
        core_dir, user_dir = discovery_dirs
        (core_dir / "a.json").write_text("{}", encoding="utf-8")
        (user_dir / "b.json").write_text("{}", encoding="utf-8")
        assert DiscoveryManager.discover_configs("markets") == ["a", "b"]

    def test_discover_config_paths(self, discovery_dirs):
        core_dir, user_dir = discovery_dirs
        (core_dir / "p.json").write_text("{}", encoding="utf-8")
        found = DiscoveryManager.discover_config("markets", "p")
        assert found.core_path == core_dir / "p.json"
        assert found.user_path is None
        assert found.exists

    def test_load_with_merge_fn(self, discovery_dirs):
        core_dir, user_dir = discovery_dirs
        core = {"rules": {"x": {"default_ratio": 0.1, "rules": [{"key": "k", "ratio": 0.2}]}}}
        user = {"rules": {"x": {"default_ratio": 0.11}}}
        (core_dir / "p.json").write_text(json.dumps(core), encoding="utf-8")
        (user_dir / "p.json").write_text(json.dumps(user), encoding="utf-8")
        out = DiscoveryManager.load_overridable_config(
            "markets", "p", merge_fn=merge_market_profile_dicts
        )
        assert out["rules"]["x"]["default_ratio"] == 0.11
        assert out["rules"]["x"]["rules"][0]["ratio"] == 0.2

    def test_missing_raises(self, discovery_dirs):
        with pytest.raises(OverridableConfigNotFoundError):
            DiscoveryManager.load_overridable_config(
                "markets", "missing", merge_fn=merge_market_profile_dicts
            )

    def test_root_domain_load(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
        core_root = tmp_path / "core" / "default_config"
        user_root = tmp_path / "userspace" / "config"
        core_root.mkdir(parents=True, exist_ok=True)
        user_root.mkdir(parents=True, exist_ok=True)
        monkeypatch.setattr(
            "core.infra.project_context.discovery_manager.PathManager.get_default_config_root",
            lambda: core_root,
        )
        monkeypatch.setattr(
            "core.infra.project_context.discovery_manager.PathManager.get_user_config_root",
            lambda: user_root,
        )
        (core_root / "data.json").write_text('{"a": 1}', encoding="utf-8")
        out = DiscoveryManager.load_overridable_config("", "data")
        assert out["a"] == 1
