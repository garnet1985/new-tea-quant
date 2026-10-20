"""validate_strategy accepts short meta.key under descriptive demo folders."""

from __future__ import annotations

from core.modules.agent.core.code.tools.strategy.validate_strategy import validate_strategy


def test_nested_demo_accepts_path_and_short_meta_key() -> None:
    # rsi_v2 keeps short meta.key under a descriptive folder.
    full = "demo/regression/rsi/rsi_v2_net_profit_gate"
    by_path = validate_strategy({"key": full})
    assert by_path.get("ok") is True, by_path
    assert full in str(by_path.get("path") or "")

    by_alias = validate_strategy({"key": "rsi_v2"})
    assert by_alias.get("ok") is True, by_alias
    assert full in str(by_alias.get("path") or "")


def test_meta_key_mismatch_still_fails(tmp_path, monkeypatch) -> None:
    from core.modules.agent.core.code.tools.strategy import validate_strategy as mod
    from core.modules.agent.core.code.tools.strategy import _strategy_key as key_mod

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
    monkeypatch.setattr(mod, "strategy_folder", fake_folder)
    # Avoid StrategyHooksLoader needing real package layout
    monkeypatch.setattr(
        mod,
        "_hooks_status",
        lambda *_a, **_k: ("", "H"),
    )
    monkeypatch.setattr(mod, "_bar_attribute_access", lambda *_a, **_k: "")

    out = validate_strategy({"key": "my_strat"})
    assert out.get("ok") is False
    assert any("meta.key" in str(e) for e in (out.get("errors") or []))
