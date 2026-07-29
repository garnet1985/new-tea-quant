"""non_time_series Tag：装载非时序（及可选时序辅助）contracts。

消费者: TagNonTimeSeriesPipeline
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


class TagNonTimeSeriesDataLoader:
    """主进程 issue contracts（不走 shm / JobBundleLoader）。"""

    @classmethod
    def load(
        cls,
        settings: TagSettings,
        *,
        start_date: str = "",
        end_date: str = "",
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
                    "TagNonTimeSeriesDataLoader: 跳过 per_entity 声明 %s"
                    "（non_ts runner 不装实体序列）",
                    data_key,
                )
                continue
            params = dict(item.get("params") or {})
            runtime: Dict[str, Any] = dict(params)
            if DataSettings.is_time_series(data_key):
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
                    "TagNonTimeSeriesDataLoader: issue 失败 data_key=%s error=%s",
                    data_key,
                    exc,
                    exc_info=True,
                )
                continue
            if not getattr(contract, "is_loaded", False):
                logger.warning(
                    "TagNonTimeSeriesDataLoader: contract 未加载 data_key=%s",
                    data_key,
                )
                continue
            out[data_key] = contract
        return out

    @classmethod
    def to_items(
        cls,
        contracts: Dict[str, Any],
        *,
        as_of: str = "",
    ) -> Dict[str, List[Dict[str, Any]]]:
        """非时序 → ``get_data()``；时序辅助源 → ``until(as_of)``。"""
        items: Dict[str, List[Dict[str, Any]]] = {}
        point = str(as_of or "").strip()
        for data_key, contract in contracts.items():
            if DataSettings.is_time_series(data_key):
                items[data_key] = cls._slice_time_series(contract, data_key, point)
                continue
            items[data_key] = cls._rows_from_non_ts(contract, data_key)
        return items

    @classmethod
    def _rows_from_non_ts(cls, contract: Any, data_key: str) -> List[Dict[str, Any]]:
        try:
            raw = contract.get_data()
        except Exception as exc:
            logger.error(
                "get_data 失败 data_key=%s error=%s",
                data_key,
                exc,
                exc_info=True,
            )
            return []
        if raw is None:
            return []
        if isinstance(raw, list):
            return [row for row in raw if isinstance(row, dict)]
        if isinstance(raw, dict):
            # 个别 loader 可能包一层
            if all(isinstance(v, dict) for v in raw.values()):
                return list(raw.values())
            return [raw]
        return []

    @classmethod
    def _slice_time_series(
        cls,
        contract: Any,
        data_key: str,
        as_of: str,
    ) -> List[Dict[str, Any]]:
        if not as_of:
            return []
        try:
            pit = contract.until(as_of)
        except Exception as exc:
            logger.error(
                "until 失败 data_key=%s as_of=%s error=%s",
                data_key,
                as_of,
                exc,
                exc_info=True,
            )
            return []
        if not isinstance(pit, dict):
            return []
        rows = pit.get("_global")
        if rows is None and len(pit) == 1:
            rows = next(iter(pit.values()))
        if not isinstance(rows, list):
            return list(rows) if rows else []
        return rows


__all__ = ["TagNonTimeSeriesDataLoader"]
