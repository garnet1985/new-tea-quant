"""Data manager 跨模块公开类型与少量跨域辅助符号。"""

from __future__ import annotations

from typing import Any, Optional

from core.modules.data_manager.core.data_services.stock.sub_services.tag_service import (
    TagDataService,
    TagDbUnavailable,
)
from core.modules.data_manager.core.enums import BaseTableNames


def normalize_delist_date(raw: Any) -> Optional[str]:
    """将源数据占位退市日（0 / 0.0）视为未退市；``DataManager.normalize_delist_date`` 入口。"""
    s = str(raw or "").strip()
    if not s or s.lower() in ("none", "nan", "0", "0.0"):
        return None
    return s


__all__ = [
    "BaseTableNames",
    "TagDataService",
    "TagDbUnavailable",
    "normalize_delist_date",
]
