"""股票元数据加载工具。

本文件:
- StockMetaHelper: 单股 / 批量 meta 加载
  边界: 负责 DataManager.stock.list 封装；不负责 sampling 或 contract 注入

slice_based 在 reader ProcessPool 阶段会释放主进程 DuckDB。
此时禁止再 ``DataManager()``（会 wait/抢锁，Windows 上表现为卡死或 Conflicting lock）。
批量 meta 须在进池前写入 payload.stock_info。
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Iterable, Mapping, Optional

logger = logging.getLogger(__name__)


class StockMetaHelper:
    """加载单股 / 批量 meta（entity / slice 共用）。"""

    @staticmethod
    def fallback(stock_id: str) -> Dict[str, Any]:
        sid = str(stock_id or "").strip()
        return {
            "id": sid,
            "name": sid,
            "industry": "",
            "type": "",
            "exchange_center": "",
            "delist_date": "",
        }

    @staticmethod
    def load(stock_id: str) -> Dict[str, Any]:
        sid = str(stock_id or "").strip()
        fallback = StockMetaHelper.fallback(sid)
        if not sid:
            return fallback
        if StockMetaHelper._duckdb_pool_suspended():
            return fallback
        try:
            from core.modules.data_manager import DataManager

            row = DataManager().stock.list.load_meta(sid)
            if isinstance(row, dict) and row.get("id"):
                return {**fallback, **row}
        except Exception as exc:
            if sid.upper() != "DUMMY":
                logger.warning("加载股票元数据失败: stock_id=%s error=%s", sid, exc)
        return fallback

    @staticmethod
    def load_map(stock_ids: Iterable[str]) -> Dict[str, Dict[str, Any]]:
        """一次 ``load_all`` 填充 meta；进程池 suspend 期间只返回 fallback。"""
        ids = [str(s).strip() for s in stock_ids if str(s).strip()]
        out = {sid: StockMetaHelper.fallback(sid) for sid in ids}
        if not ids:
            return out
        if StockMetaHelper._duckdb_pool_suspended():
            logger.warning(
                "DuckDB ProcessPool 已释放主库，跳过 stock meta 批量加载（%d ids）",
                len(ids),
            )
            return out
        try:
            from core.modules.data_manager import DataManager

            dm = DataManager()
            rows = dm.stock.list.load_all() or []
            normalize = getattr(dm.stock.list, "_normalize_delist_date", None)
        except Exception as exc:
            logger.warning("批量加载股票元数据失败: error=%s", exc)
            return out

        by_id: Dict[str, Dict[str, Any]] = {}
        for row in rows:
            if not isinstance(row, dict):
                continue
            rid = str(row.get("id") or "").strip()
            if rid:
                by_id[rid] = row
        for sid in ids:
            row = by_id.get(sid)
            if not row:
                continue
            delist_raw = row.get("delist_date") or row.get("delisted_date")
            if callable(normalize):
                delist = normalize(delist_raw) or ""
            else:
                delist = str(delist_raw or "").strip()
                if delist in ("0", "0.0"):
                    delist = ""
            out[sid] = {
                "id": sid,
                "name": row.get("name") or sid,
                "industry": row.get("industry") or "",
                "type": row.get("type") or "",
                "exchange_center": row.get("exchange_center") or "",
                "delist_date": delist,
                "list_status": row.get("list_status") or "",
                "list_date": row.get("list_date") or "",
            }
        return out

    @staticmethod
    def from_payload(
        payload: Optional[Mapping[str, Any]],
        stock_ids: Iterable[str],
    ) -> Dict[str, Dict[str, Any]]:
        """优先用 payload.stock_info；缺省再 load_map（须主库仍可用）。"""
        ids = [str(s).strip() for s in stock_ids if str(s).strip()]
        cached = payload.get("stock_info") if isinstance(payload, Mapping) else None
        if isinstance(cached, dict) and cached:
            out: Dict[str, Dict[str, Any]] = {}
            for sid in ids:
                raw = cached.get(sid)
                if isinstance(raw, dict) and (
                    raw.get("id") or raw.get("name") is not None
                ):
                    out[sid] = {**StockMetaHelper.fallback(sid), **raw}
                    out[sid]["id"] = sid
                else:
                    out[sid] = StockMetaHelper.fallback(sid)
            return out
        return StockMetaHelper.load_map(ids)

    @staticmethod
    def _duckdb_pool_suspended() -> bool:
        try:
            from core.infra.db import Db

            return bool(Db.duckdb.worker_pool.is_main_active())
        except Exception:
            return False


__all__ = ["StockMetaHelper"]
