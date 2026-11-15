"""Scan → post_process 推送用：从 price 模拟产物组装历史统计（供 context 注入，不回读磁盘）。"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from core.modules.strategy.core.services.artifacts import PriceFactorStore
from core.modules.strategy.core.services.discovery import DiscoveryService

logger = logging.getLogger(__name__)


def build_price_history_for_adapter(
    strategy_name: str,
    stock_ids: Sequence[str],
) -> Dict[str, Any]:
    """
    供扫描 present / presenter adapter 组装 ``backtest_history``。

    Returns::
        {
            "session_summary": dict | None,
            "by_stock": {stock_id: stats_dict, ...},
        }
    """
    version_dir = _latest_price_version_dir(strategy_name)
    session_summary = (
        _load_session_summary(version_dir) if version_dir is not None else None
    )
    by_stock: Dict[str, Any] = {}
    if version_dir is not None:
        for sid in dict.fromkeys(str(s).strip() for s in stock_ids if str(s).strip()):
            stats = _load_stock_history(version_dir, sid)
            if stats:
                by_stock[sid] = stats
    return {"session_summary": session_summary, "by_stock": by_stock}


def _load_stock_history(version_dir: Path, stock_id: str) -> Optional[Dict[str, Any]]:
    try:
        rows = PriceFactorStore.at(version_dir).investments(stock_id)
        if not rows:
            return None
        investments = [
            {
                "roi": row.roi,
                "result": row.result,
                "duration_in_days": row.holding_days,
            }
            for row in rows
        ]
        return _calculate_statistics(investments)
    except Exception as e:
        logger.debug(
            "[price_history] 加载股票历史失败: stock_id=%s error=%s",
            stock_id,
            e,
        )
        return None


def _load_session_summary(version_dir: Path) -> Optional[Dict[str, Any]]:
    try:
        store = PriceFactorStore.at(version_dir)
        path = store.file("overall_report")
        if not path.is_file():
            return None
        raw = store.read_json("overall_report")
        if not isinstance(raw, dict):
            return None
        # overall_report.json 契约：指标在嵌套 ``summary``；兼容旧扁平结构
        nested = raw.get("summary")
        if isinstance(nested, dict) and nested:
            return dict(nested)
        return raw
    except Exception as e:
        logger.debug("[price_history] 加载会话汇总失败: %s", e)
        return None


def refresh_presenter_backtest_history(
    props: Dict[str, Any],
    *,
    fallback_strategy_name: str = "",
) -> Dict[str, Any]:
    """按当前磁盘 price 产物重填 ``props.backtest_history``（扫描早于回测写完时用）。"""
    if not isinstance(props, dict):
        return {}
    out = dict(props)
    strategies = list(out.get("strategies") or [])
    history: Dict[str, Any] = {}
    for row in strategies:
        if not isinstance(row, dict):
            continue
        name = str(row.get("strategy_name") or fallback_strategy_name or "").strip()
        if not name:
            continue
        entity_ids = [
            str(o.get("entity_id") or "").strip()
            for o in (row.get("opportunities") or [])
            if isinstance(o, dict) and str(o.get("entity_id") or "").strip()
        ]
        history[name] = build_price_history_for_adapter(name, entity_ids)
        # 与 presenter adapter 返回形状对齐
        hist = history[name]
        history[name] = {
            "layer": "price",
            "session_summary": hist.get("session_summary"),
            "by_stock": dict(hist.get("by_stock") or {}),
            "error": None,
        }
    out["backtest_history"] = history
    return out


def enrich_post_process_ui_history(
    post_process: Optional[Dict[str, Any]],
    *,
    fallback_strategy_name: str = "",
) -> Dict[str, Any]:
    """若 ``ui.scan_report`` 为 presenter 且历史为空，则按最新 price 产物回填。"""
    pp = dict(post_process or {})
    ui = dict(pp.get("ui") or {})
    slot = ui.get("scan_report")
    if not isinstance(slot, dict) or str(slot.get("view") or "") != "presenter":
        return pp
    props = slot.get("props") if isinstance(slot.get("props"), dict) else {}
    hist = props.get("backtest_history") if isinstance(props.get("backtest_history"), dict) else {}
    needs_refresh = False
    if not hist:
        needs_refresh = True
    else:
        for entry in hist.values():
            if not isinstance(entry, dict):
                needs_refresh = True
                break
            if entry.get("error"):
                needs_refresh = True
                break
            summary = entry.get("session_summary")
            by_stock = entry.get("by_stock") if isinstance(entry.get("by_stock"), dict) else {}
            if not summary and not by_stock:
                needs_refresh = True
                break
    if not needs_refresh:
        return pp
    refreshed = refresh_presenter_backtest_history(
        props, fallback_strategy_name=fallback_strategy_name
    )
    ui["scan_report"] = {**slot, "props": refreshed}
    pp["ui"] = ui
    return pp


def _latest_price_version_dir(strategy_name: str) -> Optional[Path]:
    name = str(strategy_name or "").strip()
    if not name:
        return None
    try:
        folder = DiscoveryService.resolve_strategy_folder(name)
    except Exception:
        folder = name
    store = PriceFactorStore.latest(folder)
    return store.output_dir if store is not None else None


def _calculate_statistics(investments: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not investments:
        return {}

    completed = [
        inv for inv in investments if inv.get("result") in ["win", "loss"]
    ]

    if not completed:
        return {
            "total_investments": len(investments),
            "completed_investments": 0,
            "win_rate": 0.0,
            "avg_return": 0.0,
            "win_count": 0,
            "loss_count": 0,
            "max_return": 0.0,
            "min_return": 0.0,
            "avg_holding_days": 0.0,
        }

    returns = []
    holding_days = []
    win_count = 0
    loss_count = 0

    for inv in completed:
        roi = inv.get("roi", 0.0)
        if not isinstance(roi, (int, float)):
            try:
                roi = float(roi)
            except (ValueError, TypeError):
                roi = 0.0

        returns.append(roi)

        result = inv.get("result", "")
        if result == "win":
            win_count += 1
        elif result == "loss":
            loss_count += 1
        elif roi > 0:
            win_count += 1
        elif roi < 0:
            loss_count += 1

        duration = inv.get("duration_in_days", 0)
        if not isinstance(duration, (int, float)):
            try:
                duration = float(duration)
            except (ValueError, TypeError):
                duration = 0.0

        if duration > 0:
            holding_days.append(duration)

    total = len(completed)
    win_rate = win_count / total if total > 0 else 0.0
    avg_return = sum(returns) / len(returns) if returns else 0.0
    max_return = max(returns) if returns else 0.0
    min_return = min(returns) if returns else 0.0
    avg_holding_days = (
        sum(holding_days) / len(holding_days) if holding_days else 0.0
    )

    return {
        "total_investments": len(investments),
        "completed_investments": total,
        "win_rate": win_rate,
        "avg_return": avg_return,
        "win_count": win_count,
        "loss_count": loss_count,
        "max_return": max_return,
        "min_return": min_return,
        "avg_holding_days": avg_holding_days,
    }


__all__ = ["build_price_history_for_adapter"]
