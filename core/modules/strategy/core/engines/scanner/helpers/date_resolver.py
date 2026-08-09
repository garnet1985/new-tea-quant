"""扫描日锚点与当日有 K 线的股票宇宙。

本文件:
- ScanDateResolver: anchor_date、scan_date + stock_ids、K 线最新日
  边界: 负责 DataManager 日历/K 线查询；不负责 BE 扫描或 CSV 缓存写盘
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Tuple

logger = logging.getLogger(__name__)


class ScanDateResolver:
    """解析 scan_date + universe（当日有日 K 的股票）。"""

    def __init__(self, data_manager: Any) -> None:
        self.data_manager = data_manager

    @staticmethod
    def load_kline_latest_date(data_manager: Any) -> str:
        stock = getattr(data_manager, "stock", None)
        if stock is None:
            return ""
        loader = getattr(getattr(stock, "kline", None), "load_latest_date", None)
        if not callable(loader):
            return ""
        try:
            return str(loader("daily") or "").strip()
        except Exception as exc:
            logger.debug("load kline latest date failed: %s", exc)
            return ""

    @staticmethod
    def resolve_anchor_date(data_manager: Any, *, use_strict: bool) -> str:
        """严格：real-world 上一完整交易日；非严格：freshness 截至日（并 clamp 到 K 线最新）。"""
        meta = ScanDateResolver.resolve_anchor_meta(data_manager, use_strict=use_strict)
        return str(meta.get("scan_date") or "").strip()

    @staticmethod
    def resolve_anchor_meta(data_manager: Any, *, use_strict: bool) -> Dict[str, Any]:
        """解析扫描锚点，并返回来源说明（供报告 / CLI 标注）。"""
        cal_svc = getattr(getattr(data_manager, "service", None), "calendar", None)
        kline_latest = ScanDateResolver.load_kline_latest_date(data_manager)

        configured_as_of = ""
        try:
            from core.infra.project_context import ProjectContext

            configured_as_of = str(
                ProjectContext.config.get_as_of_latest_completed_trading_date() or ""
            ).strip()
        except Exception:
            configured_as_of = ""

        raw_anchor = ""
        source = ""
        source_detail = ""

        if cal_svc is None:
            return ScanDateResolver._finalize_meta(
                scan_date="",
                use_strict=use_strict,
                raw_anchor="",
                kline_latest=kline_latest,
                configured_as_of=configured_as_of,
                source="unavailable",
                source_detail="calendar service 不可用，无法解析扫描日",
            )

        try:
            if use_strict:
                raw_anchor = str(
                    cal_svc.get_real_world_latest_completed_trading_date() or ""
                ).strip()
                source = "real_world_latest_completed"
                source_detail = (
                    "严格模式：取真实世界上一完整交易日"
                    f"（get_real_world_latest_completed_trading_date → {raw_anchor or '空'}）"
                )
            else:
                from core.modules.data_source.core.catalog.freshness_probe import (
                    _resolve_freshness_end_date,
                )

                raw_anchor = str(_resolve_freshness_end_date(data_manager) or "").strip()
                if configured_as_of:
                    source = "data_json_as_of"
                    source_detail = (
                        "非严格模式：data.json 的 as_of_latest_completed_trading_date="
                        f"{configured_as_of}，经交易日历对齐为 {raw_anchor or '空'}"
                    )
                else:
                    source = "freshness_latest_completed"
                    source_detail = (
                        "非严格模式：未配置 data.json 截断，按 freshness/"
                        f"最新完整交易日解析 → {raw_anchor or '空'}"
                    )
        except Exception as exc:
            logger.debug("resolve_anchor_meta failed use_strict=%s: %s", use_strict, exc)
            return ScanDateResolver._finalize_meta(
                scan_date="",
                use_strict=use_strict,
                raw_anchor="",
                kline_latest=kline_latest,
                configured_as_of=configured_as_of,
                source="error",
                source_detail=f"解析扫描锚点失败: {exc}",
            )

        return ScanDateResolver._finalize_meta(
            scan_date=raw_anchor,
            use_strict=use_strict,
            raw_anchor=raw_anchor,
            kline_latest=kline_latest,
            configured_as_of=configured_as_of,
            source=source,
            source_detail=source_detail,
        )

    @staticmethod
    def _finalize_meta(
        *,
        scan_date: str,
        use_strict: bool,
        raw_anchor: str,
        kline_latest: str,
        configured_as_of: str,
        source: str,
        source_detail: str,
    ) -> Dict[str, Any]:
        day = str(scan_date or "").strip()
        clamped = False
        if day and kline_latest and day > kline_latest:
            logger.warning(
                "扫描锚点 %s 晚于库内 K 线最新日 %s，按 %s 执行扫描",
                day,
                kline_latest,
                kline_latest,
            )
            day = kline_latest
            clamped = True
            source_detail = (
                f"{source_detail}；锚点晚于库内 K 线最新日 {kline_latest}，已截断到该日"
            )
            source = f"{source}+kline_clamp"

        mode = "strict" if use_strict else "non_strict"
        return {
            "scan_date": day,
            "use_strict": bool(use_strict),
            "mode": mode,
            "mode_label": "严格模式" if use_strict else "非严格模式",
            "raw_anchor": str(raw_anchor or "").strip(),
            "kline_latest": str(kline_latest or "").strip(),
            "configured_as_of": str(configured_as_of or "").strip(),
            "clamped_to_kline": clamped,
            "source": source,
            "source_detail": source_detail,
        }

    def resolve_scan_date(self, *, use_strict: bool) -> Tuple[str, List[str]]:
        day, ids, _meta = self.resolve_scan_date_with_meta(use_strict=use_strict)
        return day, ids

    def resolve_scan_date_with_meta(
        self, *, use_strict: bool
    ) -> Tuple[str, List[str], Dict[str, Any]]:
        meta = self.resolve_anchor_meta(self.data_manager, use_strict=use_strict)
        scan_date = str(meta.get("scan_date") or "").strip()
        if not scan_date:
            raise ValueError(
                "failed to resolve scan date "
                f"({'strict/real-world' if use_strict else 'non-strict/freshness'})"
            )
        stock_ids = self.stocks_with_kline(scan_date)
        if not stock_ids:
            raise ValueError(f"no kline data on {scan_date}")
        return scan_date, stock_ids, meta

    def stocks_with_kline(self, date: str) -> List[str]:
        get_table = getattr(self.data_manager, "get_table", None)
        if not callable(get_table):
            return []
        kline_model = get_table("sys_stock_klines")
        if not kline_model:
            return []
        rows = kline_model.load_by_date(date)
        ids = {
            str(row.get("id") or "").strip()
            for row in (rows or [])
            if isinstance(row, dict) and str(row.get("id") or "").strip()
        }
        return sorted(ids)


__all__ = ["ScanDateResolver"]
