"""Scanner Job 构建（entity_based；BE 按 scanner profile 切 batch）。"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List

from core.modules.strategy.core.engines.shared.services.entity_loader.strategy_data_resolver import (
    StrategyDataResolver,
)
from core.modules.strategy.core.engines.shared.services.strategy_settings.strategy_settings import (
    StrategySettings,
)
from core.modules.strategy.core.services.discovery.data.discovered_strategy import (
    EnabledStrategyInfo,
)

logger = logging.getLogger(__name__)

SCANNER_GLOBAL_KEY = "scanner"
_MAX_LOOKBACK_DAYS = 60


class JobBuilder:
    """组装扫描 entity_based jobs。"""

    @classmethod
    def build_jobs(
        cls,
        *,
        strategy_info: EnabledStrategyInfo,
        settings: StrategySettings,
        stock_ids: List[str],
        scan_date: str,
    ) -> List[Dict[str, Any]]:
        ids = [str(sid).strip() for sid in stock_ids if str(sid).strip()]
        if not ids:
            return []

        day = str(scan_date or "").strip()
        if not day:
            raise ValueError("scan_date 不能为空")

        settings_dict = settings.to_dict()
        resolver = StrategyDataResolver(settings_dict)
        groups = StrategyDataResolver.group_from_settings(settings_dict)
        lookback = min(int(resolver.min_required_records or 1), _MAX_LOOKBACK_DAYS)
        start_date = cls._lookback_start(day, lookback)

        entity_shared: Dict[str, Dict[str, Any]] = {}
        for declaration in groups["per_entity_declarations"]:
            data_key = declaration["data_key"]
            entity_shared[data_key] = {
                "params": declaration.get("params", {}),
                "start": start_date,
                "end": day,
                "indicators": declaration.get("indicators", {}),
            }

        market_profile = str(settings_dict.get("market_profile") or "").strip()
        payload: Dict[str, Any] = {
            "entity_specified": [{"id": eid} for eid in ids],
            "entity_shared": entity_shared,
            "global": {
                SCANNER_GLOBAL_KEY: {
                    "scan_date": day,
                    "lookback": lookback,
                    "market_profile": market_profile,
                }
            },
            "shm_info": {},
            "entities_count": len(ids),
            "strategy_info": {
                "key": strategy_info.key,
                "unique_relative_path": strategy_info.unique_relative_path,
                "hooks_module_path": strategy_info.hooks_module_path,
                "hooks_class_name": (
                    strategy_info.hooks_class.__name__
                    if strategy_info.hooks_class is not None
                    else ""
                ),
                "hooks_file_path": str(strategy_info.strategy_file.resolve()),
            },
            "settings": settings_dict,
        }

        logger.info(
            "scanner JobBuilder: entities=%d scan_date=%s lookback=%d~%s",
            len(ids),
            day,
            lookback,
            start_date,
        )
        return [{"id": f"scanner_{strategy_info.key or 'run'}", "payload": payload}]

    @staticmethod
    def scanner_meta(payload: Dict[str, Any]) -> Dict[str, Any]:
        global_block = payload.get("global") if isinstance(payload, dict) else None
        if not isinstance(global_block, dict):
            return {}
        meta = global_block.get(SCANNER_GLOBAL_KEY)
        return dict(meta) if isinstance(meta, dict) else {}

    @staticmethod
    def _lookback_start(scan_date: str, lookback: int) -> str:
        """日历窗：约 2× lookback 自然日，覆盖足够交易日。"""
        try:
            end = datetime.strptime(str(scan_date), "%Y%m%d")
        except ValueError:
            return scan_date
        days = max(int(lookback) * 2, int(lookback) + 30)
        return (end - timedelta(days=days)).strftime("%Y%m%d")


__all__ = ["JobBuilder", "SCANNER_GLOBAL_KEY"]
