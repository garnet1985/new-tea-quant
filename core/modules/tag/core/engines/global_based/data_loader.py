"""global Tag：装载 GLOBAL 时序 contracts。

消费者: TagGlobalPipeline
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

from core.modules.data_contract import ContractIssuer
from core.modules.tag.core.engines.per_entity.shared.tag_settings.data_settings import (
    DataSettings,
)
from core.modules.tag.core.engines.per_entity.shared.tag_settings.tag_settings import (
    TagSettings,
)

logger = logging.getLogger(__name__)


class TagGlobalDataLoader:
    """主进程 issue global contracts（不走 shm / JobBundleLoader）。"""

    @classmethod
    def load(
        cls,
        settings: TagSettings,
        *,
        start_date: str,
        end_date: str,
    ) -> Dict[str, Any]:
        """返回 ``{data_key: loaded Contract}``；跳过 per_entity required。"""
        settings.apply_defaults()
        start = str(start_date or "").strip()
        end = str(end_date or "").strip()
        out: Dict[str, Any] = {}
        for item in settings.data.issue_declarations():
            data_key = str(item.get("data_key") or "").strip()
            if not data_key:
                continue
            if DataSettings.is_per_entity(data_key):
                logger.warning(
                    "TagGlobalDataLoader: 跳过 per_entity 声明 %s（global runner 不装实体序列）",
                    data_key,
                )
                continue
            params = dict(item.get("params") or {})
            runtime: Dict[str, Any] = dict(params)
            if start:
                runtime["start_time"] = start
            if end:
                runtime["end_time"] = end
            try:
                contract = ContractIssuer.issue(
                    data_key,
                    runtime=runtime,
                    fill_in_data=True,
                )
            except Exception as exc:
                logger.error(
                    "TagGlobalDataLoader: issue 失败 data_key=%s error=%s",
                    data_key,
                    exc,
                    exc_info=True,
                )
                continue
            if not getattr(contract, "is_loaded", False):
                logger.warning(
                    "TagGlobalDataLoader: contract 未加载 data_key=%s", data_key
                )
                continue
            out[data_key] = contract
        return out

    @classmethod
    def slice_items(
        cls,
        contracts: Dict[str, Any],
        as_of: str,
    ) -> Dict[str, List[Dict[str, Any]]]:
        """对每个 contract ``until(as_of)`` → ``{data_key: rows}``。"""
        items: Dict[str, List[Dict[str, Any]]] = {}
        point = str(as_of or "").strip()
        for data_key, contract in contracts.items():
            if not point:
                items[data_key] = []
                continue
            try:
                pit = contract.until(point)
            except Exception as exc:
                logger.error(
                    "until 失败 data_key=%s as_of=%s error=%s",
                    data_key,
                    point,
                    exc,
                    exc_info=True,
                )
                items[data_key] = []
                continue
            if not isinstance(pit, dict):
                items[data_key] = []
                continue
            rows = pit.get("_global")
            if rows is None and len(pit) == 1:
                rows = next(iter(pit.values()))
            if not isinstance(rows, list):
                rows = list(rows) if rows else []
            items[data_key] = rows
        return items


__all__ = ["TagGlobalDataLoader"]
