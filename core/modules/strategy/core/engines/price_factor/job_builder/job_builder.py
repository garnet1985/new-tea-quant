"""价格回测 Job 构建（entity_based bundle；枚举结果由 worker 读）。

本文件:
- PriceFactorJobBuilder: entity_specified + enum 目录路径；不含枚举结果内容
  边界: 负责 job payload；不负责执行、读枚举 JSON、BE batch 切分
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from core.modules.strategy.core.services.artifacts import EnumerateStore

if TYPE_CHECKING:
    from core.modules.strategy.core.engines.price_factor.report_manager import ReportManager
    from core.modules.strategy.core.services.discovery.data.discovered_strategy import (
        EnabledStrategyInfo,
    )

logger = logging.getLogger(__name__)

# BE entity_based 切 batch 时只保留固定字段；自定义元数据必须放进 global / entity_shared / settings。
PRICE_FACTOR_GLOBAL_KEY = "price"


class PriceFactorJobBuilder:
    """组装价格回测 bundle job。

    边界:
    - 负责: 单 bundle（entity_specified + enum 目录路径）；枚举结果不进 payload
    - 不负责: 执行、读枚举 JSON / CSV、切 batch（BE Planner）、建 timeline 轴
    - 调用方: PriceFactorPipeline
    """

    @classmethod
    def build_jobs(
        cls,
        data: EnumerateStore,
        *,
        report: Optional["ReportManager"] = None,
        strategy_info: Optional["EnabledStrategyInfo"] = None,
    ) -> List[Dict[str, Any]]:
        """返回 ``[{"id", "payload"}, ...]``（通常 1 个 bundle）。"""
        entity_ids = [
            str(entity_id).strip()
            for entity_id in data.entity_ids
            if str(entity_id).strip()
        ]
        if not entity_ids:
            logger.warning("price_factor PriceFactorJobBuilder: entity_ids 为空，返回空 jobs")
            return []

        start = data.start_date
        end = data.end_date
        if not start or not end:
            raise ValueError(
                f"枚举 version 缺少 period.start_date/end_date: {data.output_dir}"
            )

        runtime = data.runtime
        strategy_key = str(runtime.strategy_key or "").strip()
        strategy_path = str(runtime.strategy_path or strategy_key).strip()
        settings = dict(runtime.settings_snapshot.effective_settings or {})
        if not settings.get("market_profile") and runtime.market_profile:
            settings["market_profile"] = str(runtime.market_profile).strip()

        price_meta: Dict[str, Any] = {
            "enum_output_dir": str(data.output_dir),
            "enum_version_id": str(data.version_id),
            "start_date": start,
            "end_date": end,
        }
        if report is not None:
            price_meta["price_output_dir"] = str(report.output_dir)
            price_meta["price_version_id"] = str(report.version_id or "").strip()

        payload: Dict[str, Any] = {
            "entity_specified": [{"id": entity_id} for entity_id in entity_ids],
            "entity_shared": {},
            "global": {PRICE_FACTOR_GLOBAL_KEY: price_meta},
            "shm_info": {},
            "strategy_info": cls._strategy_info_payload(
                strategy_key, strategy_path, strategy_info
            ),
            "settings": settings,
            "entities_count": len(entity_ids),
        }

        logger.info(
            "price_factor PriceFactorJobBuilder: entities=%d, period=%s~%s, enum_dir=%s",
            len(entity_ids),
            start,
            end,
            data.output_dir,
        )
        return [{"id": "price_run", "payload": payload}]

    @staticmethod
    def _strategy_info_payload(
        strategy_key: str,
        strategy_path: str,
        strategy_info: Optional["EnabledStrategyInfo"],
    ) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "key": strategy_key,
            "unique_relative_path": strategy_path,
        }
        if strategy_info is None:
            return payload
        payload["hooks_module_path"] = str(
            getattr(strategy_info, "hooks_module_path", "") or ""
        )
        hooks_cls = getattr(strategy_info, "hooks_class", None)
        payload["hooks_class_name"] = (
            str(getattr(hooks_cls, "__name__", "") or "") if hooks_cls is not None else ""
        )
        strategy_file = getattr(strategy_info, "strategy_file", None)
        file_path = ""
        if strategy_file is not None:
            try:
                file_path = str(strategy_file.resolve())
            except Exception:
                file_path = str(strategy_file)
        payload["hooks_file_path"] = file_path
        return payload

    @classmethod
    def price_factor_meta(cls, payload: Dict[str, Any]) -> Dict[str, Any]:
        """从 job payload 取出 ``global.price``（worker / hooks 用）。"""
        global_block = payload.get("global") if isinstance(payload, dict) else None
        if not isinstance(global_block, dict):
            raise ValueError("price payload 缺少 global")
        meta = global_block.get(PRICE_FACTOR_GLOBAL_KEY)
        if not isinstance(meta, dict) or not meta:
            raise ValueError(f"price payload 缺少 global.{PRICE_FACTOR_GLOBAL_KEY}")
        return dict(meta)


__all__ = ["PriceFactorJobBuilder", "PRICE_FACTOR_GLOBAL_KEY"]
