"""Strategy 跨模块公开契约（hooks + 共享数据类型 / 运行时协作面 re-export）。

本文件:
- StrategyHooks / StrategyContext: 用户策略 hook 契约
- Opportunity / Investment / CalendarAsOfResult: 引擎共享数据类
- AsOfSlice / JobBundleLoader / ProgressRecorder: tag / BE 协作面（勿 deep-import）
  边界: 仅类型与协作类导出；编排实现仍在 core/
"""

from __future__ import annotations

from core.modules.strategy.core.engines.shared.data_class import (
    CalendarAsOfResult,
    Investment,
    Opportunity,
)
from core.modules.strategy.core.engines.shared.services.as_of_slice import AsOfSlice
from core.modules.strategy.core.hooks.base import StrategyHooks
from core.modules.strategy.core.enums import (
    ExecutionMode,
    SellReason,
    SimulateKind,
    WorkbenchStep,
)
from core.modules.strategy.core.hooks.hook_params import (
    StrategyContext,
    StrategyData,
    StrategyInfo,
)
from core.modules.strategy.core.services.entity_loader.job_bundle_loader import (
    JobBundleLoader,
)
from core.modules.strategy.core.services.progress import ProgressRecorder

__all__ = [
    "AsOfSlice",
    "CalendarAsOfResult",
    "ExecutionMode",
    "Investment",
    "JobBundleLoader",
    "Opportunity",
    "ProgressRecorder",
    "SellReason",
    "SimulateKind",
    "StrategyContext",
    "StrategyData",
    "StrategyHooks",
    "StrategyInfo",
    "WorkbenchStep",
]
