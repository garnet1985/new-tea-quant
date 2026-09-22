"""回测前解析实入池：sampling → ``to_sample_list`` → 排序（指纹前）。

调用方: Strategy.simulate、DecisionMaker 找枚举 vid。
"""

from __future__ import annotations

import logging
from typing import Any, List, Optional, Sequence

from core.modules.strategy.core.engines.shared.services.strategy_settings.strategy_settings import (
    StrategySettings,
)
from core.modules.strategy.core.hooks.hook_params import StrategyContext
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
    """DB 宇宙 → settings.sampling → hooks.to_sample_list → sorted unique。"""

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
    def _apply_hook(
        cls,
        strategy_info: EnabledStrategyInfo,
        settings: StrategySettings,
        stock_list: List[str],
    ) -> List[str]:
        runtime, err = StrategyHookRuntime.from_strategy_info(strategy_info, settings)
        if runtime is None:
            logger.error(
                "to_sample_list: hooks 加载失败，使用 sampling 结果 strategy=%s err=%s",
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
        ctx = StrategyContext.assemble(
            strategy_key=strategy_key,
            settings=settings,
            stock_list=stock_list,
            strategy_path=strategy_path,
        )
        allowed = set(stock_list)
        try:
            raw = runtime.call("to_sample_list", ctx, stock_list=list(stock_list))
        except Exception:
            logger.error(
                "to_sample_list 失败 strategy=%s，回退 sampling 结果",
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
