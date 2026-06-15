#!/usr/bin/env python3
"""价格回测逐股 ref（``0_stock_ref.json`` / 单股 JSON 摘要）。"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.modules.strategy.engines.shared.report_base import ReportBase
from core.modules.strategy.services.data.output.enumerator_output_service import STOCK_REF_FILENAME

logger = logging.getLogger(__name__)


def _investment_expired(inv: Dict[str, Any]) -> bool:
    for tgt in inv.get("completed_targets") or []:
        if not isinstance(tgt, dict):
            continue
        target_type = str(tgt.get("target_type") or "").lower()
        name = str(tgt.get("name") or "").lower()
        if target_type == "expired" or "expiration" in name:
            return True
    return False


def _roi_as_percent(avg_roi: float) -> float:
    if abs(avg_roi) < 1.0:
        return round(avg_roi * 100.0, 2)
    return round(avg_roi, 2)


def build_price_stock_ref_entry(stock_summary: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """由 worker 落盘的 ``{stock_id}.json`` 或内存 ``stock_summary`` 生成逐股 ref 条目。"""
    if not isinstance(stock_summary, dict):
        return None
    stock = stock_summary.get("stock") if isinstance(stock_summary.get("stock"), dict) else {}
    stock_id = str(stock.get("id") or "").strip()
    if not stock_id:
        return None

    summary = stock_summary.get("summary") if isinstance(stock_summary.get("summary"), dict) else {}
    investments = [
        x for x in (stock_summary.get("investments") or []) if isinstance(x, dict)
    ]
    total = int(summary.get("total_investments") or 0)
    if total <= 0 and investments:
        total = len(investments)
    if total <= 0:
        return None

    total_win = int(summary.get("total_complete_win") or 0)
    if total_win <= 0 and investments:
        from core.modules.strategy.engines.shared.data_classes.investment_state import (
            InvestmentLifecycle,
            InvestmentOutcome,
        )

        total_win = sum(
            1
            for x in investments
            if str(x.get("lifecycle") or "").lower() == InvestmentLifecycle.COMPLETE.value
            and str(x.get("outcome") or "").lower() == InvestmentOutcome.WIN.value
        )

    avg_roi_raw = float(summary.get("avg_roi") or 0.0)
    if avg_roi_raw == 0.0 and investments:
        avg_roi_raw = ReportBase.safe_div(
            sum(float(x.get("roi") or 0.0) for x in investments),
            len(investments),
        )

    avg_duration = float(summary.get("avg_duration_in_days") or 0.0)
    if avg_duration <= 0.0 and investments:
        avg_duration = ReportBase.safe_div(
            sum(float(x.get("holding_days") or 0.0) for x in investments),
            len(investments),
        )

    expired_count = sum(1 for x in investments if _investment_expired(x))
    stock_name = ""
    for inv in investments:
        nm = str(inv.get("stock_name") or "").strip()
        if nm:
            stock_name = nm
            break

    return {
        "stock_name": stock_name or stock_id,
        "win_rate": round(ReportBase.safe_div(total_win, total) * 100.0, 1),
        "avg_roi": _roi_as_percent(avg_roi_raw),
        "avg_duration_in_days": round(avg_duration, 1),
        "expiration_ratio": round(ReportBase.safe_div(expired_count, total) * 100.0, 1),
        "total_investments": total,
    }


def build_price_stock_ref_map(stock_summaries: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    out: Dict[str, Dict[str, Any]] = {}
    for stock_summary in stock_summaries:
        if not isinstance(stock_summary, dict):
            continue
        stock = stock_summary.get("stock") if isinstance(stock_summary.get("stock"), dict) else {}
        sid = str(stock.get("id") or "").strip()
        if not sid:
            continue
        entry = build_price_stock_ref_entry(stock_summary)
        if entry:
            out[sid] = entry
    return out


def load_price_stock_ref_from_dir(output_dir: Path) -> Dict[str, Dict[str, Any]]:
    """优先读 ``0_stock_ref.json``；否则扫描单股 ``{id}.json`` 聚合。"""
    base = Path(output_dir)
    ref_path = base / STOCK_REF_FILENAME
    if ref_path.is_file():
        try:
            raw = json.loads(ref_path.read_text(encoding="utf-8"))
            if isinstance(raw, dict) and raw:
                return {str(k): dict(v) for k, v in raw.items() if isinstance(v, dict)}
        except Exception:
            logger.exception("读取价格回测 stock_ref 失败: %s", ref_path)

    out: Dict[str, Dict[str, Any]] = {}
    for path in sorted(base.glob("*.json")):
        if path.name.startswith("0_"):
            continue
        sid = path.stem.strip()
        if not sid:
            continue
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if not isinstance(raw, dict):
            continue
        entry = build_price_stock_ref_entry(raw)
        if entry:
            out[sid] = entry
    return out


def write_price_stock_ref(output_dir: Path, stock_summaries: List[Dict[str, Any]]) -> None:
    ref_map = build_price_stock_ref_map(stock_summaries)
    if not ref_map:
        return
    output_dir.mkdir(parents=True, exist_ok=True)
    ordered = {sid: ref_map[sid] for sid in sorted(ref_map.keys())}
    path = output_dir / STOCK_REF_FILENAME
    path.write_text(
        json.dumps(ordered, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


__all__ = [
    "build_price_stock_ref_entry",
    "build_price_stock_ref_map",
    "load_price_stock_ref_from_dir",
    "write_price_stock_ref",
]
