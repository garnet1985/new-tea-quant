"""策略结果缓存基类（simulate / 后续 scan 等共用骨架）。"""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any, ClassVar, Dict, Optional

from core.modules.data_manager import DataManager

logger = logging.getLogger(__name__)

_DB_CACHE_META_KEY = "_db_cache_meta"
_WRITE_COUNT_KEY = "write_count"


class BaseCacheManager(ABC):
    """按 strategy key + 指纹查写 DB 缓存的公共骨架。

    子类通过覆盖类属性 / 抽象方法差异化：
    - ``table_name`` / ``max_rows``：表与保留行数
    - ``get_cache`` / ``set_cache``：读写语义（槽位、payload 形状等）
    """

    table_name: ClassVar[str] = ""
    max_rows: ClassVar[int] = 50

    @classmethod
    @abstractmethod
    def get_cache(
        cls,
        key: str,
        fps: Any,
        kind: Any = None,
    ) -> Optional[Dict[str, Any]]:
        """命中返回缓存 payload；未命中返回 None。"""

    @classmethod
    @abstractmethod
    def set_cache(
        cls,
        key: str,
        fps: Any,
        value: Dict[str, Any],
    ) -> int:
        """写入缓存；返回版本号（失败 0）。"""

    # --- shared persistence helpers ---------------------------------------

    @classmethod
    def _table(cls):
        name = str(cls.table_name or "").strip()
        if not name:
            raise ValueError(f"{cls.__name__}.table_name 未配置")
        try:
            return DataManager().get_table(name)
        except Exception:
            logger.exception("获取表 %s 失败", name)
            return None

    @classmethod
    def _load_row_by_fingerprints(
        cls,
        strategy_name: str,
        settings_fp: str,
        env_fp: str,
        *,
        model: Any = None,
    ) -> Optional[Dict[str, Any]]:
        op = model if model is not None else cls._table()
        if op is None:
            return None
        rows = op.list_by_strategy_fingerprints(
            strategy_name=strategy_name,
            settings_finger_print_id=settings_fp,
            env_fingerprint_id=env_fp,
            limit=1,
        )
        if not rows:
            return None
        return dict(rows[0] or {})

    @classmethod
    def _reports_from_row(cls, row: Dict[str, Any]) -> Dict[str, Any]:
        blob = row.get("result_report")
        if not isinstance(blob, dict):
            blob = row.get("reports")
        return dict(blob) if isinstance(blob, dict) else {}

    @classmethod
    def _attach_initial_write_meta(cls, report: Dict[str, Any]) -> Dict[str, Any]:
        merged = dict(report or {})
        merged.pop(_DB_CACHE_META_KEY, None)
        merged[_DB_CACHE_META_KEY] = {_WRITE_COUNT_KEY: 1}
        return merged

    @classmethod
    def _bump_write_count(cls, report: Dict[str, Any]) -> Dict[str, Any]:
        merged = dict(report or {})
        meta = dict(merged.get(_DB_CACHE_META_KEY) or {})
        try:
            count = int(meta.get(_WRITE_COUNT_KEY, 0) or 0) + 1
        except (TypeError, ValueError):
            count = 1
        meta[_WRITE_COUNT_KEY] = count
        merged[_DB_CACHE_META_KEY] = meta
        return merged

    @classmethod
    def _prune_oldest(cls, model: Any, strategy_name: str) -> None:
        sn = str(strategy_name or "").strip()
        if not sn or model is None:
            return
        cap = int(cls.max_rows)
        try:
            rows = model.list_versions_asc(sn, limit=cap + 50)
        except Exception:
            logger.exception("list_versions_asc 失败 strategy=%s", sn)
            return
        while len(rows) > cap:
            oldest = rows[0] or {}
            version = int(oldest.get("version") or 0)
            if version <= 0:
                break
            try:
                model.delete_version_row(sn, version)
            except Exception:
                logger.exception(
                    "delete_version_row 失败 strategy=%s version=%s", sn, version
                )
                break
            rows = rows[1:]


__all__ = ["BaseCacheManager"]
