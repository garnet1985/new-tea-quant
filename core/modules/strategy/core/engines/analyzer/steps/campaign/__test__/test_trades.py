"""战役单笔铺平 → XGB 二分类。"""
from __future__ import annotations

from typing import Any

import pytest

from core.modules.strategy.core.engines.analyzer.steps.campaign.trades import (
    TradesBase,
    TradesStep,
)

pytestmark = pytest.mark.force_run


def _row(
    vid: str,
    rsi_th: float,
    pe: Any,
    rsi: float,
    pe_pct: float,
    win: bool,
    *,
    group: str = "",
) -> dict:
    return {
        "version_id": vid,
        "knobs": {
            "core.rsi_oversold_threshold": rsi_th,
            "core.max_pe_percentile": pe,
        },
        "capture": {"rsi14": rsi, "pe_percentile": pe_pct},
        "group": group,
        "roi": 0.1 if win else -0.05,
        "win": win,
    }


def test_trades_from_rows_fits_classifier() -> None:
    pytest.importorskip("xgboost")
    pytest.importorskip("shap")
    rows = []
    for i in range(100):
        rsi = 12.0 + (i % 25)
        rows.append(
            _row(
                "21" if i % 2 == 0 else "22",
                20.0 if i % 2 == 0 else 25.0,
                30.0 if i % 3 else None,
                rsi,
                10.0 + (i % 40),
                rsi < 22,
            )
        )
    out = TradesStep.from_rows(
        rows,
        versions=["21", "22"],
        knob_paths=["core.rsi_oversold_threshold", "core.max_pe_percentile"],
    )
    assert out.get("n_versions") == 2
    assert out.get("n_parameter") >= 1
    assert out.get("n_opportunity") >= 1
    assert out.get("status") in ("ok", "partial")
    assert (out.get("shap") or {}).get("status") == "ok"


def test_trades_skips_too_few_features() -> None:
    rows = [
        _row("21", 20, 30, 18.0, 10.0, True),
        _row("21", 20, 30, 18.0, 10.0, False),
    ]
    out = TradesStep.from_rows(
        rows,
        versions=["21"],
        knob_paths=["core.rsi_oversold_threshold"],
    )
    assert out["status"] == "skipped"
    assert out["reason"] == "insufficient_varying_fields"


def test_trades_skip_or_fit_with_enough_rows() -> None:
    rows = []
    for i in range(100):
        rsi = 12.0 + (i % 25)
        rows.append(
            _row(
                "21" if i % 2 == 0 else "22",
                20.0 if i % 2 == 0 else 25.0,
                30.0 if i % 3 else None,
                rsi,
                10.0 + (i % 40),
                rsi < 22,
            )
        )
    out = TradesStep.from_rows(
        rows,
        versions=["21", "22"],
        knob_paths=["core.rsi_oversold_threshold", "core.max_pe_percentile"],
    )
    assert out.get("n_parameter") >= 1
    assert out.get("n_opportunity") >= 1
    if out.get("status") == "skipped":
        assert out.get("reason") == "missing_dependency"
        return
    assert out.get("status") in ("ok", "partial")


def test_trades_keeps_knob_off_and_drops_ohlcv() -> None:
    rows = []
    for i in range(40):
        rows.append(
            {
                "version_id": "21" if i < 20 else "26",
                "knobs": {
                    "core.max_pe_percentile": 30 if i < 20 else None,
                    "core.rsi_oversold_threshold": 20,
                },
                "capture": {
                    "open": 10.0 + i,
                    "close": 11.0 + i,
                    "rsi14": 12.0 + (i % 10),
                    "pe_percentile": 8.0 + i,
                    "stock.finance.quarterly.roe": 0.1 + i * 0.01,
                },
                "roi": 0.1 if i % 2 == 0 else -0.05,
                "win": i % 2 == 0,
            }
        )
    names, kinds = TradesBase._feature_spec(
        rows,
        ["core.max_pe_percentile", "core.rsi_oversold_threshold"],
    )
    assert "core.max_pe_percentile" in names
    assert "core.rsi_oversold_threshold" not in names
    assert "rsi14" in names
    assert "pe_percentile" in names
    assert "open" not in names
    assert "close" not in names
    assert "stock.finance.quarterly.roe" not in names
    assert kinds.count("parameter") == 1


def test_trades_grouped_split_from_group_key() -> None:
    pytest.importorskip("xgboost")
    pytest.importorskip("shap")
    rows = []
    for i in range(50):
        rsi = 12.0 + (i % 25)
        group = f"60000{i % 20}.SH|202401{i % 10 + 10}"
        for vid, th in (("21", 20.0), ("22", 25.0)):
            rows.append(
                _row(vid, th, 30.0, rsi, 10.0 + (i % 40), rsi < 22, group=group)
            )
    out = TradesStep.from_rows(
        rows,
        versions=["21", "22"],
        knob_paths=["core.rsi_oversold_threshold", "core.max_pe_percentile"],
    )
    assert out.get("status") in ("ok", "partial")
    assert (out.get("split") or {}).get("kind") == "grouped"
    assert (out.get("overview") or {}).get("auc_train") is not None
