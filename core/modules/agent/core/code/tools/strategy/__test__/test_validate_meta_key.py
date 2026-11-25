"""validate_strategy accepts short meta.key under descriptive nested folders."""

from __future__ import annotations

from pathlib import Path

from core.modules.agent.core.code.tools.strategy.validate_strategy import validate_strategy


def _write_nested_strategy(root: Path, *, folder_key: str, meta_key: str) -> Path:
    folder = root / "strategies" / Path(folder_key)
    folder.mkdir(parents=True)
    (folder / "strategy.py").write_text(
        "from core.modules.strategy.contracts import StrategyHooks\n"
        "class H(StrategyHooks):\n"
        "    def is_opportunity(self, *a, **k):\n"
        "        return False\n",
        encoding="utf-8",
    )
    (folder / "settings.py").write_text(
        "settings = {\n"
        '  "is_enabled": True,\n'
        f'  "meta": {{"key": "{meta_key}", "display_name": "{meta_key}"}}\n'
        "}\n",
        encoding="utf-8",
    )
    return folder


def test_nested_demo_accepts_path_and_short_meta_key(tmp_path, monkeypatch) -> None:
    from core.modules.agent.core.code.tools.strategy import _strategy_key as key_mod
    from core.modules.strategy import Strategy
    from core.modules.strategy.core.services.artifact_ops import ops as artifact_ops

    full = "demo/nested/rsi/rsi_v2_net_profit_gate"
    short = "rsi_v2"
    folder = _write_nested_strategy(tmp_path, folder_key=full, meta_key=short)

    def fake_folder(key: str):
        if key in (full, short, f"strategies/{full}"):
            return folder, f"strategies/{full}"
        raise FileNotFoundError(key)

    monkeypatch.setattr(key_mod, "strategy_folder", fake_folder)
    monkeypatch.setattr(
        artifact_ops.StrategyArtifactOps,
        "_folder_for_key",
        classmethod(lambda cls, key: fake_folder(key)),
    )
    def fake_resolve_folder(key: str):
        if key in (full, short):
            return folder
        raise FileNotFoundError(key)

    # 短 meta.key 通过发现解析到同一目录时视为对齐
    monkeypatch.setattr(Strategy, "resolve_folder", staticmethod(fake_resolve_folder))
    monkeypatch.setattr(
        artifact_ops.StrategyArtifactOps,
        "_hooks_status",
        classmethod(lambda *_a, **_k: ("", "H")),
    )
    monkeypatch.setattr(
        artifact_ops.StrategyArtifactOps,
        "_bar_attribute_access",
        classmethod(lambda *_a, **_k: ""),
    )

    by_path = validate_strategy({"key": full})
    assert by_path.get("ok") is True, by_path
    assert full in str(by_path.get("path") or "")

    by_alias = validate_strategy({"key": short})
    assert by_alias.get("ok") is True, by_alias
    assert full in str(by_alias.get("path") or "")


def test_meta_key_mismatch_still_fails(tmp_path, monkeypatch) -> None:
    from core.modules.agent.core.code.tools.strategy import _strategy_key as key_mod
    from core.modules.strategy.core.services.artifact_ops import ops as artifact_ops

    folder = tmp_path / "strategies" / "my_strat"
    folder.mkdir(parents=True)
    (folder / "strategy.py").write_text(
        "from core.modules.strategy.contracts import StrategyHooks\n"
        "class H(StrategyHooks):\n"
        "    def is_opportunity(self, *a, **k):\n"
        "        return False\n",
        encoding="utf-8",
    )
    (folder / "settings.py").write_text(
        'settings = {"is_enabled": True, "meta": {"key": "other_name"}}\n',
        encoding="utf-8",
    )

    def fake_folder(key: str):
        return folder, f"strategies/{key}"

    monkeypatch.setattr(key_mod, "strategy_folder", fake_folder)
    monkeypatch.setattr(
        artifact_ops.StrategyArtifactOps,
        "_folder_for_key",
        classmethod(lambda cls, key: (folder, f"strategies/{key}")),
    )
    monkeypatch.setattr(
        artifact_ops.StrategyArtifactOps,
        "_hooks_status",
        classmethod(lambda *_a, **_k: ("", "H")),
    )
    monkeypatch.setattr(
        artifact_ops.StrategyArtifactOps,
        "_bar_attribute_access",
        classmethod(lambda *_a, **_k: ""),
    )

    out = validate_strategy({"key": "my_strat"})
    assert out.get("ok") is False
    assert any("meta.key" in str(e) for e in (out.get("errors") or []))
