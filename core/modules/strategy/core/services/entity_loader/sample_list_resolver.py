"""回测前解析实入池：stock_list_filter → sampling → ``to_sample_list`` → 排序（指纹前）。

调用方: Strategy.simulate、DecisionMaker 找枚举 vid。
维度查询只经 DataManager.stock.list.filter_ids。
"""

from __future__ import annotations

import logging
from typing import Any, List, Optional, Sequence

from core.modules.data_manager import DataManager
from core.modules.strategy.core.engines.shared.services.strategy_settings.strategy_settings import (
    StrategySettings,
)
from core.modules.strategy.core.hooks.hook_params import open_context
from core.modules.strategy.core.hooks.runtime import StrategyHookRuntime
from core.modules.strategy.core.services.discovery.data.discovered_strategy import (
    EnabledStrategyInfo,
)
from core.modules.strategy.core.services.entity_loader.global_entity_loader import (
    GlobalEntityCache,
)
from core.modules.strategy.core.services.entity_loader.stock_sampling import StockSampler

logger = logging.getLogger(__name__)


class SampleListResolver:
    """DB 宇宙 → data.stock_list_filter → settings.sampling → hooks.to_sample_list → sorted unique。"""

    @classmethod
    def resolve(
        cls,
        strategy_info: EnabledStrategyInfo,
        settings: StrategySettings,
        *,
        universe: Optional[Sequence[str]] = None,
    ) -> List[str]:
        raw_universe = (
            list(universe)
            if universe is not None
            else GlobalEntityCache.get_stock_list()
        )
        stock_list = cls._normalize_ids(raw_universe)
        stock_list = cls._apply_stock_list_filter(settings, stock_list)

        if settings.sampling.use_sampling:
            stock_list = cls._normalize_ids(
                StockSampler.sample(
                    stock_list,
                    settings.sampling.sampling,
                    str(getattr(strategy_info, "key", "") or ""),
                )
            )

        stock_list = cls._apply_hook(strategy_info, settings, stock_list)
        return sorted(stock_list)

    @classmethod
    def _apply_stock_list_filter(
        cls,
        settings: StrategySettings,
        stock_list: List[str],
    ) -> List[str]:
        filt = settings.data.normalized_stock_list_filter()
        if filt is None:
            return stock_list
        try:
            filtered = DataManager().stock.list.filter_ids(
                include=filt.get("include"),
                exclude=filt.get("exclude"),
                universe=stock_list,
            )
        except Exception:
            logger.error(
                "stock_list_filter 失败，回退未过滤宇宙",
                exc_info=True,
            )
            return stock_list
        return cls._normalize_ids(filtered)

    @classmethod
    def _apply_hook(
        cls,
        strategy_info: EnabledStrategyInfo,
        settings: StrategySettings,
        stock_list: List[str],
    ) -> List[str]:
        runtime, err = StrategyHookRuntime.from_strategy_info(strategy_info, settings)
        if runtime is None:
            logger.error(
                "to_sample_list: hooks 加载失败，使用 filter/sampling 结果 strategy=%s err=%s",
                getattr(strategy_info, "key", ""),
                (err or {}).get("error"),
            )
            return stock_list

        strategy_key = str(
            getattr(strategy_info, "key", None)
            or getattr(strategy_info, "unique_relative_path", "")
            or ""
        ).strip()
        strategy_path = str(
            getattr(strategy_info, "unique_relative_path", "") or strategy_key
        ).strip()
        ctx = open_context(
            strategy_key=strategy_key,
            settings=settings,
            sample_list=stock_list,
            strategy_path=strategy_path,
        )
        allowed = set(stock_list)
        try:
            raw = runtime.call("to_sample_list", ctx, list(stock_list))
        except Exception:
            logger.error(
                "to_sample_list 失败 strategy=%s，回退 filter/sampling 结果",
                strategy_key,
                exc_info=True,
            )
            return stock_list

        out: List[str] = []
        seen = set()
        for item in raw or []:
            sid = str(item).strip()
            if not sid or sid not in allowed or sid in seen:
                continue
            seen.add(sid)
            out.append(sid)
        return out

    @staticmethod
    def _normalize_ids(ids: Optional[Sequence[Any]]) -> List[str]:
        out: List[str] = []
        seen = set()
        for item in ids or []:
            sid = str(item).strip()
            if not sid or sid in seen:
                continue
            seen.add(sid)
            out.append(sid)
        return out


__all__ = ["SampleListResolver"]
