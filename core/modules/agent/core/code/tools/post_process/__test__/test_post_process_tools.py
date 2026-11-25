"""Agent post_process tools：薄封装。"""

from __future__ import annotations

from pathlib import Path

import pytest

from core.modules.agent.core.code.tools.post_process.create_adapter import (
    create_post_process_adapter,
)


@pytest.fixture()
def adapters_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    root = tmp_path / "extensions" / "post_process"
    adapters = root / "adapters"
    tmpl = root / "_template" / "empty_adapter"
    tmpl.mkdir(parents=True)
    adapters.mkdir(parents=True)
    (tmpl / "adapter.py").write_text(
        "from core.modules.post_process.contracts import BaseAdapter, ScanSessionReport\n"
        "from typing import Any, Dict\n"
        "class EmptyAdapter(BaseAdapter):\n"
        "    def run(self, session, config, deps): pass\n",
        encoding="utf-8",
    )
    (tmpl / "settings.py").write_text(
        'settings = {"display_name": "空"}\n', encoding="utf-8"
    )
    monkeypatch.setattr(
        "core.infra.project_context.ProjectContext.path.get_post_process_extensions_directory",
        lambda: root,
    )
    monkeypatch.setattr(
        "core.infra.project_context.ProjectContext.path.get_adapters_directory",
        lambda: adapters,
    )
    return adapters


def test_agent_create_adapter(adapters_root: Path) -> None:
    created = create_post_process_adapter({"name": "agent_ad"})
    assert created.get("ok") is True, created
    assert (adapters_root / "agent_ad" / "adapter.py").is_file()


def test_set_post_processor_enabled_delegates(monkeypatch: pytest.MonkeyPatch) -> None:
    from core.modules.agent.core.code.tools.post_process import enable as enable_mod

    called: dict = {}

    def fake_set(key: str, enabled: bool):
        called["key"] = key
        called["enabled"] = enabled
        return {"key": key, "is_enabled": enabled}

    monkeypatch.setattr(enable_mod.PostProcess, "set_enabled", staticmethod(fake_set))
    out = enable_mod.set_post_processor_enabled(
        {"key": "presenter", "is_enabled": False}
    )
    assert out.get("ok") is True, out
    assert called == {"key": "presenter", "enabled": False}


def test_post_process_run_enabled_roundtrip(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from core.modules.agent.core.code.tools.post_process import enable as enable_mod
    from core.modules.post_process.core import run_prefs as prefs_mod

    prefs = tmp_path / "prefs"
    prefs.mkdir()
    monkeypatch.setattr(
        "core.infra.project_context.ProjectContext.path.get_user_prefs_root",
        lambda: prefs,
    )
    off = enable_mod.set_post_process_run_enabled({"enabled": False})
    assert off.get("ok") is True, off
    assert prefs_mod.RunPrefs.is_enabled() is False
    got = enable_mod.get_post_process_run_enabled({})
    assert got.get("ok") is True and got.get("enabled") is False
    on = enable_mod.set_post_process_run_enabled({"enabled": True})
    assert on.get("ok") is True, on
    assert enable_mod.get_post_process_run_enabled({}).get("enabled") is True
