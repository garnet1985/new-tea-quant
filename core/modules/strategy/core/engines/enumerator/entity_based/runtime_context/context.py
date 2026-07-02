"""entity_based 模式 runtime context（外壳）。"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

from core.modules.strategy.core.data.settings.strategy_settings import StrategySettings
from core.modules.strategy.core.services.discovery.data.discovered_strategy import EnabledStrategyInfo

from .data import EntityBasedDataContext
from .info import EntityBasedGeneralInfo
from .performance_config import PerformanceConfig
from .status import EntityBasedRuntimeStatus


@dataclass
class EntityBasedRuntimeContext:
    """entity_based 回测 runtime context（外壳）。"""

    # 基础信息
    strategy_info: EnabledStrategyInfo

    # 子context
    performance: PerformanceConfig      # 性能配置（传递给BacktestEngine）
    settings: StrategySettings
    data: EntityBasedDataContext
    status: EntityBasedRuntimeStatus
    info: EntityBasedGeneralInfo

    @classmethod
    def init(cls, strategy_info: EnabledStrategyInfo, global_data_cache: Dict[str, Any] = None) -> EntityBasedRuntimeContext:
        """初始化runtime context（调用子context.init）。"""

        # 1. 构建validated settings对象（传递给子context使用）
        settings_obj = StrategySettings.from_dict(strategy_info.settings)

        # 2. 调用子context.init（传递settings_obj）
        performance = PerformanceConfig.init()
        info = EntityBasedGeneralInfo.init(strategy_info, settings_obj)
        data = EntityBasedDataContext.init(strategy_info, settings_obj, global_data_cache)
        status = EntityBasedRuntimeStatus.init()

        return cls(
            strategy_info=strategy_info,
            performance=performance,
            settings=settings_obj,
            data=data,
            status=status,
            info=info,
        )


__all__ = ["EntityBasedRuntimeContext"]